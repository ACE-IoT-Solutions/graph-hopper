"""
Subnet Mismatches Check - Phase 2.3

Detects device subnets that don't match their network topology.
Devices with IP addresses outside their declared subnet ranges can cause routing issues
and communication failures in BACnet systems.

This check validates that device IP addresses fall within the subnet ranges they are
assigned to, ensuring proper network topology consistency.
"""

from typing import List, Tuple, Any, Dict
import ipaddress
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_subnet_mismatches(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for devices with IP addresses that don't match their subnet assignments.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = []
    
    device_type = BACNET_NS['Device']
    subnet_type = BACNET_NS['Subnet']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Build subnet information mapping
    subnet_info = {}
    for subnet, _, _ in graph.triples((None, rdf_type, subnet_type)):
        subnet_address = None
        subnet_label = str(subnet)
        
        # Get subnet address/CIDR
        for _, _, addr in graph.triples((subnet, BACNET_NS['subnet-address'], None)):
            subnet_address = str(addr)
        
        # Get subnet label for better reporting
        for _, _, label in graph.triples((subnet, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            subnet_label = str(label)
        
        if subnet_address:
            subnet_info[subnet] = {
                'address': subnet_address,
                'label': subnet_label,
                'network': None
            }
            
            # Find which network this subnet belongs to
            for _, _, network in graph.triples((subnet, BACNET_NS['subnet-of-network'], None)):
                subnet_info[subnet]['network'] = network
    
    # Check each device's IP address against its subnet
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        device_address = None
        device_label = str(device)
        device_instance = None
        device_subnet = None
        
        # Get device information
        for _, _, addr in graph.triples((device, BACNET_NS['address'], None)):
            device_address = str(addr)
            
        for _, _, label in graph.triples((device, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            device_label = str(label)
            
        for _, _, instance in graph.triples((device, BACNET_NS['device-instance'], None)):
            device_instance = str(instance)
            
        for _, _, subnet in graph.triples((device, BACNET_NS['device-on-subnet'], None)):
            device_subnet = subnet
            
        # Only check devices that have both address and subnet assignment
        if device_address and device_subnet and device_subnet in subnet_info:
            subnet_data = subnet_info[device_subnet]
            
            # Check if device IP is within subnet range
            if not _is_ip_in_subnet(device_address, subnet_data['address']):
                issue = {
                    'issue_type': 'subnet-mismatches',
                    'severity': 'medium',
                    'message': f'Device IP address {device_address} does not match subnet {subnet_data["address"]}',
                    'description': ('Device IP address is outside the range of its assigned subnet. '
                                  'This can cause routing issues and communication failures.'),
                    'device': str(device),
                    'device_label': device_label,
                    'device_instance': device_instance,
                    'device_address': device_address,
                    'subnet': str(device_subnet),
                    'subnet_label': subnet_data['label'],
                    'subnet_address': subnet_data['address']
                }
                
                if verbose:
                    network_label = "Unknown"
                    if subnet_data['network']:
                        for _, _, label in graph.triples((subnet_data['network'], URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
                            network_label = str(label)
                            break
                        if network_label == "Unknown":
                            network_label = str(subnet_data['network'])
                    
                    issue['verbose_details'] = (
                        f'Device "{device_label}" (instance {device_instance}) has IP {device_address} '
                        f'but is assigned to subnet {subnet_data["address"]}. Network: {network_label}'
                    )
                
                issues.append(issue)
                affected_nodes.append(device)
    
    return issues, affected_nodes


def _is_ip_in_subnet(ip_address: str, subnet_cidr: str) -> bool:
    """
    Check if an IP address falls within a subnet CIDR range.
    
    Args:
        ip_address: IP address to check (e.g., "192.168.1.100")
        subnet_cidr: Subnet in CIDR notation (e.g., "192.168.1.0/24")
    
    Returns:
        True if IP is in subnet, False otherwise
    """
    try:
        # Parse the IP address
        ip = ipaddress.ip_address(ip_address)
        
        # Parse the subnet
        network = ipaddress.ip_network(subnet_cidr, strict=False)
        
        # Check if IP is in network
        return ip in network
        
    except (ipaddress.AddressValueError, ValueError):
        # If we can't parse the IP or subnet, skip validation
        # This handles BACnet addresses, malformed IPs, etc.
        return True
