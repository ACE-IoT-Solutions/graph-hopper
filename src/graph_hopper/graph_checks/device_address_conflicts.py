"""
Device Address Conflicts Check - Phase 1.3

Detects multiple devices with the same address on the same network/subnet.
Address conflicts cause critical communication failures in BACnet networks.

This check groups devices by their network/subnet membership and identifies
devices that share the same address within the same network segment.
"""

from typing import List, Tuple, Any, Dict
from collections import defaultdict
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_device_address_conflicts(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for devices with conflicting addresses within the same network/subnet.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = []
    
    # Find all devices and group them by network/subnet
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Data structures to track devices by network/subnet and address
    network_devices = defaultdict(list)  # network -> [(device, address), ...]
    subnet_devices = defaultdict(list)   # subnet -> [(device, address), ...]
    
    # First pass: collect all devices with their network/subnet membership and addresses
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        # Get device properties
        device_name = None
        device_instance = None
        device_address = None
        
        # Extract device name/label
        for _, _, label_value in graph.triples((device, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            device_name = str(label_value)
            break
        
        # Extract device instance
        for _, _, instance_value in graph.triples((device, BACNET_NS['device-instance'], None)):
            device_instance = str(instance_value)
            break
            
        # Extract address
        for _, _, address_value in graph.triples((device, BACNET_NS['address'], None)):
            device_address = str(address_value)
            break
            
        # Use defaults if not found
        final_device_name = device_name if device_name else f"Device {device_instance if device_instance else 'Unknown'}"
        final_device_instance = device_instance if device_instance else 'Unknown'
        
        if not device_address:
            continue  # Skip devices without addresses
            
        # Get networks this device is on
        device_networks = []
        for _, _, network in graph.triples((device, BACNET_NS['device-on-network'], None)):
            device_info = {
                'device': device,
                'device_name': final_device_name,
                'device_instance': final_device_instance,
                'address': device_address
            }
            network_devices[str(network)].append(device_info)
            device_networks.append(str(network))
            
        # Get subnets this device is on  
        device_subnets = []
        for _, _, subnet in graph.triples((device, BACNET_NS['device-on-subnet'], None)):
            device_info = {
                'device': device,
                'device_name': final_device_name,
                'device_instance': final_device_instance,
                'address': device_address
            }
            subnet_devices[str(subnet)].append(device_info)
            device_subnets.append(str(subnet))
    
    # Second pass: check for address conflicts within each network
    for network, devices in network_devices.items():
        address_map = defaultdict(list)
        
        # Group devices by address
        for device_info in devices:
            address_map[device_info['address']].append(device_info)
        
        # Check for conflicts (multiple devices with same address)
        for address, conflicting_devices in address_map.items():
            if len(conflicting_devices) > 1:
                issue = {
                    'type': 'device-address-conflicts',
                    'severity': 'critical',
                    'network': network,
                    'network_type': 'network',
                    'address': address,
                    'device_count': len(conflicting_devices),
                    'devices': conflicting_devices,
                    'description': f'{len(conflicting_devices)} devices share address {address} on network {network}'
                }
                
                if verbose:
                    device_names = [dev['device_name'] for dev in conflicting_devices]
                    issue['verbose_description'] = (
                        f'Address conflict detected on network {network}: '
                        f'Address {address} is assigned to {len(conflicting_devices)} devices: '
                        f'{", ".join(device_names)}. This will cause communication failures '
                        f'as multiple devices cannot share the same address on the same network segment.'
                    )
                
                issues.append(issue)
                
                # Add all conflicting devices to affected nodes
                for device_info in conflicting_devices:
                    affected_nodes.append(device_info['device'])
    
    # Third pass: check for address conflicts within each subnet
    for subnet, devices in subnet_devices.items():
        address_map = defaultdict(list)
        
        # Group devices by address
        for device_info in devices:
            address_map[device_info['address']].append(device_info)
        
        # Check for conflicts (multiple devices with same address)
        for address, conflicting_devices in address_map.items():
            if len(conflicting_devices) > 1:
                issue = {
                    'type': 'device-address-conflicts',
                    'severity': 'critical',
                    'network': subnet,
                    'network_type': 'subnet',
                    'address': address,
                    'device_count': len(conflicting_devices),
                    'devices': conflicting_devices,
                    'description': f'{len(conflicting_devices)} devices share address {address} on subnet {subnet}'
                }
                
                if verbose:
                    device_names = [dev['device_name'] for dev in conflicting_devices]
                    issue['verbose_description'] = (
                        f'Address conflict detected on subnet {subnet}: '
                        f'Address {address} is assigned to {len(conflicting_devices)} devices: '
                        f'{", ".join(device_names)}. This will cause communication failures '
                        f'as multiple devices cannot share the same address on the same network segment.'
                    )
                
                issues.append(issue)
                
                # Add all conflicting devices to affected nodes
                for device_info in conflicting_devices:
                    affected_nodes.append(device_info['device'])
    
    return issues, affected_nodes
