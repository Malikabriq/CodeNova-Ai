import os
from typing import Literal
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools.tavily_search import TavilySearchResults
from agent.graph.state import FrontendState

# Initialize search tools
ddg_search = DuckDuckGoSearchRun()

def get_search_results(query: str) -> str:
    """Run search using Tavily if API key is present, otherwise useful DuckDuckGo."""
    if os.getenv("TAVILY_API_KEY"):
        try:
            tavily = TavilySearchResults(max_results=3)
            # Tavily returns a list of dicts. We want to format this cleanly.
            results = tavily.run(query)
            if isinstance(results, list):
                formatted_results = []
                for i, res in enumerate(results):
                    content = res.get('content', '')[:500] # Truncate content
                    url = res.get('url', 'No URL')
                    formatted_results.append(f"Result {i+1}: {content} (Source: {url})")
                return "\n\n".join(formatted_results)
            return str(results)[:2000] # Fallback truncation
        except Exception as e:
            fallback = ddg_search.run(query)
            return f"Search Error: {str(e)}. Fallback Results:\n{fallback}"[:2000]
    
    # DDG generic run
    return ddg_search.run(query)[:2000]

@tool
def search_web_and_handover(
    query: str,
    tool_call_id: str = "manual",
) -> Command:
    """Search the web for frontend code, documentation, or solutions, then transition back to generator."""
    results = get_search_results(query)
    # Ensure no system-like headers that might confuse the model
    clean_results = results.replace("System:", "System_Info:").replace("User:", "User_Info:")
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Search Query: {query}\n\nResults:\n{clean_results}",
                    tool_call_id=tool_call_id,
                )
            ],
            "search_results": clean_results,
            "current_step": "frontend_generator",
        },
        goto="frontend_generator"
    )

@tool
def transition_to_search(
    query: str,
    tool_call_id: str = "manual",
) -> Command:
    """Transition to the web searcher step to find more information."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Transitioning to search for: {query}",
                    tool_call_id=tool_call_id,
                )
            ],
            "search_query": query,
            "current_step": "web_searcher",
        },
        goto="web_searcher"
    )

@tool
def transition_to_test(
    code: str,
    file_path: str,
    tool_call_id: str = "manual",
) -> Command:
    """Transition to the code tester step to verify the generated code."""
    # Strip any markdown fencing if the model accidentally included it in the string argument
    clean_code = code.replace("```tsx", "").replace("```typescript", "").replace("```javascript", "").replace("```", "").strip()
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Code generated for {file_path}. Transitioning to test.",
                    tool_call_id=tool_call_id,
                )
            ],
            "generated_code": clean_code,
            "file_path": file_path,
            "current_step": "code_tester",
        },
        goto="code_tester"
    )

@tool
def report_test_results(
    success: bool,
    feedback: str,
    tool_call_id: str = "manual",
    iteration_count: int = 0,
) -> Command:
    """Report test results from Daytona. If failed, transition back to generator for fix."""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Test {'Success' if success else 'Failure'}: {feedback}",
                    tool_call_id=tool_call_id,
                )
            ],
            "test_results": "Success" if success else "Failure",
            "error_feedback": feedback if not success else "",
            "last_error": feedback if not success else "None",
            "current_step": "frontend_generator",
            "iteration_count": iteration_count + 1
        },
        goto="frontend_generator"
    )
