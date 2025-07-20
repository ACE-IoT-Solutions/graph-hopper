"""
Check-graph command for analyzing TTL graphs for BACnet network issues.
"""

import click
import sys
from pathlib import Path
from rdflib import Graph

from ..graph_checks import (
    check_duplicate_device_ids,
    check_duplicate_networks,
    check_duplicate_bbmds,
    check_orphaned_devices,
    format_human_readable,
    format_json_output
)


@click.command()
@click.argument('ttl_file', type=click.Path(exists=True, path_type=Path))
@click.option('--issue', '-i', 
              type=click.Choice(['duplicate-device-id', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error', 'orphaned-devices', 'all']),
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
    
    # Determine which issues to check
    if issue == 'all':
        issues_to_check = ['duplicate-device-id', 'orphaned-devices', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error']
    elif issue in ['duplicate-network', 'duplicate-router']:
        issues_to_check = ['duplicate-network', 'duplicate-router']
    elif issue in ['duplicate-bbmd-warning', 'duplicate-bbmd-error']:
        issues_to_check = ['duplicate-bbmd-warning', 'duplicate-bbmd-error']
    else:
        issues_to_check = [issue]
    
    all_issues = {}
    all_affected_triples = []
    
    # Check each issue type
    for issue_type in issues_to_check:
        if issue_type == 'duplicate-device-id':
            issues, affected_triples = check_duplicate_device_ids(graph, verbose)
            all_issues[issue_type] = issues
            all_affected_triples.extend(affected_triples)
        elif issue_type == 'orphaned-devices':
            issues, affected_triples = check_orphaned_devices(graph, verbose)
            all_issues[issue_type] = issues
            all_affected_triples.extend(affected_triples)
        elif issue_type in ['duplicate-network', 'duplicate-router']:
            # The duplicate network function returns both types in one call
            if 'duplicate-network' not in all_issues and 'duplicate-router' not in all_issues:
                issues, affected_triples = check_duplicate_networks(graph, verbose)
                # Separate the issues by type
                network_issues = [i for i in issues if i['issue_type'] == 'duplicate-network']
                router_issues = [i for i in issues if i['issue_type'] == 'duplicate-router']
                all_issues['duplicate-network'] = network_issues
                all_issues['duplicate-router'] = router_issues
                all_affected_triples.extend(affected_triples)
        elif issue_type in ['duplicate-bbmd-warning', 'duplicate-bbmd-error']:
            # The duplicate BBMD function returns both types in one call
            if 'duplicate-bbmd-warning' not in all_issues and 'duplicate-bbmd-error' not in all_issues:
                issues, affected_triples = check_duplicate_bbmds(graph, verbose)
                # Separate the issues by type
                warning_issues = [i for i in issues if i['issue_type'] == 'duplicate-bbmd-warning']
                error_issues = [i for i in issues if i['issue_type'] == 'duplicate-bbmd-error']
                all_issues['duplicate-bbmd-warning'] = warning_issues
                all_issues['duplicate-bbmd-error'] = error_issues
                all_affected_triples.extend(affected_triples)
    
    # Output results
    if output_json:
        # Filter the results based on what was requested
        filtered_issues = {}
        if issue == 'all':
            filtered_issues = all_issues
        elif issue == 'orphaned-devices':
            filtered_issues = {'orphaned-devices': all_issues.get('orphaned-devices', [])}
        elif issue == 'duplicate-network':
            filtered_issues = {'duplicate-network': all_issues.get('duplicate-network', [])}
        elif issue == 'duplicate-router':
            filtered_issues = {'duplicate-router': all_issues.get('duplicate-router', [])}
        elif issue == 'duplicate-bbmd-warning':
            filtered_issues = {'duplicate-bbmd-warning': all_issues.get('duplicate-bbmd-warning', [])}
        elif issue == 'duplicate-bbmd-error':
            filtered_issues = {'duplicate-bbmd-error': all_issues.get('duplicate-bbmd-error', [])}
        else:
            filtered_issues = {issue: all_issues.get(issue, [])}
        
        click.echo(format_json_output(filtered_issues))
    else:
        # Human-readable output
        output_issues = []
        if issue == 'all':
            output_issues = ['duplicate-device-id', 'orphaned-devices', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error']
        elif issue in ['duplicate-network', 'duplicate-router']:
            output_issues = [issue] 
        elif issue in ['duplicate-bbmd-warning', 'duplicate-bbmd-error']:
            output_issues = [issue]
        else:
            output_issues = [issue]
            
        for issue_type in output_issues:
            if issue_type in all_issues:
                result = format_human_readable(all_issues[issue_type], issue_type, verbose)
                if result.strip():
                    click.echo(result)
        
        if verbose and all_affected_triples:
            click.echo("Affected triples:")
            for triple in all_affected_triples[:20]:  # Limit to first 20 to avoid overwhelming output
                click.echo(f"  {triple[0]} {triple[1]} {triple[2]}")
            if len(all_affected_triples) > 20:
                click.echo(f"  ... and {len(all_affected_triples) - 20} more triples")
    
    # Exit with error code if issues were found (for scripting)
    total_issues = sum(len(issues) for issues in all_issues.values())
    if total_issues > 0:
        sys.exit(1)
    else:
        sys.exit(0)
