"""
Main graph for Deep Research Agent

Consists of 3 agents:
- Advisor (ReAct loop), which acts as the user's advisor and guides the user through the research process
- Supervisor (Deep Agent), which coordinates the research, delegates research tasks, and stores findings/sources in filesystem
- Report Writer (Deep Agent), which writes the final report based on the findings/sources in the filesystem
"""

from typing_extensions import Literal
from langgraph.graph import StateGraph, START, END

# State
from src.state import FullResearchState

# Agents
from src.advisor.advisor_agent import advisor_agent 
from src.researcher import deep_research_supervisor 
from src.report_writer.report_writer import write_final_report 


# ===== ROUTING LOGIC =====
# It ends the graph while the user is interacting with the advisor agent
# It'll only route to the deep research supervisor if the user approves the research topic and scope
def route_after_advisor(state: FullResearchState) -> Literal["supervisor", "__end__"]:
    """Route to supervisor if approved, otherwise end."""
    if state.get("user_approved"):
        return "supervisor"
    return END


# ===== GRAPH CONSTRUCTION =====
# StateGraph instance
full_builder = StateGraph(FullResearchState)

# Add nodes
full_builder.add_node("advisor", advisor_agent)
full_builder.add_node("supervisor", deep_research_supervisor)
full_builder.add_node("write_report", write_final_report)

# Add edges
full_builder.add_edge(START, "advisor")
full_builder.add_conditional_edges("advisor", route_after_advisor)
full_builder.add_edge("supervisor", "write_report")
full_builder.add_edge("write_report", END)

# Compile
deep_research_agent = full_builder.compile()

