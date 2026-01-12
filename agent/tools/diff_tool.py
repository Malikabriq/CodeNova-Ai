def diff_tool(original: str, modified: str):
    """
    Creates a patch/diff between two versions of code.
    """
    import difflib
    diff = difflib.unified_diff(original.splitlines(), modified.splitlines())
    return "\n".join(diff)
