"""
Minimal test to isolate the Ollama connection issue.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

print("Testing Ollama connection with langchain_ollama...")
print("-" * 50)

try:
    # Test 1: Simple invoke
    print("\nTest 1: Simple invoke without tools")
    model = ChatOllama(model="gpt-oss:120b-cloud", temperature=0)
    response = model.invoke([HumanMessage(content="Say 'Hello' in one word.")])
    print(f"✓ Success: {response.content}")
    
    # Test 2: With streaming
    print("\nTest 2: Streaming response")
    for chunk in model.stream([HumanMessage(content="Count to 3")]):
        print(chunk.content, end="", flush=True)
    print("\n✓ Streaming works")
    
    # Test 3: With tools (this is where it might fail)
    print("\nTest 3: With tool binding")
    from langchain.tools import tool
    
    @tool
    def test_tool(query: str) -> str:
        """A simple test tool."""
        return f"Received: {query}"
    
    model_with_tools = model.bind_tools([test_tool])
    response = model_with_tools.invoke([HumanMessage(content="Just say hello, don't call any tools.")])
    print(f"✓ Tool binding works: {response.content if hasattr(response, 'content') else response}")
    
    print("\n" + "=" * 50)
    print("All tests passed! The issue might be in the agent's prompt or state.")
    
except Exception as e:
    import traceback
    print(f"\n✗ Error: {str(e)}")
    print(traceback.format_exc())
    print("\nDiagnostics:")
    print(f"- Model: gpt-oss:120b-cloud")
    print(f"- Error type: {type(e).__name__}")
    if "429" in str(e) or "limit" in str(e).lower():
        print("- Likely cause: Rate limit or usage limit")
    elif "500" in str(e) or "-1" in str(e):
        print("- Likely cause: Model timeout or VRAM issue")
        print("- Suggestion: The cloud model might be overloaded or timing out")
