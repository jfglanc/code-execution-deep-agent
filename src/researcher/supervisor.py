"""
Deep Agent supervisor for research coordination.
"""

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage

from src.state import FullResearchState
from src.config import get_supervisor_model
from src.researcher.researcher_subagent import research_subagent
from src.researcher.prompts import SUPERVISOR_SYSTEM_PROMPT, SUPERVISOR_INITIAL_MESSAGE_TEMPLATE


# ===== CREATE SUPERVISOR DEEP AGENT =====
# This is the supervisor deep agent that coordinates the research, delegates research tasks, and stores findings/sources in filesystem.
supervisor_deep_agent = create_deep_agent(
    model=get_supervisor_model(),
    tools=[],  # Supervisor only delegates, no need for extra tools
    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    subagents=[research_subagent],
    # backend defaults to StateBackend (virtual filesystem in state["files"])
)


# ===== WRAPPER FUNCTION FOR MAIN GRAPH =====

async def deep_research_supervisor(state: FullResearchState) -> dict:
    """
    Wrapper function to integrate Deep Agent supervisor into main graph.
    
    Receives FullResearchState from advisor, invokes Deep Agent supervisor,
    returns updated state for report writer.
    
    Args:
        state: State from main graph containing research_topic and research_scope
        
    Returns:
        Updated state with files populated and supervisor's final message
    """
    
    # We trigger the supervisor with a custom human message that includes the topic and scope from the advisor.
    initial_message = HumanMessage(
        content=SUPERVISOR_INITIAL_MESSAGE_TEMPLATE.format(
            research_topic=state["research_topic"],
            research_scope=state["research_scope"]
        )
    )
    
    # We invoke the supervisor with the initial message and the empty files and todos.
    result = await supervisor_deep_agent.ainvoke({
        "messages": [initial_message],
        "files": state.get("files", {}),
        "todos": state.get("todos", [])
    })
    
    # We return the updated state with the files populated and supervisor summary (not in messages).
    return {
        "files": result["files"],  # All research files created by subagents + index
        "supervisor_summary": result["messages"][-1].content,  # Store content only (hidden from user)
        # Pass through unchanged fields, which will be used by the report writer.
        "research_topic": state["research_topic"],
        "research_scope": state["research_scope"]
    }

