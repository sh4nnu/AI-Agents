import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import AliasChoices, BaseModel, Field, ConfigDict
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()
def _require_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your environment before starting the backend."
        )
    return api_key


class ChartIdea(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: str = Field(..., description="Readable chart name.")
    description: str = Field(..., description="Short description of the insight.")
    chart_type: str = Field(
        ...,
        description="Type of chart (bar, line, pie, scatter, heatmap, radar, etc.).",
    )
    option: Dict[str, Any] = Field(
        default_factory=dict,
        description="Apache ECharts option JSON needed to render the chart.",
        validation_alias=AliasChoices("option", "option_json"),
    )


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str
    chart_suggestions: List[ChartIdea] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    dataset_profile: str
    user_input: str
    chat_history: List[Dict[str, str]]
    chart_suggestions: List[Dict[str, Any]]
    reply: Optional[str]


MANUAL_CHART_ORDER = ["bar", "line", "pie"]


def build_agent_graph() -> Any:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        api_key=_require_api_key(),
    )

    def agent_node(state: AgentState) -> AgentState:
        history = state.get("chat_history", [])
        history_lines = [f"{msg['role'].upper()}: {msg['content']}" for msg in history]
        history_text = "\n".join(history_lines) if history_lines else "None so far."
        chart_suggestions = state.get("chart_suggestions", [])
        prompt = (
            "You are a data visualization agent that designs Apache ECharts configs.\n"
            "You always return concise explanations plus up to six chart ideas. "
            "Each chart must include a full ECharts option JSON referencing the provided dataset.\n"
            "Dataset profile:\n"
            f"{state['dataset_profile']}\n\n"
            f"Previous charts (JSON): {json.dumps(chart_suggestions, indent=2)}\n"
            f"Conversation so far:\n{history_text}\n\n"
            f"User message: {state['user_input']}\n"
            "Craft new or refined chart suggestions that fit the data and highlight insights."
        )
        structured_llm = llm.with_structured_output(
            AgentResponse, method="function_calling"
        )
        agent_response = structured_llm.invoke(prompt)
        state["chart_suggestions"] = [
            suggestion.model_dump() for suggestion in agent_response.chart_suggestions
        ]
        state["reply"] = agent_response.reply
        return state

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph.compile()


agent_graph: Optional[Any] = None


def get_agent_graph() -> Any:
    global agent_graph
    if agent_graph is None:
        agent_graph = build_agent_graph()
    return agent_graph


def format_value(value: Any) -> Any:
    if isinstance(value, (int, float, str)):
        return value
    if pd.isna(value):
        return None
    return str(value)


def summarize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    preview_records = df.head(20).to_dict(orient="records")
    preview_records = [
        {k: format_value(v) for k, v in record.items()} for record in preview_records
    ]
    column_summaries = []
    for column in df.columns:
        series = df[column]
        column_summaries.append(
            {
                "name": column,
                "dtype": str(series.dtype),
                "non_null": int(series.notna().sum()),
                "sample_values": [format_value(v) for v in series.head(5).tolist()],
            }
        )
    try:
        describe_df = df.describe(include="all", datetime_is_numeric=True)
    except TypeError:
        # Older pandas versions do not accept datetime_is_numeric.
        describe_df = df.describe(include="all")
    describe = describe_df.fillna("").to_dict()
    profile_text = json.dumps(
        {
            "columns": column_summaries,
            "stats": describe,
            "preview_rows": preview_records,
        },
        indent=2,
    )
    return {
        "columns": column_summaries,
        "preview": preview_records,
        "profile_text": profile_text,
    }


