"""
Deep Agent report writer for final research report generation.

Reads research findings from virtual filesystem and synthesizes
comprehensive markdown report.
"""

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage

from src.state import FullResearchState
from src.config import get_report_writer_model
from src.report_writer.prompts import (
    REPORT_WRITER_SYSTEM_PROMPT,
    REPORT_WRITER_INITIAL_MESSAGE_TEMPLATE
)


# ===== CREATE REPORT WRITER DEEP AGENT =====
report_writer_agent = create_deep_agent(
    model=get_report_writer_model(),
    tools=[],
    system_prompt=REPORT_WRITER_SYSTEM_PROMPT,
    subagents=[]
)

## Why a deep agent for a report writer?
# We want to use the file system tools to read the findings and synthesize the report.
# The researcher is fully in charge of investigating and collecting findings and sources.
# That is the equivalent to "compressing the web" into an organized file system.
# The report writer is then in charge of synthesizing the findings into a comprehensive report.


# ===== WRAPPER FUNCTION FOR MAIN GRAPH =====

async def write_final_report(state: FullResearchState) -> dict:
    """
    Generate final research report using a Deep Agent.
    
    Reads research findings from state["files"] and synthesizes
    into comprehensive markdown report.
    
    Args:
        state: State from supervisor containing research_topic, research_scope,
               files (all research findings), and supervisor's summary message
               
    Returns:
        Updated state with final_report field populated and report in message
    """
    
    # Extract supervisor's summary from dedicated field
    # This summary is hidden from the user - it's just context for the report writer
    supervisor_summary = state.get("supervisor_summary", "Research completed.")
    
    # Prepare initial message with all context to the report writer.
    initial_message = HumanMessage(
        content=REPORT_WRITER_INITIAL_MESSAGE_TEMPLATE.format(
            research_topic=state["research_topic"],
            research_scope=state["research_scope"],
            supervisor_summary=supervisor_summary
        )
    )
    
    # Invoke deep agent with files from supervisor (file system is shared across all deep agents)
    result = await report_writer_agent.ainvoke({
        "messages": [initial_message],
        "files": state.get("files", {}),  # All research files
        "todos": []
    })
    
    # Extract final report from last message
    final_report_content = result["messages"][-1].content
    
    # Return report in both final_report field and message to the user.
    return {
        "final_report": final_report_content,
        "messages": [result["messages"][-1]] 
    }
