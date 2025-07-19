import click
import httpx
import json
from typing import Optional, List, Dict, Any
import sys
from urllib.parse import urlparse
import re
from pathlib import Path
import glob
import rdflib


def parse_host_url(host_input: Optional[str]) -> str:
    """
    Parse host input and return a complete URL with defaults.
    
    Supports various input formats:
    - Simple hostname/IP: "localhost" -> "http://localhost:8000"
    - With port: "localhost:9000" -> "http://localhost:9000" 
    - With scheme: "http://localhost" -> "http://localhost:8000"
    - Full URL: "http://localhost:9000" -> "http://localhost:9000"
    - HTTPS: "https://api.example.com:8443" -> "https://api.example.com:8443"
    - Trailing slash handling: "localhost/" -> "http://localhost:8000"
    
    Args:
        host_input: The host string to parse
        
    Returns:
        Complete URL string with scheme, host, and port
        
    Raises:
        ValueError: If the host input is invalid or empty
    """
    if not host_input or not host_input.strip():
        raise ValueError("Host URL cannot be empty")
    
    host_input = host_input.strip()
    
    # Check if it's already a complete URL with scheme
    if '://' in host_input:
        parsed = urlparse(host_input)
        
        # Validate that we have a valid scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid host URL: {host_input}")
        
        # Remove trailing slash if it's just "/" (no actual path)
        path = parsed.path
        if path == "/":
            path = ""
        
        # If no port specified, add default port
        if not parsed.port:
            default_port = 443 if parsed.scheme == 'https' else 8000
            if ':' not in parsed.netloc:
                # No port in netloc, add it
                netloc_with_port = f"{parsed.netloc}:{default_port}"
                return f"{parsed.scheme}://{netloc_with_port}{path}"
        
        # Port already specified, just clean up the path
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    # Handle cases without scheme
    # First, strip trailing slash if it exists (for cases without scheme)
    if host_input.endswith('/'):
        host_input = host_input.rstrip('/')
    
    # First check for IPv6 cases (must come before general colon check)
    if host_input.startswith('[') and ']:' in host_input:
        # IPv6 with port: "[::1]:9000"
        return f"http://{host_input}"
    elif host_input.startswith('[') and host_input.endswith(']'):
        # IPv6 without port: "[::1]"
        return f"http://{host_input}:8000"
    elif ':' in host_input:
        # Format: "hostname:port" (non-IPv6)
        return f"http://{host_input}"
    else:
        # Simple hostname or IP without port
        return f"http://{host_input}:8000"


class GrasshopperClient:
    """Client for interacting with the Grasshopper API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
    
    def get_ttl_list(self) -> List[str]:
        """Get list of available TTL files"""
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl")
            response.raise_for_status()
            
            # The API returns a generic response, so we need to handle it appropriately
            data = response.json()
            
            # Handle different possible response formats
            if isinstance(data, dict):
                if 'file_list' in data:
                    return data['file_list']
                elif 'files' in data:
                    return data['files']
                # If it's a dict with other keys, try to extract file-like values
                elif len(data) == 1:
                    # Single key dict - might be the file list
                    key = list(data.keys())[0]
                    if isinstance(data[key], list):
                        return data[key]
                # Return empty list for unknown dict formats
                return []
            elif isinstance(data, list):
                return data
            else:
                # For any other type, try to convert to list or return empty
                return []
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return []
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return []
        except Exception as e:
            click.echo(f"Unexpected error parsing response: {e}", err=True)
            return []
    
    def get_ttl_compare_list(self) -> List[str]:
        """Get list of available TTL comparison files"""
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl_compare")
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and 'file_list' in data:
                return data['file_list']
            else:
                return []
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return []
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return []
    
    def get_ttl_network(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get network data for a specific TTL file"""
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl_network/{filename}")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return None
    
    def get_ttl_file(self, filename: str) -> Optional[str]:
        """Get raw TTL file content"""
        try:
            # Use text/turtle Accept header to get raw TTL content
            headers = {"Accept": "text/turtle"}
            response = self.client.get(f"{self.base_url}/api/operations/ttl_file/{filename}", headers=headers)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return None
    
    def close(self):
        """Close the HTTP client"""
        self.client.close()


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


