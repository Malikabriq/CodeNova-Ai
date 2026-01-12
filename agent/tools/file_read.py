def file_read_tool(file_path: str):
    """
    Reads a file from the local system.
    """
    with open(file_path, 'r') as f:
        return f.read()
