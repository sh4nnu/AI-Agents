from typing import TypedDict, Annotated
from langgraph.graph import add_messages, StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from tool import calendar_tools

load_dotenv()

class BasicChatState(TypedDict):
    messages: Annotated[list, add_messages]


# search_tool = TavilySearchResults()
tools = calendar_tools

llm = ChatOpenAI(model="gpt-4o-mini")



###
#  PLANNING THE DESIGN
#  a simple chatbot can look like this  [[ __start__ => chatbot => __end__ ]]
#  but we want some memory, so we can have a state that is list of messages
#
#  Before memory let's add tools to the chatbot
# Now the graph looks like this 
# [Start] --> (Chatbot) --> [End]
#               |  ^
#               v  |
#             (Tools)
##

llm_with_tools = llm.bind_tools(tools=tools)


def chatbot_node(state: BasicChatState) -> BasicChatState:
    # Add system message for calendar agent context
    system_message = HumanMessage(content="""You are a helpful calendar assistant. You can help users:
    - Create new calendar events
    - List upcoming events  
    - Update existing events
    - Delete events
    - Postpone events by hours
    
    When creating events, always ask for required details like title, start time, and end time.
    For dates and times, use ISO format (e.g., '2025-01-15T14:30:00').
    Be friendly and helpful in managing calendar tasks.""")
    
    # Prepend system message if not already present
    messages = state["messages"]
    if not any("calendar assistant" in str(msg.content).lower() for msg in messages):
        messages = [system_message] + messages
    
    return {
        "messages": [llm_with_tools.invoke(messages)]
    }

def tools_router(state: BasicChatState) -> BasicChatState:
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # If there are tool calls, we assume the LLM wants to use a tool
        return "tool_node"
    else:
        return END
    

tool_node = ToolNode(tools=tools, messages_key="messages")
# it looks up for messages key in the state by default. and executes all the tools in tool_calls.
# if we want to customize we can pass tool_calls_key and messages_key parameters.

graph = StateGraph(BasicChatState)
graph.add_node("chatbot", chatbot_node)
graph.add_node("tool_node", tool_node)

graph.set_entry_point("chatbot")
graph.add_conditional_edges("chatbot", tools_router, {
    "tool_node": "tool_node",
    END: END
})
graph.add_edge("tool_node", "chatbot")


app = graph.compile()

while True:
    user_input = input("User: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Exiting the chatbot. Goodbye!")
        break

    response = app.invoke({
        "messages": [HumanMessage(content=user_input)]
    })
    # print(response)
    print("AI:", response["messages"][-1].content)
