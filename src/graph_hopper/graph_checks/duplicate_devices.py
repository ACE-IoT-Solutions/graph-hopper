"""
Check for duplicate device IDs across different networks/subnets.
"""

import click
from typing import List, Dict, Any, Tuple
import rdflib
from rdflib import Graph

from .utils import BACNET_NS


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
