def file_write_tool(file_path: str, content: str):
    """
    Writes content to a file on the local system.
    """
    with open(file_path, 'w') as f:
        f.write(content)
    return f"File written to {file_path}"
