"""Tools for research advisor.

This module provides the tools used by the advisor agent:
1. search_web: Search for current/niche information
2. execute_research: Trigger to launch deep research
"""

from typing import List
import os

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient

from src.advisor.prompts import SEARCH_SUMMARIZER_PROMPT
from src.config import get_researcher_model


# ===== CONFIGURATION =====
# This model is only used to summarize the search results for the advisor to use in the conversation.
model = get_researcher_model()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# ===== TOOLS =====

@tool(parse_docstring=True)
def search_web(queries: List[str], research_focus: str) -> str:
    """Tool to search the web for recent news and niche information.

    Use this tool when the user's research focus is a current event, recent news,
    or a niche topic that is not well known or mainstream.

    When to use:
    - Current events, recent news, or niche topics
    - Topics that are not well known or mainstream
    - Topics that need clarification or are not well defined
    
    Args:
        queries: A list of 2-3 specific search queries (avoid generic queries)
        research_focus: The focus of the research based on conversation with user

    Returns:
        A string summarizing the search results
    """
    search_results = []
    for query in queries:
        # Get results for each query
        query_results = tavily_client.search(query, max_results=2)
        search_results.append(query_results)
    
    # Summarize results with research focus
    system_message = SystemMessage(content=SEARCH_SUMMARIZER_PROMPT.format(
        research_focus=research_focus
    ))
    results_to_summarize = HumanMessage(content=str(search_results))
    results_summary = model.invoke([system_message, results_to_summarize]).content
    
    return results_summary


@tool(parse_docstring=True)
def execute_research(research_topic: str, research_scope: str) -> str:
    """Tool to launch comprehensive deep research.

    Use this when the user has confirmed they want to proceed with research.
    This launches a full research process that will deliver a detailed report.

    When to use:
    - When the user clearly confirms (says "yes", "sounds good", "let's do it", etc.)
    - When you understand what they want and they've agreed to proceed

    When NOT to use:
    - When the user is still exploring or refining what they want to research
    - When the user needs more clarification
    
    Args:
        research_topic: Clear, concise topic (e.g., "AI Impact on Software Engineering Careers")
        research_scope: Capture what the user said and the conversation context - nothing more. Helps define the scope and angle of the research.

    Returns:
        Confirmation message that research has been launched
    """
    return f"Research launched: {research_topic}\n\nScope: {research_scope}\n\n"

