#!/usr/bin/env python3
"""Agent graph definition and interactive runner.

This module creates the agent graph using configuration from config.py
and provides an interactive CLI for user interaction.
"""

import sys

from langchain_core.messages import HumanMessage

from deepagents import create_deep_agent

from agent.config import (
    ANTHROPIC_API_KEY,
    INTERRUPT_ON,
    SYSTEM_PROMPT,
    backend,
    model,
    skills_middleware,
)

# Create the agent graph directly
agent = create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    backend=backend,
    middleware=[skills_middleware],
    #interrupt_on=INTERRUPT_ON,
)

