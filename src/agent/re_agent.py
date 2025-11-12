from google.cloud.aiplatform_v1beta1.types import api_auth
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from PIL import Image as PILImage
import io

from langchain_google_vertexai import ChatVertexAI

llm = ChatVertexAI(
    model="gemini-2.5-pro",
    temperature=1,
    max_tokens=2000,
    max_retries=6,
    stop=None,
    # other params...
)

# Graph state
class State(TypedDict):
    topic: str
    joke: str
    improved_joke: str
    ask_for_applause: str
    final_joke: str


# Nodes
def generate_joke(state: State):
    """First LLM call to generate initial joke"""

    msg = llm.invoke(f"Write a short joke about {state['topic']}")
    return {"joke": msg.content}


def check_punchline(state: State):
    """Gate function to check if the joke has a punchline"""

    # Simple check - does the joke contain "?" or "!"
    if "?" in state["joke"] or "!" in state["joke"]:
        return "Pass"
    return "Fail"


def improve_joke(state: State):
    """Second LLM call to improve the joke"""

    msg = llm.invoke(f"Make this joke funnier by adding wordplay: {state['joke']}")
    return {"improved_joke": msg.content}


def ask_for_applause(state: State):
    """Third LLM call to ask for applause"""

    msg = llm.invoke(f"Ask for applause for the joke: {state['joke']}")
    return {"ask_for_applause": msg.content}


def polish_joke(state: State):
    """Third LLM call for final polish"""
    msg = llm.invoke(f"Add a surprising twist to this joke: {state['improved_joke']}")
    return {"final_joke": msg.content}


# Build workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node("generate_joke", generate_joke)
workflow.add_node("improve_joke", improve_joke)
workflow.add_node("ask_for_applause", ask_for_applause)
workflow.add_node("polish_joke", polish_joke)

# Add edges to connect nodes
workflow.add_edge(START, "generate_joke")
workflow.add_conditional_edges(
    "generate_joke", check_punchline, {"Fail": "improve_joke", "Pass": "ask_for_applause"}
)
workflow.add_edge("improve_joke", "polish_joke")
workflow.add_edge("polish_joke", "ask_for_applause")
workflow.add_edge("ask_for_applause", END)

# Compile
chain = workflow.compile()

# Show workflow
graph_image = chain.get_graph().draw_mermaid_png()
img = PILImage.open(io.BytesIO(graph_image))
img.show()  # Abrirá la imagen con el visor predeterminado

# Invoke
state = chain.invoke({"topic": "cats"})
print("This is the state: ", state)
print("Initial joke:")
print(state["joke"])
print("\n--- --- ---\n")
if "improved_joke" in state:
    print("Improved joke:")
    print(state["improved_joke"])
    print("\n--- --- ---\n")

    print("Final joke:")
    print(state["final_joke"])
elif "ask_for_applause" in state:
    print("Ask for applause:")
    print(state["ask_for_applause"])
else:
    print("Joke failed quality gate - no punchline detected!")