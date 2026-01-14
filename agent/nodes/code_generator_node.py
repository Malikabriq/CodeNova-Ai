from typing import Dict, Any, List, Callable
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph.state import FrontendState
from agent.tools.handoff_tools import (
    search_web_and_handover, 
    transition_to_search, 
    transition_to_test, 
    report_test_results
)
from agent.tools.daytona_tool import run_daytona_test

# --- PROMPTS ---

FRONTEND_GENERATOR_PROMPT = """You are a Forward-Thinking Frontend Architect.
CURRENT STEP: Generation / Refinement
ITERATION: {iteration_count} / 5

GOAL: Build state-of-the-art frontend solutions using the ABSOLUTE LATEST techniques.

CRITICAL WORKFLOW:
1. **First Time (no search results)**: Call 'transition_to_search' with a specific query.
2. **After Search Results**: IMMEDIATELY generate code. DO NOT search again.
3. **Upon Generating Code**: You MUST call 'transition_to_test' with your code and file path.
4. **After Test Failure**: Fix the code based on error feedback, then call 'transition_to_test' again.
5. **After Test Success**: STOP. Do not generate anything else.

STRICT RULES:
1. **SINGLE ACTION ONLY**: You MUST call EXACTLY ONE tool.
2. **ALLOWED TOOLS**: 'transition_to_search', 'transition_to_test'.
3. **FORBIDDEN**: DO NOT call 'search_web_and_handover'. DO NOT call 'run_daytona_test'.
4. **CLEAN CODE ONLY**: Your 'transition_to_test' call must contain ONLY valid code in the 'code' argument. NO Markdown blocks, NO system logs, NO "Search Results" text.

Context:
Generated Code: {generated_code}
Test Results: {test_results}
Error Feedback: {error_feedback}
Last Error: {last_error}
{search_context}
"""

WEB_SEARCHER_PROMPT = """You are a Web Research specialist.
GOAL: Find the latest 2026 documentation and code for the user requested topic.

CRITICAL RULES:
1. You have access ONLY to 'search_web_and_handover'.
2. You MUST use 'search_web_and_handover' immediately with a relevant search query.
3. Do NOT attempt to provide code. Do NOT attempt to hand off to other specialists.
4. Your search query MUST BE: {search_query}
"""

CODE_TESTER_PROMPT = """You are a Quality Assurance Specialist.
GOAL: Verify the provided code for syntax errors.

CRITICAL RULES:
1. You have access ONLY to 'run_daytona_test' and 'report_test_results'.
2. **STEP 1**: Call 'run_daytona_test' FIRST with the generated code.
3. **STEP 2**: Wait for the result, then call 'report_test_results' with success=True/False.
4. If 'run_daytona_test' returns "STATUS: SUCCESS", you MUST call 'report_test_results' with success=True.
5. **FORBIDDEN**: DO NOT call 'transition_to_test'.

**Code to test**: {generated_code}
**Target file**: {file_path}
"""

# --- CONFIGURATION ---

STEP_CONFIG = {
    "frontend_generator": {
        "prompt": FRONTEND_GENERATOR_PROMPT,
        "tools": [transition_to_test, transition_to_search],
        "requires": []
    },
    "web_searcher": {
        "prompt": WEB_SEARCHER_PROMPT,
        "tools": [search_web_and_handover],
        "requires": ["search_query"]
    },
    "code_tester": {
        "prompt": CODE_TESTER_PROMPT,
        "tools": [run_daytona_test, report_test_results],
        "requires": ["generated_code", "file_path"]
    }
}

# --- MIDDLEWARE ---

