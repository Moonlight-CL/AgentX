"""
AWS DB Evaluation MCP Server

This module provides MCP server tools for analyzing RDS MySQL instances
and calculating Aurora conversion and RDS replacement costs.
"""

__version__ = "0.1.0"

from .server import server, run
