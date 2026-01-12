from langgraph.graph import StateGraph, END
from agent.graph.state import State
# Import nodes once they are implemented
# from agent.nodes.planner_node import planner_node
# from agent.nodes.code_generator_node import code_generator_node
# from agent.nodes.executor_node import executor_node
# from agent.nodes.error_handler_node import error_handler_node

def create_graph():
    """
    Assembles the LangGraph object and registers nodes and edges.
    """
    workflow = StateGraph(State)

    # Register all nodes
    # workflow.add_node("planner", planner_node)
    # workflow.add_node("generator", code_generator_node)
    # workflow.add_node("executor", executor_node)
    # workflow.add_node("error_handler", error_handler_node)

    # Connect edges & conditions
    # workflow.set_entry_point("planner")
    # ...

    return workflow.compile()