@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Configure agent behavior based on the current step."""
    current_step = request.state.get("current_step", "frontend_generator")
    iteration_count = request.state.get("iteration_count", 0)
    
    step_config = STEP_CONFIG[current_step]
    
    # Prepare search context if available
    search_results = request.state.get("search_results")
    search_context = f"Search Results: {search_results}" if search_results else ""

    state_data = {
        "generated_code": request.state.get("generated_code", "None"),
        "test_results": request.state.get("test_results", "None"),
        "error_feedback": request.state.get("error_feedback", "None"),
        "search_results": search_results or "None",
        "search_query": request.state.get("search_query", "None"),
        "file_path": request.state.get("file_path", "None"),
        "iteration_count": iteration_count,
        "last_error": request.state.get("last_error", "None"),
        "search_context": search_context
    }
    
    system_prompt = step_config["prompt"].format(**state_data)
    
    # Enforce strictly compatible tools
    request = request.override(
        system_prompt=system_prompt,
        tools=step_config["tools"],
    )
    return handler(request)

# --- NODE IMPLEMENTATIONS ---

def generator_node(state: FrontendState) -> Dict[str, Any]:
    """Expert Frontend Architect node with enhanced state logic AND dynamic tool binding."""
    step_config = STEP_CONFIG["frontend_generator"]
    search_results = state.get("search_results")
    search_context = f"Search Results: {search_results}" if search_results else ""
    
    iteration_count = state.get("iteration_count", 0)
    generated_code = state.get("generated_code")
    test_results = state.get("test_results")

    # --- STATE CHECK 1: STOP CONDITION ---
    if test_results == "Success":
        # Tests passed, we are done. Stop generating.
        return {"messages": []}

    state_data = {
        "generated_code": generated_code or "None",
        "test_results": test_results or "None",
        "error_feedback": state.get("error_feedback", "None"),
        "search_results": search_results or "None",
        "search_query": state.get("search_query", "None"),
        "file_path": state.get("file_path", "None"),
        "iteration_count": iteration_count,
        "last_error": state.get("last_error", "None"),
        "search_context": search_context
    }
    
    prompt = step_config["prompt"].format(**state_data)
    
    model = ChatOllama(model="glm-4.6:cloud", temperature=0)
    
    # --- DYNAMIC TOOL BINDING (CRITICAL FIX) ---
    # Force the model down the correct path by removing options.
    available_tools = []
    
    if not search_results or search_results == "None":
        # No search results yet? You MUST search.
        print("[GENERATOR] No search results found. Forcing 'transition_to_search'.")
        available_tools = [transition_to_search]
        # Append instruction to invalid context
        prompt += "\n\nCONSTRAINT: You have NO search results. You MUST call 'transition_to_search' now."
    else:
        # Have search results? You MUST generate/test. Search is forbidden.
        print("[GENERATOR] Search results present. Forcing 'transition_to_test'.")
        available_tools = [transition_to_test]
        prompt += "\n\nCONSTRAINT: Search complete. You MUST generate code and call 'transition_to_test' now. Do NOT search again."

    model_with_tools = model.bind_tools(available_tools)
    
    # Filter messages to remove old system messages
    messages = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    
    system_msg = SystemMessage(content=prompt)
    
    # Retry logic
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = model_with_tools.invoke([system_msg] + messages)
            return {"messages": [response]}
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                if "Internal Server Error" in error_msg or "status code: -1" in error_msg:
                    import time
                    print(f"[RETRY] Ollama connection failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            raise


def searcher_node(state: FrontendState) -> Dict[str, Any]:
    """Web Research specialist node."""
    step_config = STEP_CONFIG["web_searcher"]
    state_data = {
        "search_query": state.get("search_query", "None"),
    }
    prompt = step_config["prompt"].format(**state_data)
    model = ChatOllama(model="glm-4.6:cloud", temperature=0)
    model_with_tools = model.bind_tools(step_config["tools"])
    
    system_msg = SystemMessage(content=prompt)
    
    # ISOLATION: Searcher only needs the prompt and no history
    # This prevents it from seeing previous failed attempts
    
    for attempt in range(3):
        try:
            response = model_with_tools.invoke([system_msg])
            return {"messages": [response]}
        except Exception:
            if attempt < 2:
                continue
            raise

def tester_node(state: FrontendState) -> Dict[str, Any]:
    """QA Tester node."""
    step_config = STEP_CONFIG["code_tester"]
    state_data = {
        "file_path": state.get("file_path", "None"),
        "generated_code": state.get("generated_code", "None")
    }
    prompt = step_config["prompt"].format(**state_data)
    model = ChatOllama(model="glm-4.6:cloud", temperature=0)
    model_with_tools = model.bind_tools(step_config["tools"])
    
    system_msg = SystemMessage(content=prompt)
    
    for attempt in range(3):
        try:
            response = model_with_tools.invoke([system_msg])
            return {"messages": [response]}
        except Exception:
            if attempt < 2:
                continue
            raise

def get_frontend_agent():
    """Returns the compiled graph."""
    from agent.graph.graph import create_graph
    return create_graph()
