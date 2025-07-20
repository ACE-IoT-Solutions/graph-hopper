"""
Check-graph command for analyzing TTL graphs for BACnet network issues.
"""

import click
import sys
from pathlib import Path
from rdflib import Graph

from ..graph_checks import (
    format_human_readable,
    format_json_output,
    ISSUE_REGISTRY
)


@click.command()
@click.argument('ttl_file', type=click.Path(exists=True, path_type=Path))
@click.option('--issue', '-i', 
              type=click.Choice(ISSUE_REGISTRY.get_cli_choices()),
              default='all',
              help='Specific issue to check for (default: all)')
@click.option('--json', 'output_json', is_flag=True,
              help='Output results in JSON format')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed information including affected triples')
def check_graph(ttl_file: Path, issue: str, output_json: bool, verbose: bool):
    """Analyze TTL graphs for common BACnet network issues.
    
    Checks for problems like duplicate device IDs across different networks/subnets.
    
    TTL_FILE: Path to the TTL file to analyze
    """
    
    if verbose:
        click.echo(f"Loading TTL file: {ttl_file}")
    
    # Load and parse the TTL file
    try:
        graph = Graph()
        graph.parse(str(ttl_file), format='turtle')
        
        if verbose:
            click.echo(f"Loaded {len(graph)} triples")
        
    except Exception as e:
        click.echo(f"✗ Error parsing TTL file: {e}", err=True)
        sys.exit(1)
    
    # Determine which issues to check using the registry
    issues_to_check = ISSUE_REGISTRY.resolve_issues_to_check(issue)
    
    # Execute all checks using the registry
    all_issues, all_affected_triples = ISSUE_REGISTRY.execute_checks(issues_to_check, graph, verbose)
    
    # Output results
    if output_json:
        # Filter the results based on what was requested
        if issue == 'all':
            filtered_issues = all_issues
        else:
            # For specific issues, include only what was requested and related types
            requested_types = ISSUE_REGISTRY.resolve_issues_to_check(issue)
            filtered_issues = {issue_type: all_issues.get(issue_type, []) for issue_type in requested_types if issue_type in all_issues}
        
        click.echo(format_json_output(filtered_issues))
    else:
        # Human-readable output - show all issues that were checked and have results
        issues_to_display = issues_to_check if issue == 'all' else ISSUE_REGISTRY.resolve_issues_to_check(issue)
            
        for issue_type in issues_to_display:
            if issue_type in all_issues:
                result = format_human_readable(all_issues[issue_type], issue_type, verbose)
                if result.strip():
                    click.echo(result)
        
        if verbose and all_affected_triples:
            click.echo("Affected triples:")
            for i, triple in enumerate(all_affected_triples[:20]):  # Limit to first 20 to avoid overwhelming output
                # Triple is a Node, not indexable - convert to string representation
                click.echo(f"  {str(triple)}")
            if len(all_affected_triples) > 20:
                click.echo(f"  ... and {len(all_affected_triples) - 20} more triples")
    
    # Exit with error code if issues were found (for scripting)
    total_issues = sum(len(issues) for issues in all_issues.values())
    if total_issues > 0:
        sys.exit(1)
    else:
        sys.exit(0)
