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


def check_duplicate_networks(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for duplicate network numbers on multiple routers.
    
    Same network number on multiple routers:
    - If routers are on same subnet: duplicate router issue (likely)  
    - If routers are on different subnets: duplicate network issue (likely)
    
    Args:
        graph: The RDF graph to analyze
        verbose: Whether to include detailed triple information
        
    Returns:
        Tuple of (issues_list, affected_triples)
    """
    issues = []
    affected_triples = []
    
    try:
        # Find all routers and their networks/subnets
        router_networks = {}
        
        # First pass: collect all routers with their networks and subnets  
        rdf_type = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        routers_query = graph.triples((None, rdf_type, BACNET_NS['Router']))
        for router, _, _ in routers_query:
            networks = []
            subnets = []
            
            # Get networks for this router
            for _, _, network in graph.triples((router, BACNET_NS['device-on-network'], None)):
                networks.append(str(network))
            
            # Get subnet for this router  
            for _, _, subnet in graph.triples((router, BACNET_NS['device-on-subnet'], None)):
                subnets.append(str(subnet))
            
            if networks:  # Only track routers that have networks
                router_networks[str(router)] = {
                    'networks': networks,
                    'subnets': subnets
                }
        
        # Second pass: group by network number to find duplicates
        network_to_routers = {}
        for router, info in router_networks.items():
            for network in info['networks']:
                if network not in network_to_routers:
                    network_to_routers[network] = []
                network_to_routers[network].append({
                    'router': router,
                    'subnets': info['subnets']
                })
        
        # Third pass: identify duplicate networks
        for network, router_list in network_to_routers.items():
            if len(router_list) > 1:
                # Multiple routers have the same network number
                # Check if they're on same or different subnets
                all_subnets = set()
                for router_info in router_list:
                    all_subnets.update(router_info['subnets'])
                
                if len(all_subnets) == 1:
                    # Same subnet - likely duplicate router
                    issue_type = 'duplicate-router'
                    description = 'Same network number on multiple routers in the same subnet'
                else:
                    # Different subnets - likely duplicate network
                    issue_type = 'duplicate-network' 
                    description = 'Same network number on routers in different subnets'
                
                issue = {
                    'issue_type': issue_type,
                    'network': network,
                    'router_count': len(router_list),
                    'routers': router_list,
                    'subnets': list(all_subnets),
                    'description': description
                }
                issues.append(issue)
                
                if verbose:
                    # Collect affected triples for all routers involved
                    for router_info in router_list:
                        router_uri = rdflib.URIRef(router_info['router'])
                        for triple in graph.triples((router_uri, None, None)):
                            affected_triples.append(triple)
    
    except Exception as e:
        click.echo(f"Error analyzing graph for duplicate networks: {e}", err=True)
        return [], []
    
    return issues, affected_triples


def check_duplicate_bbmds(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for duplicate BBMDs on the same subnet.
    
    Issues detected:
    - Warning: Multiple BBMDs on same subnet (>1 BBMD)
    - Error: Multiple BBMDs with BDT entries on same subnet (both have BDT entries)
    
    Args:
        graph: The RDF graph to analyze
        verbose: Whether to include detailed triple information
        
    Returns:
        Tuple of (issues_list, affected_triples)
    """
    issues = []
    affected_triples = []
    
    try:
        # Find all BBMDs and their subnets/BDT entries
        bbmd_info = {}
        
        # First pass: collect all BBMDs with their subnets and BDT entries
        rdf_type = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        bbmds_query = graph.triples((None, rdf_type, BACNET_NS['BBMD']))
        
        for bbmd, _, _ in bbmds_query:
            subnets = []
            bdt_entries = []
            
            # Get broadcast domains (subnets) for this BBMD
            for _, _, subnet in graph.triples((bbmd, BACNET_NS['bbmd-broadcast-domain'], None)):
                subnets.append(str(subnet))
            
            # Get BDT entries for this BBMD
            for _, _, bdt_entry in graph.triples((bbmd, BACNET_NS['bdt-entry'], None)):
                bdt_entries.append(str(bdt_entry))
            
            if subnets:  # Only track BBMDs that have broadcast domains
                bbmd_info[str(bbmd)] = {
                    'subnets': subnets,
                    'bdt_entries': bdt_entries,
                    'has_bdt': len(bdt_entries) > 0
                }
        
        # Second pass: group by subnet to find duplicates
        subnet_to_bbmds = {}
        for bbmd, info in bbmd_info.items():
            for subnet in info['subnets']:
                if subnet not in subnet_to_bbmds:
                    subnet_to_bbmds[subnet] = []
                subnet_to_bbmds[subnet].append({
                    'bbmd': bbmd,
                    'bdt_entries': info['bdt_entries'],
                    'has_bdt': info['has_bdt']
                })
        
        # Third pass: identify duplicate BBMDs on same subnet
        for subnet, bbmd_list in subnet_to_bbmds.items():
            if len(bbmd_list) > 1:
                # Multiple BBMDs on same subnet
                bbmds_with_bdt = [bbmd for bbmd in bbmd_list if bbmd['has_bdt']]
                
                if len(bbmds_with_bdt) > 1:
                    # Error: Multiple BBMDs with BDT entries on same subnet
                    issue_type = 'duplicate-bbmd-error'
                    severity = 'error'
                    description = 'Multiple BBMDs with BDT entries on the same subnet'
                else:
                    # Warning: Multiple BBMDs on same subnet but not all have BDT entries
                    issue_type = 'duplicate-bbmd-warning'
                    severity = 'warning'
                    description = 'Multiple BBMDs on the same subnet'
                
                issue = {
                    'issue_type': issue_type,
                    'severity': severity,
                    'subnet': subnet,
                    'bbmd_count': len(bbmd_list),
                    'bbmds': bbmd_list,
                    'bbmds_with_bdt_count': len(bbmds_with_bdt),
                    'description': description
                }
                issues.append(issue)
                
                if verbose:
                    # Collect affected triples for all BBMDs involved
                    for bbmd_info in bbmd_list:
                        bbmd_uri = rdflib.URIRef(bbmd_info['bbmd'])
                        for triple in graph.triples((bbmd_uri, None, None)):
                            affected_triples.append(triple)
    
    except Exception as e:
        click.echo(f"Error analyzing graph for duplicate BBMDs: {e}", err=True)
        return [], []
    
    return issues, affected_triples


def format_human_readable(issues: List[Dict[str, Any]], issue_type: str, verbose: bool = False) -> str:
    """Format issues in human-readable format."""
    if not issues:
        return f"✓ No {issue_type.replace('-', ' ')} issues found"
    
    output = []
    
    # Use appropriate emoji and text based on severity
    if issue_type.endswith('-error'):
        icon = "❌"
        issue_label = issue_type.replace('-', ' ').replace('error', 'errors')
    elif issue_type.endswith('-warning'):
        icon = "⚠"
        issue_label = issue_type.replace('-', ' ').replace('warning', 'warnings')
    else:
        icon = "⚠"
        issue_label = issue_type.replace('-', ' ') + " issue(s)"
    
    output.append(f"{icon} Found {len(issues)} {issue_label}:")
    output.append("")
    
    for i, issue in enumerate(issues, 1):
        if issue_type == 'duplicate-device-id':
            output.append(f"{i}. Device ID {issue['device_id']} appears on {issue['device_count']} different devices:")
            for device_info in issue['devices']:
                network_type = device_info['network_type']
                output.append(f"   • {device_info['device']} on {network_type}: {device_info['network']}")
            output.append("")
        elif issue_type in ['duplicate-network', 'duplicate-router']:
            output.append(f"{i}. Network {issue['network']} found on {issue['router_count']} routers:")
            output.append(f"   Description: {issue['description']}")
            for router_info in issue['routers']:
                subnets_str = ', '.join(router_info['subnets']) if router_info['subnets'] else 'No subnet'
                output.append(f"   • {router_info['router']} (subnet: {subnets_str})")
            output.append("")
        elif issue_type in ['duplicate-bbmd-warning', 'duplicate-bbmd-error']:
            output.append(f"{i}. Subnet {issue['subnet']} has {issue['bbmd_count']} BBMDs:")
            output.append(f"   Description: {issue['description']}")
            output.append(f"   BBMDs with BDT entries: {issue['bbmds_with_bdt_count']}/{issue['bbmd_count']}")
            for bbmd_info in issue['bbmds']:
                bdt_status = "with BDT entries" if bbmd_info['has_bdt'] else "without BDT entries"
                bdt_count = len(bbmd_info['bdt_entries'])
                output.append(f"   • {bbmd_info['bbmd']} ({bdt_status}: {bdt_count} entries)")
            output.append("")
    
    return "\n".join(output)


def format_json_output(all_issues: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format issues in JSON format."""
    return json.dumps(all_issues, indent=2)


@click.command()
@click.argument('ttl_file', type=click.Path(exists=True, path_type=Path))
@click.option('--issue', '-i', 
              type=click.Choice(['duplicate-device-id', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error', 'all']),
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
        issues_to_check = ['duplicate-device-id', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error']
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
            output_issues = ['duplicate-device-id', 'duplicate-network', 'duplicate-router', 'duplicate-bbmd-warning', 'duplicate-bbmd-error']
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
