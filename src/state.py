from langgraph.graph import MessagesState


# ===== STATE FOR THE MAIN GRAPH =====

class FullResearchState(MessagesState):
    """
    Main graph state for Deep Research Agent.
    
    It incorporates research parameters from the advisor as well as the filesystem and todo list from the deep agents.
    Supervisor summary helps the report writer understand the context of the research without showing it to the user.
    
    Final report is the output of the report writer agent.
    """
    
    # From advisor - research parameters
    research_topic: str = ""
    research_scope: str = ""
    user_approved: bool = False
    
    # Shared with deep agents (both research deep agent and report writer deep agent)
    files: dict[str, str] = {}
    todos: list[dict[str, str]] = []
    
    # Internal handoff from supervisor to report writer
    supervisor_summary: str = ""
    
    # Final output
    final_report: str = ""