from langgraph.graph import StateGraph, END
from agent.graph.state import FrontendState
from agent.nodes.code_generator_node import (
    generator_node,
    searcher_node,
    tester_node
)
from agent.tools.handoff_tools import (
    search_web_and_handover,
    transition_to_search,
    transition_to_test,
    report_test_results
)
from agent.tools.daytona_tool import run_daytona_test
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import ToolMessage, SystemMessage
from typing import Dict, Any, List
import logging
import os

logger = logging.getLogger(__name__)

# --- SPECIALIZED TOOL HANDLERS ---

def handle_generator_tools(state: FrontendState) -> Any:
    """Execute tools for the generator. Ensures tools belong to the generator."""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}
    
    # STRICT RULE: Only execute the FIRST tool call to prevent loops
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call.get("args") or {}
    kwargs = {**args, "tool_call_id": tool_call["id"]}

    print(f"[GENERATOR] Handling tool call: {tool_name}")

    if tool_name == "transition_to_search":
        return transition_to_search.invoke(kwargs)
    
    elif tool_name == "transition_to_test":
        return transition_to_test.invoke(kwargs)
        
    elif tool_name == "run_daytona_test":
        # Auto-correct hallucination: treat run_daytona_test as transition_to_test
        print(f"[AUTO-CORRECT] Generator called 'run_daytona_test', redirecting to 'transition_to_test'.")
        # Inject feedback so the model learns
        return {
            "messages": [
                ToolMessage(
                    content="AUTO-CORRECT: You called 'run_daytona_test' which is forbidden. I have redirected this to 'transition_to_test' for you. Next time, use 'transition_to_test' directly.",
                    tool_call_id=tool_call["id"]
                )
            ]
        }
        # Ideally we would invoke transition_to_test here, but since the tool call ID matches the forbidden tool,
        # we might just want to fail strictly or map it? 
        # Mapping it is better for flow, but we need to return the Command object from the tool.
        # But the tool_call_id won't match if we invoke a different tool? 
        # Actually, we can just return the Command from transition_to_test but we need to arguably use the same ID?
        # Let's just Return the ToolMessage explaining the fix, and THEN trigger the state update manually?
        # Simplified: Just run the tool it meant to run.
        return transition_to_test.invoke(kwargs)

    elif tool_name == "search_web_and_handover":
         # Auto-correct hallucination: Generator trying to do searcher's job
         print(f"[AUTO-CORRECT] Generator called 'search_web_and_handover', redirecting to 'transition_to_search'.")
         return transition_to_search.invoke(kwargs)

    else:
        # Report unknown tool to the agent so it can self-correct
        return {"messages": [ToolMessage(
            content=f"Error: Tool '{tool_name}' not available. You MUST use 'transition_to_search' or 'transition_to_test'.",
            tool_call_id=tool_call["id"]
        )]}

def handle_searcher_tools(state: FrontendState) -> Any:
    """Execute tools for the searcher."""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}
    
    # Only execute first tool
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call.get("args") or {}
    kwargs = {**args, "tool_call_id": tool_call["id"]}

    if tool_name == "search_web_and_handover":
        return search_web_and_handover.invoke(kwargs)
    else:
        return {"messages": [ToolMessage(
            content=f"Error: Unexpected tool call '{tool_name}'. You only have access to 'search_web_and_handover'.",
            tool_call_id=tool_call["id"]
        )]}

def _execute_test_logic(state, tool_call_id, file_path, generated_code, iteration_count):
    """Refactored logic to run Daytona test and handle file writing."""
    print(f"\n[DAYTONA TEST] Running syntax check for {file_path or 'unknown file'}...")
    
    # We invoke the tool to get the string result
    test_result = run_daytona_test.invoke({
        "code": generated_code, 
        "file_path": file_path,
        "tool_call_id": tool_call_id
    })
    
    if hasattr(test_result, 'content'):
        test_result = test_result.content
    
    print(f"[DAYTONA TEST] Result: {str(test_result)[:100]}...")

    success = "STATUS: SUCCESS" in str(test_result)
    print(f"[DAYTONA TEST] {'✓ PASSED' if success else '✗ FAILED'}")

    # If successful, write file ONLY if it's new or changed (Mock implementation of check for now)
    if success and file_path and generated_code:
        try:
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(generated_code)
            print(f"[FILE WRITTEN] Successfully saved {file_path}")
        except Exception as e:
             print(f"[FILE WRITE ERROR] {str(e)}")

    return report_test_results.invoke({
        "success": success,
        "feedback": test_result,
        "tool_call_id": tool_call_id,
        "iteration_count": iteration_count
    })

