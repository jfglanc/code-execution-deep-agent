"""
Research subagent configuration for Deep Agents.

This subagent is spawned by the supervisor to conduct focused research
on specific subtopics. It has access to web search and sharedfile system tools.
"""

from src.researcher.tools import tavily_search
from src.researcher.prompts import RESEARCHER_SYSTEM_PROMPT
from src.config import get_researcher_model


# Research subagent configuration
# Used by supervisor's SubAgentMiddleware to create research-agent instances
research_subagent = {
    "name": "research-agent",
    
    "description": (
        "Delegate focused research to this agent when you need comprehensive investigation "
        "of a specific subtopic with targeted research questions. "
        "\n\n"
        "Usage: Provide clear subtopic, directory path, and 2-4 specific questions. "
        "\n\n"
        "The agent will:\n"
        "- Conduct web searches to gather information\n"
        "- Save raw search results to files for traceability\n"
        "- Write comprehensive findings.md with citations\n"
        "- Create sources.json with all source metadata\n"
        "- Return summary with file paths (not full content)\n"
        "\n"
        "**Important**: Only delegate ONE subtopic per agent. For multiple subtopics, spawn multiple agents."
    ),
    
    "system_prompt": RESEARCHER_SYSTEM_PROMPT,
    
    "tools": [tavily_search],
    
    "model": get_researcher_model()
}

