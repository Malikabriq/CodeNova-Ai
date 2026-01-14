import os
import subprocess
from langchain_core.tools import tool
from daytona_sdk import Daytona, CreateSandboxFromImageParams, DaytonaError

@tool
def run_daytona_test(code: str, file_path: str) -> str:
    """
    Runs a syntax check for the generated code using a real Daytona Sandbox.
    If the Daytona API is unavailable, falls back to a local Node.js syntax check.
    
    Args:
        code: The full source code content to test.
        file_path: The relative path where the file would be saved (e.g., 'src/components/Navbar.jsx').
    """
    print(f"\n[DAYTONA] Testing {file_path}...")
    
    # 1. Try Real Daytona Integration
    api_key = os.getenv("DAYTONA_API_KEY")
    if api_key and api_key != "YOUR_DAYTONA_API_KEY":
        try:
            daytona = Daytona()
            # Use node:20-slim for fast starts and guaranteed node availability
            params = CreateSandboxFromImageParams(
                image="node:20-slim",
                language="javascript",
                name=f"codenova-test-{os.urandom(4).hex()}"
            )
            sandbox = daytona.create(params, timeout=120)
            
            # Write file to sandbox
            sandbox.fs.upload_file(code.encode("utf-8"), file_path)
            
            # Execute syntax check
            check_cmd = f"node --check {file_path}"
            result = sandbox.process.exec(check_cmd)
            
            # Cleanup sandbox
            try:
                daytona.delete(sandbox)
            except:
                pass
            
            if result.exit_code == 0:
                print(f"[DAYTONA] {file_path} passed real sandbox check.")
                return f"Syntax OK for {file_path}.\nSTATUS: SUCCESS"
            else:
                print(f"[DAYTONA] {file_path} failed real sandbox check.")
                # Truncate error to avoid context blowout
                error_summary = result.result[:1000]
                return f"Syntax Error in {file_path}:\n{error_summary}\nSTATUS: FAILURE"
                
        except Exception as e:
            print(f"[DAYTONA] SDK Error: {str(e)}. Falling back to local check.")
    
    # 2. Fallback to Local Check
    try:
        # For local check, we need a temporary file.
        # We'll use a generic .js extension for the local check to ensure node --check works.
        temp_file_name = "temp_test_file.js"
        with open(temp_file_name, "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(
            ["node", "--check", temp_file_name],
            capture_output=True,
            text=True
        )
        
        try:
         os.remove(temp_file_name)
        except:
         pass
        
        if result.returncode == 0:
            return f"Local Syntax OK for {file_path}.\nSTATUS: SUCCESS"
        else:
            return f"Local Syntax Error for {file_path}:\n{result.stderr[:1000]}\nSTATUS: FAILURE"
            
    except Exception as e:
        return f"Syntax Check Error: {str(e)}\nSTATUS: FAILURE"
