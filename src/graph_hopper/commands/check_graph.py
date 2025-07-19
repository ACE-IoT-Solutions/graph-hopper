"""
Check-graph command for analyzing TTL graphs for BACnet network issues.
"""

import click
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import rdflib
from rdflib import Graph, Namespace


# BACnet namespace from the real data
BACNET_NS = Namespace("http://data.ashrae.org/bacnet/2020#")


def check_duplicate_device_ids(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for duplicate device IDs across different networks/subnets.
    
    Args:
        graph: The RDF graph to analyze
        verbose: Whether to include detailed triple information
        
    Returns:
        Tuple of (issues_list, affected_triples)
    """
    issues = []
    affected_triples = []
    
    try:
        # Find all devices and their device instances
        device_instances = {}
        device_networks = {}
        
        # First pass: collect all devices with their device instances
        for device, predicate, device_instance in graph.triples((None, BACNET_NS['device-instance'], None)):
            device_id = str(device_instance)
            if device_id not in device_instances:
                device_instances[device_id] = []
            device_instances[device_id].append(device)
        
        # Second pass: find network relationships for each device
        for device_id, devices in device_instances.items():
            for device in devices:
                networks = []
                
                # Check for device-on-network relationships
                for _, _, network in graph.triples((device, BACNET_NS['device-on-network'], None)):
                    networks.append((str(network), 'network'))
                
                # Check for device-on-subnet relationships  
                for _, _, subnet in graph.triples((device, BACNET_NS['device-on-subnet'], None)):
                    networks.append((str(subnet), 'subnet'))
                
                if networks:
                    device_networks[str(device)] = {
                        'device_id': device_id,
                        'networks': networks
                    }
        
        # Third pass: find duplicate device IDs across different networks
        for device_id, devices in device_instances.items():
            if len(devices) > 1:
                # Check if these devices are on different networks
                network_sets = []
                device_info_list = []
                
                for device in devices:
                    device_str = str(device)
                    if device_str in device_networks:
                        networks = device_networks[device_str]['networks']
                        network_sets.extend(networks)
                        device_info_list.append({
                            'device': device_str,
                            'networks': networks
                        })
                
                # If we have multiple unique networks, it's a duplicate issue
                unique_networks = set(network_sets)
                if len(unique_networks) > 1:
                    # Flatten device info for the issue report
                    devices_flat = []
                    for device_info in device_info_list:
                        for network, network_type in device_info['networks']:
                            devices_flat.append({
                                'device': device_info['device'],
                                'network': network,
                                'network_type': network_type
                            })
                    
                    issue = {
                        'issue_type': 'duplicate-device-id',
                        'device_id': device_id,
                        'device_count': len(devices),
                        'devices': devices_flat,
                        'networks': list(unique_networks)
                    }
                    issues.append(issue)
                    
                    if verbose:
                        # Collect affected triples
                        for device in devices:
                            # Get all triples for this device
                            for triple in graph.triples((device, None, None)):
                                affected_triples.append(triple)
    
    except Exception as e:
        click.echo(f"Error analyzing graph for duplicate device IDs: {e}", err=True)
        return [], []
    
    return issues, affected_triples


def format_human_readable(issues: List[Dict[str, Any]], issue_type: str, verbose: bool = False) -> str:
    """Format issues in human-readable format."""
    if not issues:
        return f"✓ No {issue_type.replace('-', ' ')} issues found"
    
    output = []
    output.append(f"⚠ Found {len(issues)} {issue_type.replace('-', ' ')} issue(s):")
    output.append("")
    
    for i, issue in enumerate(issues, 1):
        if issue_type == 'duplicate-device-id':
            output.append(f"{i}. Device ID {issue['device_id']} appears on {issue['device_count']} different devices:")
            for device_info in issue['devices']:
                network_type = device_info['network_type']
                output.append(f"   • {device_info['device']} on {network_type}: {device_info['network']}")
            output.append("")
    
    return "\n".join(output)


def format_json_output(all_issues: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format issues in JSON format."""
    return json.dumps(all_issues, indent=2)


@click.command()
@click.argument('ttl_file', type=click.Path(exists=True, path_type=Path))
@click.option('--issue', '-i', 
              type=click.Choice(['duplicate-device-id', 'all']),
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
    issues_to_check = ['duplicate-device-id'] if issue == 'duplicate-device-id' else ['duplicate-device-id']
    
    all_issues = {}
    all_affected_triples = []
    
    # Check each issue type
    for issue_type in issues_to_check:
        if issue_type == 'duplicate-device-id':
            issues, affected_triples = check_duplicate_device_ids(graph, verbose)
            all_issues[issue_type] = issues
            all_affected_triples.extend(affected_triples)
    
    # Output results
    if output_json:
        click.echo(format_json_output(all_issues))
    else:
        # Human-readable output
        for issue_type in issues_to_check:
            click.echo(format_human_readable(all_issues[issue_type], issue_type, verbose))
        
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