@dataclass
class SessionState:
    dataframe: pd.DataFrame
    profile_text: str
    columns: List[Dict[str, Any]]
    preview: List[Dict[str, Any]]
    history: List[Dict[str, str]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    manual_charts: Dict[str, Dict[str, Any]] = field(default_factory=dict)


sessions: Dict[str, SessionState] = {}


def get_all_charts(session: SessionState) -> List[Dict[str, Any]]:
    manual: List[Dict[str, Any]] = []
    for chart_type in MANUAL_CHART_ORDER:
        chart = session.manual_charts.get(chart_type)
        if chart:
            manual.append(chart)
    for chart_type, chart in session.manual_charts.items():
        if chart_type not in MANUAL_CHART_ORDER:
            manual.append(chart)
    manual.extend(session.charts)
    return manual


CHART_SLOT_PATTERN = re.compile(r"chart\s*(\d+)", re.IGNORECASE)


def extract_chart_command(message: str) -> Optional[Tuple[Optional[int], str]]:
    lower = message.lower()
    chart_type = None
    if "bar" in lower:
        chart_type = "bar"
    elif any(token in lower for token in ("line", "timeseries", "trend")):
        chart_type = "line"
    elif "pie" in lower:
        chart_type = "pie"
    match = CHART_SLOT_PATTERN.search(lower)
    slot: Optional[int] = None
    if match:
        slot_num = int(match.group(1))
        if 1 <= slot_num <= 6:
            slot = slot_num
    if not chart_type and slot:
        index = slot - 1
        if 0 <= index < len(MANUAL_CHART_ORDER):
            chart_type = MANUAL_CHART_ORDER[index]
    if not chart_type:
        return None
    return slot, chart_type


def _choose_categorical_column(df: pd.DataFrame) -> Optional[str]:
    candidates: List[Tuple[str, int]] = []
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            unique = series.nunique(dropna=True)
            if unique > 0:
                candidates.append((column, unique))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[1], item[0]))
    return candidates[0][0]


def _choose_numeric_column(df: pd.DataFrame) -> Optional[str]:
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            return column
    return None


def _extract_datetime_series(df: pd.DataFrame) -> Tuple[Optional[str], Optional[pd.Series]]:
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            converted = pd.to_datetime(series, errors="coerce")
            if converted.notna().any():
                return column, converted
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_object_dtype(series):
            converted = pd.to_datetime(series, errors="coerce")
            if converted.notna().sum() >= 3:
                return column, converted
    return None, None


def build_bar_chart(df: pd.DataFrame) -> ChartIdea:
    column = _choose_categorical_column(df)
    if column:
        counts = (
            df[column]
            .dropna()
            .astype(str)
            .value_counts()
            .head(10)
        )
        if counts.empty:
            raise ValueError(f"No valid values found in column '{column}'.")
        categories = counts.index.tolist()
        values = counts.values.tolist()
        title = f"Distribution of {column}"
        description = f"Top categories in {column} sorted by frequency."
    else:
        numeric_col = _choose_numeric_column(df)
        if not numeric_col:
            raise ValueError("No suitable categorical or numeric column available for a bar chart.")
        numeric_series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        if numeric_series.empty:
            raise ValueError(f"No numeric values found in column '{numeric_col}'.")
        binned = pd.cut(numeric_series, bins=min(10, numeric_series.nunique()))
        counts = binned.value_counts().sort_index()
        categories = [str(interval) for interval in counts.index]
        values = counts.values.tolist()
        title = f"Distribution of {numeric_col}"
        description = f"Value distribution of {numeric_col} grouped into bins."
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": categories},
        "yAxis": {"type": "value"},
        "series": [
            {
                "type": "bar",
                "data": values,
                "itemStyle": {"color": "#2563eb"},
            }
        ],
    }
    return ChartIdea(
        title=title,
        description=description,
        chart_type="bar",
        option=option,
    )


def build_pie_chart(df: pd.DataFrame) -> ChartIdea:
    column = _choose_categorical_column(df)
    if not column:
        raise ValueError("A pie chart requires a categorical column.")
    counts = (
        df[column]
        .dropna()
        .astype(str)
        .value_counts()
        .head(8)
    )
    if counts.empty:
        raise ValueError(f"No valid values found in column '{column}'.")
    series_data = [
        {"name": name, "value": int(value)} for name, value in counts.items()
    ]
    option = {
        "title": {"text": f"Share of {column}", "left": "center"},
        "tooltip": {"trigger": "item"},
        "legend": {"bottom": 0},
        "series": [
            {
                "name": column,
                "type": "pie",
                "radius": "60%",
                "data": series_data,
            }
        ],
    }
    return ChartIdea(
        title=f"Share of {column}",
        description=f"Percentage breakdown of {column} values based on the dataset.",
        chart_type="pie",
        option=option,
    )