def require_host(ctx):
    """Helper function to ensure host is provided for API commands"""
    if not ctx.obj.get('client') or not ctx.obj.get('base_url'):
        click.echo("Error: The --host/-h option is required for this command.", err=True)
        click.echo("Use: graph-hopper -h <host> <command>", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', '-l', default=5, help='Number of graphs to retrieve (default: 5)')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def list_graphs(ctx, limit: int, output_json: bool):
    """List available TTL network files from the Grasshopper API"""
    require_host(ctx)
    client: GrasshopperClient = ctx.obj['client']
    
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


@cli.command()
@click.option('--limit', '-l', default=5, help='Number of comparison files to retrieve (default: 5)')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def list_compares(ctx, limit: int, output_json: bool):
    """List available TTL comparison files from the Grasshopper API"""
    require_host(ctx)
    client: GrasshopperClient = ctx.obj['client']
    
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
            click.echo("No comparison files found.")
            return
        
        click.echo(f"Found {len(files)} total comparison files. Showing top {len(limited_files)}:")
        click.echo()
        
        for i, file_info in enumerate(limited_files, 1):
            click.echo(f"{i}. {file_info['filename']} - {file_info['description']}")


@cli.command()
@click.argument('filename')
@click.option('--output', '-o', help='Output file path (default: stdout)')
@click.option('--json', 'output_json', is_flag=True, help='Output network data as JSON instead of raw TTL')
@click.pass_context
def get_network(ctx, filename: str, output: Optional[str], output_json: bool):
    """Get data for a specific TTL file (raw TTL by default, JSON with --json)"""
    require_host(ctx)
    client: GrasshopperClient = ctx.obj['client']
    
    if output_json:
        # Get network data as JSON
        data = client.get_ttl_network(filename)
        if data is None:
            sys.exit(1)
        content = json.dumps(data, indent=2)
    else:
        # Get raw TTL file content
        data = client.get_ttl_file(filename)
        if data is None:
            sys.exit(1)
        content = data
    
    if output:
        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            click.echo(f"Data saved to {output}")
        except IOError as e:
            click.echo(f"Error writing to file: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(content)


@cli.command()
@click.option('--count', '-c', default=5, help='Number of recent graphs to download (default: 5)')
@click.option('--output-dir', '-d', default='data/network_snapshots', 
              help='Output directory for downloaded files (default: data/network_snapshots)')
@click.option('--json', 'download_json', is_flag=True, help='Download network data as JSON instead of raw TTL files')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress information')
@click.pass_context
def download_recent(ctx, count: int, output_dir: str, download_json: bool, verbose: bool):
    """Download the most recent network graph files (raw TTL by default, JSON with --json)"""
    from pathlib import Path
    from datetime import datetime
    
    require_host(ctx)
    client: GrasshopperClient = ctx.obj['client']
    
    if verbose:
        click.echo("Fetching list of available TTL files...")
    
    # Get list of TTL files
    ttl_files = client.get_ttl_list()
    
    if not ttl_files:
        click.echo("No TTL files found on the server.")
        return
    
    if verbose:
        click.echo(f"Found {len(ttl_files)} TTL files")
    
    # Sort files by name (assuming filename contains timestamp/date info for recency)
    # Most recent should be last when sorted alphabetically if using ISO date format
    ttl_files.sort(reverse=True)
    
    # Get the most recent files up to the specified count
    recent_files = ttl_files[:count]
    
    if verbose:
        click.echo(f"Selecting {len(recent_files)} most recent files:")
        for i, filename in enumerate(recent_files, 1):
            click.echo(f"  {i}. {filename}")
    
    # Create output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        if verbose:
            click.echo(f"Output directory: {output_path.absolute()}")
    except OSError as e:
        click.echo(f"Error creating output directory '{output_dir}': {e}", err=True)
        sys.exit(1)
    
    # Download each file's data
    successful_downloads = 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    file_type = "network JSON data" if download_json else "TTL files"
    click.echo(f"Downloading {len(recent_files)} {file_type}...")
    
    with click.progressbar(recent_files, label='Downloading') as files:
        for filename in files:
            try:
                if download_json:
                    # Get network data as JSON
                    data = client.get_ttl_network(filename)
                    if data is None:
                        if verbose:
                            click.echo(f"\n  Failed to get network data for {filename}")
                        continue
                    
                    # Create output filename: remove .ttl extension and add timestamp and .json
                    base_name = filename.replace('.ttl', '').replace('.TTL', '')
                    output_filename = f"{base_name}_{timestamp}.json"
                    output_file_path = output_path / output_filename
                    
                    # Write network data to file as JSON
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    # Get raw TTL file content
                    data = client.get_ttl_file(filename)
                    if data is None:
                        if verbose:
                            click.echo(f"\n  Failed to get TTL data for {filename}")
                        continue
                    
                    # Create output filename: keep original name and add timestamp
                    base_name = filename.replace('.ttl', '').replace('.TTL', '')
                    output_filename = f"{base_name}_{timestamp}.ttl"
                    output_file_path = output_path / output_filename
                    
                    # Write TTL data to file
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(data)
                
                successful_downloads += 1
                
                if verbose:
                    click.echo(f"\n  ✓ {filename} → {output_file_path.name}")
                    
            except Exception as e:
                if verbose:
                    click.echo(f"\n  ✗ Error downloading {filename}: {e}")
                continue
    
    # Summary
    click.echo("\nDownload complete!")
    click.echo(f"Successfully downloaded: {successful_downloads}/{len(recent_files)} files")
    click.echo(f"Files saved to: {output_path.absolute()}")
    
    if successful_downloads < len(recent_files):
        failed_count = len(recent_files) - successful_downloads
        click.echo(f"Failed downloads: {failed_count}")
        if not verbose:
            click.echo("Use --verbose flag for detailed error information")


@cli.command()
@click.pass_context
def status(ctx):
    """Check the status of the Grasshopper API"""
    require_host(ctx)
    client: GrasshopperClient = ctx.obj['client']
    base_url = ctx.obj['base_url']
    
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


@cli.command()
@click.option('--input-dir', '-i', default='data/network_snapshots',
              help='Directory containing TTL files to merge (default: data/network_snapshots)')
@click.option('--input-pattern', '-p', default='*.ttl',
              help='File pattern to match (default: *.ttl)')
@click.option('--output', '-o', default='data/merged_graph.ttl',
              help='Output file path for merged graph (default: data/merged_graph.ttl)')
@click.option('--verbose', '-v', is_flag=True,
              help='Show verbose output including statistics')
def merge_graphs(input_dir, input_pattern, output, verbose):
    """Merge multiple TTL files into a single RDF graph"""
    try:
        input_path = Path(input_dir)
        if not input_path.exists():
            click.echo(f"✗ Input directory does not exist: {input_dir}", err=True)
            sys.exit(1)
        
        if not input_path.is_dir():
            click.echo(f"✗ Input path is not a directory: {input_dir}", err=True)
            sys.exit(1)
        
        # Find TTL files matching pattern
        ttl_files = list(input_path.glob(input_pattern))
        
        if not ttl_files:
            click.echo(f"⚠ No TTL files found matching pattern '{input_pattern}' in {input_dir}")
            
            # Create empty output file
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            empty_graph = rdflib.Graph()
            empty_graph.serialize(destination=str(output_path), format='turtle')
            
            click.echo(f"✓ Created empty TTL file: {output}")
            return
        
        if verbose:
            click.echo(f"Found {len(ttl_files)} TTL files:")
            for file_path in sorted(ttl_files):
                click.echo(f"  - {file_path.name}")
        
        # Create merged graph
        merged_graph = rdflib.Graph()
        parsed_files = 0
        total_triples = 0
        parse_errors = []
        
        for ttl_file in ttl_files:
            try:
                file_graph = rdflib.Graph()
                file_graph.parse(str(ttl_file), format='turtle')
                
                # Add triples from this file to merged graph
                for triple in file_graph:
                    merged_graph.add(triple)
                
                parsed_files += 1
                file_triple_count = len(file_graph)
                total_triples += file_triple_count
                
                if verbose:
                    click.echo(f"  Parsed {ttl_file.name}: {file_triple_count} triples")
                    
            except Exception as e:
                parse_errors.append((ttl_file.name, str(e)))
                if verbose:
                    click.echo(f"  ✗ Failed to parse {ttl_file.name}: {e}")
        
        if parse_errors:
            click.echo(f"⚠ Warning: Failed to parse {len(parse_errors)} files:", err=True)
            for filename, error in parse_errors:
                click.echo(f"  - {filename}: {error}", err=True)
        
        if parsed_files == 0:
            click.echo("✗ No files could be parsed successfully", err=True)
            sys.exit(1)
        
        # Write merged graph to output file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        merged_graph.serialize(destination=str(output_path), format='turtle')
        
        # Statistics
        merged_triple_count = len(merged_graph)
        duplicates_removed = total_triples - merged_triple_count
        
        click.echo(f"✓ Successfully merged {parsed_files} TTL files")
        click.echo(f"  Output: {output}")
        click.echo(f"  Unique triples: {merged_triple_count}")
        
        if verbose or duplicates_removed > 0:
            click.echo(f"  Total triples processed: {total_triples}")
            click.echo(f"  Duplicates removed: {duplicates_removed}")
        
    except Exception as e:
        click.echo(f"✗ Error merging graphs: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)