def handle_tester_tools(state: FrontendState) -> Any:
    """Execute tools for the tester."""
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}
    
    # PREVENT REDUNDANT TESTING
    if state.get("test_results") == "Success":
         print("[TESTER] Test already PASSED. Skipping redundant test run.")
         tool_call = last_message.tool_calls[0]
         return report_test_results.invoke({
            "success": True, 
            "feedback": "Test already passed previously.", 
            "tool_call_id": tool_call["id"],
            "iteration_count": state.get("iteration_count", 0)
        })

    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call.get("args") or {}
    tool_call_id = tool_call["id"]
    
    # Common state data
    file_path = state.get("file_path", "")
    generated_code = state.get("generated_code", "")
    iteration_count = state.get("iteration_count", 0)
    
    if tool_name in ["run_daytona_test", "transition_to_test"]:
        if tool_name == "transition_to_test":
             print(f"[AUTO-CORRECT] Tester called 'transition_to_test', redirecting to actual test.")
        
        return _execute_test_logic(state, tool_call_id, file_path, generated_code, iteration_count)

    elif tool_name == "report_test_results":
        kwargs = {**args, "tool_call_id": tool_call_id}
        kwargs["iteration_count"] = iteration_count
        return report_test_results.invoke(kwargs)
    
    else:
        return {"messages": [ToolMessage(
            content=f"Error: Unexpected tool call '{tool_name}'. Access 'run_daytona_test' or 'report_test_results'.",
            tool_call_id=tool_call_id
        )]}

# --- GRAPH DEFINITION ---

def create_graph():
    workflow = StateGraph(FrontendState)
    
    workflow.add_node("frontend_generator", generator_node)
    workflow.add_node("web_searcher", searcher_node)
    workflow.add_node("code_tester", tester_node)
    
    workflow.add_node("generator_tools", handle_generator_tools)
    workflow.add_node("searcher_tools", handle_searcher_tools)
    workflow.add_node("tester_tools", handle_tester_tools)
    
    workflow.set_entry_point("frontend_generator")
    
    # SAFE ROUTING FUNCTIONS
    def route_generator(state):
        # Check iteration limit
        iteration_count = state.get("iteration_count", 0)
        if iteration_count >= 5:
            print(f"[TERMINATION] Max iterations ({iteration_count}) reached. Ending workflow.")
            return END
        
        # Check if tests passed
        test_results = state.get("test_results")
        if test_results and str(test_results).strip().lower() == "success":
            print(f"[TERMINATION] Tests passed successfully. Ending workflow.")
            return END
        
        msg = state["messages"][-1]
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return "generator_tools"
        return END

    def route_searcher(state):
        msg = state["messages"][-1]
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return "searcher_tools"
        return "frontend_generator"

    def route_tester(state):
        msg = state["messages"][-1]
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return "tester_tools"
        return "frontend_generator"

    workflow.add_conditional_edges("frontend_generator", route_generator, ["generator_tools", END])
    workflow.add_conditional_edges("web_searcher", route_searcher, ["searcher_tools", "frontend_generator"])
    workflow.add_conditional_edges("code_tester", route_tester, ["tester_tools", "frontend_generator"])
    
    # Tool nodes always return to the correct next node based on their Command logic
    workflow.add_edge("generator_tools", "frontend_generator")
    workflow.add_edge("searcher_tools", "frontend_generator")
    workflow.add_edge("tester_tools", "frontend_generator")
    
    return workflow.compile(checkpointer=InMemorySaver())
