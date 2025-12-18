# Calendar Agent

Conversational calendar assistant built with LangGraph, LangChain tools and the Google Calendar API.

This repository contains a small agent that can create, list, update, delete, and postpone Google Calendar events via an LLM-driven chat interface. The codebase is wired so that the LLM can call structured tools (functions) through LangChain's tools system.

---


## Features

- Create events
- List upcoming events
- Update events
- Delete events
- Postpone events by hours

Planned / easy-to-add features:
- Free/busy queries
- Find free meeting slots for multiple attendees
- Create recurring events
- Modify attendees (add/remove)


---

## Quickstart

1. Create and activate a Python virtual environment (macOS / zsh):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set up Google Calendar API credentials:

- Create or select a Google Cloud project and enable the Google Calendar API.
- Create OAuth 2.0 credentials (Desktop or Web application), download the JSON and save it here as `credentials.json`.

3. Add your OpenAI API key (or other env vars) to `.env`:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

4. First run will trigger Google OAuth flow and create `token.json`.

5. Run the interactive chat:

```bash
python graph.py
```

Type natural-language instructions like "Create a meeting tomorrow at 14:00 called Sprint Review".

---

## Files

- `graph.py`: main LangGraph graph and chat loop. It constructs the LLM, binds tools, and runs the interactive loop.
- `tool.py`: Google Calendar tools implemented as `@tool(args_schema=...)` callables. This file contains Pydantic input models and all calendar operations.
- `api_test.py`: small helper script demonstrating raw Google Calendar API usage.
- `requirements.txt`: recommended Python packages.

---

## How to add a new tool (developer notes)

1. Define a Pydantic input model describing the arguments the tool expects. Use `Field(description=...)` for clearer function metadata.

2. Create the function implementing the tool. Match the function signature to the Pydantic model.

3. Decorate the function with `@tool(args_schema=YourModel)` from `langchain_core.tools`.

4. Append the callable to the `calendar_tools` list at the bottom of `tool.py`.

Example skeleton:

```python
class ExampleInput(BaseModel):
	name: str = Field(description="Name to use")

@tool(args_schema=ExampleInput)
def example_tool(name: str) -> str:
	return f"Hello, {name}!"

# then append example_tool to calendar_tools
```

Notes: when tools are defined this way, LangChain/OpenAI can convert them to OpenAI function schemas automatically.

---

## Testing tips

- For CI/local tests without hitting the real Google API, mock `get_calendar_service()` to return an object with the methods used (e.g., `events().list().execute()`).
- Add a small unit test that imports `graph` and ensures `llm.bind_tools` accepts the `calendar_tools` list without raising `ValueError`.

Quick dry-import to verify tool binding (does not call Google APIs):

```bash
python -c "import graph; print('Imported graph successfully')"
```

If you want, I can add a mocked unit test for `freebusy_query` next.

---

## Next steps (recommended)

1. Implement Free/Busy query tool and a Find Free Slots tool (these are the most useful for scheduling). I can implement these and include mocked tests so you can run them without credentials.
2. Add a small FastAPI wrapper (if you want an HTTP interface) and example endpoints that call the graph.
3. Improve LLM prompts / system message in `graph.py` to better handle follow-ups and missing required fields when creating events.

---

If you'd like, tell me which tool you want implemented first and I will add it (with tests and README notes). 

