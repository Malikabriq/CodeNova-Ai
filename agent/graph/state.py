from typing import List, Literal, Optional, Annotated, Dict, Any, Union
from typing_extensions import TypedDict, NotRequired
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Define the possible workflow steps
FrontendStep = Literal["frontend_generator", "web_searcher", "code_tester"]

def take_last(left: Any, right: Any) -> Any:
    return right if right is not None else left

class FrontendState(TypedDict):
    """State for the frontend generation workflow."""
    current_step: Annotated[Optional[FrontendStep], take_last]
    search_query: Annotated[Optional[str], take_last]
    search_results: Annotated[Optional[str], take_last]
    generated_code: Annotated[Optional[str], take_last]
    test_results: Annotated[Optional[str], take_last]
    error_feedback: Annotated[Optional[str], take_last]
    file_path: Annotated[Optional[str], take_last]
    iteration_count: Annotated[Optional[int], take_last]
    last_error: Annotated[Optional[str], take_last]
    messages: Annotated[List[AnyMessage], add_messages]
