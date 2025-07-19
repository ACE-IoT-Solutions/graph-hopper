"""
Status command for checking Grasshopper API health.
"""

import click
import sys
import httpx
from .base import get_client_and_url


@click.command()
@click.pass_context
def status(ctx):
    """Check the status of the Grasshopper API"""
    client, base_url = get_client_and_url(ctx)
    
    try:
        response = client.client.get(f"{base_url}/api/operations/hello")
        response.raise_for_status()
        data = response.json()
        
        click.echo(f"✓ Grasshopper API is accessible at {base_url}")
        if isinstance(data, dict) and 'message' in data:
            click.echo(f"  Message: {data['message']}")
        else:
            click.echo(f"  Response: {data}")
            
    except httpx.RequestError as e:
        click.echo(f"✗ Cannot connect to Grasshopper API at {base_url}: {e}", err=True)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        click.echo(f"✗ HTTP error {e.response.status_code}: {e.response.text}", err=True)
        sys.exit(1)
