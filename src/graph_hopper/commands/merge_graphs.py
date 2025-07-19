"""
Merge graphs command for combining multiple TTL files.
"""

import click
import sys
from pathlib import Path
from ..utils import find_ttl_files, merge_ttl_files, save_ttl_graph


@click.command()
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
        ttl_files = find_ttl_files(input_path, input_pattern)
        
        if not ttl_files:
            click.echo(f"⚠ No TTL files found matching pattern '{input_pattern}' in {input_dir}")
            
            # Create empty output file
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create and save empty graph
            from rdflib import Graph
            empty_graph = Graph()
            save_ttl_graph(empty_graph, output_path)
            
            click.echo(f"✓ Created empty TTL file: {output}")
            return
        
        if verbose:
            click.echo(f"Found {len(ttl_files)} TTL files:")
            for file_path in sorted(ttl_files):
                click.echo(f"  - {file_path.name}")
        
        # Merge TTL files
        merged_graph, total_triples, parse_errors = merge_ttl_files(ttl_files)
        
        # Report parsing errors
        if parse_errors:
            click.echo(f"⚠ Warning: Failed to parse {len(parse_errors)} files:", err=True)
            for filename, error in parse_errors:
                if verbose:
                    click.echo(f"  - {filename}: {error}", err=True)
                else:
                    click.echo(f"  - {filename}", err=True)
        
        parsed_files = len(ttl_files) - len(parse_errors)
        if parsed_files == 0:
            click.echo("✗ No files could be parsed successfully", err=True)
            sys.exit(1)
        
        # Show per-file statistics in verbose mode
        if verbose:
            for file_path in ttl_files:
                if file_path.name not in [error[0] for error in parse_errors]:
                    # Try to get individual file triple count (this is approximate)
                    try:
                        from rdflib import Graph
                        temp_graph = Graph()
                        temp_graph.parse(str(file_path), format='turtle')
                        click.echo(f"  Parsed {file_path.name}: {len(temp_graph)} triples")
                    except Exception:
                        pass  # Skip if we can't parse again
        
        # Save merged graph
        output_path = Path(output)
        save_ttl_graph(merged_graph, output_path)
        
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
