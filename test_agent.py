import uuid
from langchain_core.messages import HumanMessage
from agent.graph.graph import create_graph

# Initialize the graph
graph = create_graph()

# Create a unique thread ID for the conversation
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

def run_test(query: str):
    print(f"\n[USER]: {query}")
    print("-" * 50)
    
    try:
        # We use stream to see the step-by-step handoffs
        for step in graph.stream(
            {"messages": [HumanMessage(content=query)]},
            {"configurable": {"thread_id": thread_id}, "recursion_limit": 100},
            stream_mode="updates"
        ):
            for node_name, values in step.items():
                print(f"\n[NODE: {node_name}]")
                if values and "messages" in values and values["messages"]:
                    last_msg = values["messages"][-1]
                    last_msg.pretty_print()
    except Exception as e:
        import traceback
        print(f"\n[ERROR]: {str(e)}")
        print(traceback.format_exc())
        if "429" in str(e) or "limit" in str(e).lower():
            print("\n[TIP]: You've reached the usage limit for 'qwen3-coder:480b-cloud'.")
            print("Try switching the model in 'agent/nodes/code_generator_node.py' to a smaller one:")
            print("- 'qwen2.5-coder:7b'")
            print("- 'llama3:8b'")
            print("Or wait for the limit to reset.")
        elif "500" in str(e):
            print("\nTIP: A 500 error often means the model (120B) is too large for your system's VRAM or timed out.")
            print("Try pulling a smaller model like 'llama3' or 'phi3' if this persists.")

if __name__ == "__main__":
    print("Starting Frontend Expert Agent Test...")
    print("Ensure Ollama is running with 'glm-4.6:cloud' model.")
    
    # Example Query that triggers Search -> Generate -> Test
    sample_query = "Create a responsive React component for a navigation bar using Tailwind CSS."
    run_test(sample_query)