def build_line_chart(df: pd.DataFrame) -> ChartIdea:
    column, datetime_series = _extract_datetime_series(df)
    if column and datetime_series is not None:
        cleaned = datetime_series.dropna()
        if cleaned.empty:
            column = None
    if column and datetime_series is not None and not datetime_series.dropna().empty:
        grouped = (
            datetime_series.dropna().dt.to_period("D").value_counts().sort_index()
        )
        labels = [str(period) for period in grouped.index]
        values = grouped.values.tolist()
        title = f"Daily counts of {column}"
        description = f"Number of records for each day based on {column}."
        y_label = "Count"
    else:
        numeric_col = _choose_numeric_column(df)
        if not numeric_col:
            raise ValueError("Need a datetime or numeric column for a line chart.")
        numeric_series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
        if numeric_series.empty:
            raise ValueError(f"No numeric values found in column '{numeric_col}'.")
        numeric_series = numeric_series.head(100)
        labels = [str(idx + 1) for idx in range(len(numeric_series))]
        values = numeric_series.tolist()
        title = f"{numeric_col} trend"
        description = f"Sequential trend of {numeric_col} for the first {len(values)} rows."
        y_label = numeric_col
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": labels},
        "yAxis": {"type": "value", "name": y_label},
        "series": [
            {
                "type": "line",
                "smooth": True,
                "areaStyle": {},
                "data": values,
                "lineStyle": {"width": 2},
            }
        ],
    }
    return ChartIdea(
        title=title,
        description=description,
        chart_type="line",
        option=option,
    )


def build_chart_from_dataset(session: SessionState, chart_type: str) -> ChartIdea:
    if chart_type == "bar":
        return build_bar_chart(session.dataframe)
    if chart_type == "line":
        return build_line_chart(session.dataframe)
    if chart_type == "pie":
        return build_pie_chart(session.dataframe)
    raise ValueError(f"Unsupported chart type '{chart_type}'.")


AGG_FUNCTIONS: Dict[str, str] = {
    "sum": "sum",
    "mean": "mean",
    "avg": "mean",
    "count": "count",
}


def _validate_column_exists(df: pd.DataFrame, column: Optional[str]) -> str:
    if not column:
        raise HTTPException(
            status_code=400, detail="Please provide a column name to group by."
        )
    if column not in df.columns:
        raise HTTPException(
            status_code=400, detail=f"Column '{column}' was not found in the dataset."
        )
    return column


def build_grouped_chart(
    session: SessionState,
    chart_type: str,
    group_by: Optional[str],
    value: Optional[str],
    agg: Optional[str],
) -> ChartIdea:
    chart_type = chart_type.lower()
    if chart_type not in {"bar", "line", "pie"}:
        raise HTTPException(
            status_code=400,
            detail="Only bar, line, and pie charts are supported for manual builds.",
        )

    df = session.dataframe
    if not group_by:
        return build_chart_from_dataset(session, chart_type)

    group_by = _validate_column_exists(df, group_by)
    agg_key = (agg or "count").lower()
    agg_func = AGG_FUNCTIONS.get(agg_key)
    if not agg_func:
        raise HTTPException(
            status_code=400,
            detail="Aggregation must be one of: count, sum, mean.",
        )

    working = df.copy()
    if agg_func == "count":
        grouped = working.groupby(group_by).size()
        metric_label = "Count"
    else:
        metric_column = _validate_column_exists(df, value)
        working[metric_column] = pd.to_numeric(
            working[metric_column], errors="coerce"
        )
        working = working.dropna(subset=[metric_column])
        if working.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No numeric values found in column '{metric_column}' "
                "after cleaning.",
            )
        grouped = working.groupby(group_by)[metric_column].agg(agg_func)
        metric_label = f"{agg_key.title()} of {metric_column}"

    if grouped.empty:
        raise HTTPException(
            status_code=400,
            detail="Grouping returned no data. Try another column or aggregation.",
        )

    grouped = grouped.sort_values(ascending=False)
    labels = [format_value(idx) for idx in grouped.index.tolist()]
    values = [format_value(val) for val in grouped.tolist()]
    title = f"{metric_label} by {group_by}"
    description = f"{metric_label} grouped by {group_by} using {agg_key}."

    if chart_type == "pie":
        top_labels = labels[:8]
        top_values = values[:8]
        option = {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "item"},
            "legend": {"bottom": 0},
            "series": [
                {
                    "type": "pie",
                    "radius": "60%",
                    "data": [
                        {"name": name, "value": val}
                        for name, val in zip(top_labels, top_values)
                    ],
                }
            ],
        }
    else:
        option = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": labels},
            "yAxis": {"type": "value", "name": metric_label},
            "series": [
                {
                    "type": chart_type,
                    "smooth": chart_type == "line",
                    "data": values,
                    **({"areaStyle": {}} if chart_type == "line" else {}),
                }
            ],
        }

    return ChartIdea(
        title=title,
        description=description,
        chart_type=chart_type,
        option=option,
    )


