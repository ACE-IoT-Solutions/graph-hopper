"""
Graph Hopper CLI - Retrieve graphs from Grasshopper API

A Python CLI tool for retrieving BACnet network graphs from the Grasshopper API.
Supports both raw TTL (Turtle/RDF) files and processed JSON network data.
"""

import click
import sys
from typing import Optional

from .api import GrasshopperClient
from .utils import parse_host_url
from .commands import (
    status,
    list_graphs,
    list_compares, 
    get_network,
    download_recent,
    merge_graphs,
    check_graph
)

__all__ = [
    "cli",
    "main",
    "GrasshopperClient",
    "parse_host_url",
]


@click.group()
@click.option('--host', '-h', 
              help='Grasshopper instance URL (e.g., localhost, http://192.168.1.100:9000, https://api.example.com)')
@click.pass_context
def cli(ctx, host: Optional[str]):
    """Graph Hopper CLI - Retrieve graphs from Grasshopper API"""
    ctx.ensure_object(dict)
    
    if host:
        try:
            base_url = parse_host_url(host)
        except ValueError as e:
            click.echo(f"Error parsing host URL: {e}", err=True)
            sys.exit(1)
        
        ctx.obj['client'] = GrasshopperClient(base_url)
        ctx.obj['base_url'] = base_url
    else:
        # For commands that don't need API access
        ctx.obj['client'] = None
        ctx.obj['base_url'] = None


# Add all commands to the CLI group
cli.add_command(status)
cli.add_command(list_graphs)
cli.add_command(list_compares)
cli.add_command(get_network)
cli.add_command(download_recent)
cli.add_command(merge_graphs)
cli.add_command(check_graph)


def main() -> None:
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
