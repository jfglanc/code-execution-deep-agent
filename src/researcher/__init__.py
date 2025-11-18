"""Research Deep Agent module using LangChain Deep Agents.

This module replaces the custom research_supervisor and research_agent
with LangChain's Deep Agents framework.
"""

from src.researcher.supervisor import deep_research_supervisor

__all__ = ["deep_research_supervisor"]

