from typing import TypedDict, List, Optional

class State(TypedDict):
    """
    Represents the unified state for the LangGraph workflow.
    """
    steps: List[str]
    current_task: str
    generated_code: Optional[str]
    execution_output: Optional[str]
    error_log: Optional[str]
    retry_count: int
