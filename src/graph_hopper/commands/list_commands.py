"""
List commands for retrieving file listings from Grasshopper API.
"""

import click
import json
from .base import get_client_and_url


@click.command()
@click.option('--limit', '-l', default=5, help='Number of graphs to retrieve (default: 5)')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def list_graphs(ctx, limit: int, output_json: bool):
    """List available TTL network files from the Grasshopper API"""
    client, _ = get_client_and_url(ctx)
    
    ttl_files = client.get_ttl_list()
    
    # Create file info for TTL files only
    files = []
    for filename in ttl_files:
        files.append({
            'filename': filename,
            'type': 'ttl',
            'description': 'TTL network file'
        })
    
    # Sort by filename and limit results
    files.sort(key=lambda x: x['filename'])
    limited_files = files[:limit]
    
    if output_json:
        click.echo(json.dumps(limited_files, indent=2))
    else:
        if not limited_files:
            click.echo("No TTL network files found.")
            return
        
        click.echo(f"Found {len(files)} total TTL files. Showing top {len(limited_files)}:")
        click.echo()
        
        for i, file_info in enumerate(limited_files, 1):
            click.echo(f"{i}. {file_info['filename']} - {file_info['description']}")


@click.command()
@click.option('--limit', '-l', default=5, help='Number of comparison files to retrieve (default: 5)')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def list_compares(ctx, limit: int, output_json: bool):
    """List available TTL comparison files from the Grasshopper API"""
    client, _ = get_client_and_url(ctx)
    
    compare_files = client.get_ttl_compare_list()
    
    # Create file info for comparison files only
    files = []
    for filename in compare_files:
        files.append({
            'filename': filename,
            'type': 'compare',
            'description': 'TTL comparison file'
        })
    
    # Sort by filename and limit results
    files.sort(key=lambda x: x['filename'])
    limited_files = files[:limit]
    
    if output_json:
        click.echo(json.dumps(limited_files, indent=2))
    else:
        if not limited_files:
            click.echo("No TTL comparison files found.")
            return
        
        click.echo(f"Found {len(files)} total comparison files. Showing top {len(limited_files)}:")
        click.echo()
        
        for i, file_info in enumerate(limited_files, 1):
            click.echo(f"{i}. {file_info['filename']} - {file_info['description']}")
