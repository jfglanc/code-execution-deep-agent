"""Research tools for Deep Agent researchers."""

from langchain_core.tools import tool
from tavily import TavilyClient

from src.config import TAVILY_CONFIG


# Initialize Tavily client
tavily_client = TavilyClient()


@tool
def tavily_search(query: str) -> str:
    """Search the web for information.
    
    Performs a single focused search query using Tavily API.
    Returns formatted results with source numbering for easy citation.
    
    Note: You can call this tool multiple times in parallel for different queries.
    Example: Search for "React learning curve" and "React hiring market" in the same turn.
    
    Args:
        query: A single search query to execute
    
    Returns:
        Formatted string with search results including titles, URLs, and content summaries
    """
    # Execute search using config
    results = tavily_client.search(
        query,
        max_results=TAVILY_CONFIG["max_results"],
        topic=TAVILY_CONFIG["topic"],
        include_raw_content=TAVILY_CONFIG["include_raw_content"]
    )
    
    # Format results
    formatted = f"Search results for: {query}\n\n"
    
    for i, result in enumerate(results['results'], 1):
        formatted += f"--- SOURCE {i}: {result['title']} ---\n"
        formatted += f"URL: {result['url']}\n"
        formatted += f"CONTENT:\n{result['content']}\n"
        formatted += "-" * 80 + "\n\n"
    
    return formatted

