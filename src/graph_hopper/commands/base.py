"""
Base functionality for CLI commands.

This module provides common functions and utilities used by multiple commands.
"""

import click
import sys
from ..api import GrasshopperClient


def require_host(ctx) -> None:
    """
    Helper function to ensure host is provided for API commands.
    
    Args:
        ctx: Click context object
        
    Raises:
        SystemExit: If host is not provided
    """
    if not ctx.obj.get('client') or not ctx.obj.get('base_url'):
        click.echo("Error: The --host/-h option is required for this command.", err=True)
        click.echo("Use: graph-hopper -h <host> <command>", err=True)
        sys.exit(1)


def get_client_and_url(ctx) -> tuple[GrasshopperClient, str]:
    """
    Get the API client and base URL from context, ensuring they exist.
    
    Args:
        ctx: Click context object
        
    Returns:
        Tuple of (client, base_url)
        
    Raises:
        SystemExit: If host is not provided
    """
    require_host(ctx)
    return ctx.obj['client'], ctx.obj['base_url']
