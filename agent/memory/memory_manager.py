class MemoryManager:
    """
    Handles short-term and long-term memory for the agent.
    """
    def __init__(self):
        self.short_term = []
        self.long_term = None # RAG or Vector DB integrate here

    def track_history(self, step):
        self.short_term.append(step)
