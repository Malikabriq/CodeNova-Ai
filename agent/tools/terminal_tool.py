import subprocess

def terminal_tool(command: str):
    """
    Executes a terminal command and returns the output.
    """
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr
