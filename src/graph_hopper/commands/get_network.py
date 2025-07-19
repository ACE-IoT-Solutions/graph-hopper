"""
Get network command for retrieving specific TTL files.
"""

import click
import json
import sys
from typing import Optional
from .base import get_client_and_url


@click.command()
@click.argument('filename')
@click.option('--output', '-o', help='Output file path (default: stdout)')
@click.option('--json', 'output_json', is_flag=True, 
              help='Output network data as JSON instead of raw TTL')
@click.pass_context
def get_network(ctx, filename: str, output: Optional[str], output_json: bool):
    """Get data for a specific TTL file (raw TTL by default, JSON with --json)"""
    client, _ = get_client_and_url(ctx)
    
    if output_json:
        # Get network data as JSON
        data = client.get_ttl_network(filename)
        if data is None:
            sys.exit(1)
        content = json.dumps(data, indent=2)
    else:
        # Get raw TTL file
        content = client.get_ttl_file(filename)
        if content is None:
            sys.exit(1)
    
    if output:
        # Write to file
        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            file_format = "JSON" if output_json else "TTL"
            click.echo(f"✓ {file_format} data saved to {output}")
        except IOError as e:
            click.echo(f"✗ Error writing to file: {e}", err=True)
            sys.exit(1)
    else:
        # Output to stdout
        click.echo(content)