def describe_target_slot(slot: Optional[int], chart_type: str) -> str:
    if slot:
        return f"Chart {slot}"
    if chart_type in MANUAL_CHART_ORDER:
        return f"Chart {MANUAL_CHART_ORDER.index(chart_type) + 1}"
    return "chart canvas"


def load_dataframe(filename: Optional[str], raw_content: bytes) -> pd.DataFrame:
    if not raw_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    buffer = io.BytesIO(raw_content)
    extension = os.path.splitext(filename or "")[1].lower()
    try:
        if extension == ".csv":
            df = pd.read_csv(buffer)
        elif extension in {".xls", ".xlsx"}:
            df = pd.read_excel(buffer)
        else:
            raise HTTPException(
                status_code=400, detail="Only CSV and Excel files are supported."
            )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {exc}") from exc
    if df.empty:
        raise HTTPException(status_code=400, detail="Dataset has no rows.")
    return df


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)) -> Dict[str, Any]:
    raw = await file.read()
    df = load_dataframe(file.filename, raw)
    summary = summarize_dataframe(df)
    session_id = str(uuid4())
    sessions[session_id] = SessionState(
        dataframe=df,
        profile_text=summary["profile_text"],
        columns=summary["columns"],
        preview=summary["preview"],
    )
    return {
        "session_id": session_id,
        "columns": summary["columns"],
        "preview": summary["preview"],
    }


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ManualChartRequest(BaseModel):
    session_id: str
    chart_type: str
    group_by: Optional[str] = None
    value: Optional[str] = None
    agg: Optional[str] = None


@app.post("/chat")
async def chat_with_agent(payload: ChatRequest) -> Dict[str, Any]:
    session = sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    command = extract_chart_command(payload.message)
    if command:
        slot, chart_type = command
        target_label = describe_target_slot(slot, chart_type)
        try:
            chart = build_chart_from_dataset(session, chart_type)
        except ValueError as exc:
            reply = f"Could not build a {chart_type} chart: {exc}"
        else:
            chart_dict = chart.model_dump()
            session.manual_charts[chart_type] = chart_dict
            reply = (
                f"{target_label} updated with '{chart.title}' using real data from your upload."
            )
        session.history.append({"role": "user", "content": payload.message})
        session.history.append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "charts": get_all_charts(session),
            "history": session.history,
        }

    graph = get_agent_graph()
    state: AgentState = {
        "dataset_profile": session.profile_text,
        "user_input": payload.message,
        "chat_history": session.history,
        "chart_suggestions": session.charts,
    }
    result = graph.invoke(state)
    reply = result.get("reply")
    if not reply:
        raise HTTPException(status_code=500, detail="Agent did not return a reply.")
    session.history.append({"role": "user", "content": payload.message})
    session.history.append({"role": "assistant", "content": reply})
    session.charts = result.get("chart_suggestions", [])
        return {
        "reply": reply,
        "charts": get_all_charts(session),
        "history": session.history,
    }


@app.post("/chart/manual")
async def build_manual_chart(payload: ManualChartRequest) -> Dict[str, Any]:
    session = sessions.get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    try:
        chart = build_grouped_chart(
            session,
            chart_type=payload.chart_type,
            group_by=payload.group_by,
            value=payload.value,
            agg=payload.agg,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not build chart: {exc}"
        ) from exc
    session.manual_charts[chart.chart_type] = chart.model_dump()
    message = f"{chart.chart_type.title()} chart updated with {chart.title}."
    return {
        "message": message,
        "chart": chart.model_dump(),
        "charts": get_all_charts(session),
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}
