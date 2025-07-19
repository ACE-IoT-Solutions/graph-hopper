"""
Download recent command for bulk downloading TTL files.
"""

import click
import json
import sys
from pathlib import Path
from datetime import datetime
from .base import get_client_and_url


@click.command()
@click.option('--count', '-c', default=5, help='Number of recent graphs to download (default: 5)')
@click.option('--output-dir', '-d', default='data/network_snapshots',
              help='Output directory for downloaded files (default: data/network_snapshots)')
@click.option('--json', 'output_json', is_flag=True,
              help='Download network data as JSON instead of raw TTL files')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress information')
@click.pass_context
def download_recent(ctx, count: int, output_dir: str, output_json: bool, verbose: bool):
    """Download the most recent network graph files (raw TTL by default, JSON with --json)"""
    
    client, _ = get_client_and_url(ctx)
    
    if verbose:
        click.echo("Fetching list of available TTL files...")
    
    # Get list of TTL files
    ttl_files = client.get_ttl_list()
    
    if not ttl_files:
        click.echo("No TTL files found on the server.")
        return
    
    # Sort files by filename (which includes timestamp) and get the most recent ones
    ttl_files.sort(reverse=True)
    files_to_download = ttl_files[:count]
    
    if verbose:
        click.echo(f"Found {len(ttl_files)} total files. Downloading {len(files_to_download)} most recent:")
        for filename in files_to_download:
            click.echo(f"  - {filename}")
        click.echo()
    
    # Create output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        click.echo(f"✗ Error creating output directory: {e}", err=True)
        sys.exit(1)
    
    # Download files
    successful_downloads = 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in files_to_download:
        if verbose:
            click.echo(f"Downloading {filename}...")
        
        try:
            if output_json:
                # Download as JSON network data
                data = client.get_ttl_network(filename)
                if data is None:
                    if verbose:
                        click.echo(f"  ✗ Failed to download {filename}")
                    continue
                
                content = json.dumps(data, indent=2)
                # Create JSON filename with timestamp
                base_name = filename.replace('.ttl', '').replace('.TTL', '')
                output_filename = f"{base_name}_{timestamp}.json"
                
            else:
                # Download raw TTL file
                content = client.get_ttl_file(filename)
                if content is None:
                    if verbose:
                        click.echo(f"  ✗ Failed to download {filename}")
                    continue
                
                # Create TTL filename with timestamp
                base_name = filename.replace('.ttl', '').replace('.TTL', '')
                output_filename = f"{base_name}_{timestamp}.ttl"
            
            # Write file
            file_path = output_path / output_filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            successful_downloads += 1
            
            if verbose:
                file_format = "JSON" if output_json else "TTL"
                click.echo(f"  ✓ Saved as {output_filename} ({file_format} format)")
        
        except Exception as e:
            if verbose:
                click.echo(f"  ✗ Error downloading {filename}: {e}")
            continue
    
    # Summary
    file_format = "JSON" if output_json else "TTL"
    click.echo(f"✓ Successfully downloaded {successful_downloads} {file_format} files to {output_dir}")
    
    if successful_downloads < len(files_to_download):
        failed_count = len(files_to_download) - successful_downloads
        click.echo(f"⚠ {failed_count} files failed to download")
        if not verbose:
            click.echo("  Use --verbose to see detailed error information")
