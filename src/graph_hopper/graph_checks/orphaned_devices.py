"""
Check for orphaned devices that are not connected to any network or subnet.

Orphaned devices are BACnet devices that lack proper network connectivity,
which prevents them from communicating with other devices on the network.
"""

from typing import List, Dict, Any, Tuple
import rdflib
from rdflib import Graph

from .utils import BACNET_NS


def check_orphaned_devices(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for devices that are not connected to any network or subnet.
    
    An orphaned device is defined as a device that:
    - Has type ns1:Device (not Router, BBMD, etc.)
    - Lacks both ns1:device-on-network and ns1:device-on-subnet properties
    
    Args:
        graph: The RDF graph to analyze
        verbose: If True, include detailed information about affected triples
        
    Returns:
        Tuple of (issues_list, affected_nodes) where:
        - issues_list: List of dictionaries describing each orphaned device
        - affected_nodes: List of RDF nodes representing the orphaned devices
    """
    issues: List[Dict[str, Any]] = []
    affected_nodes: List[rdflib.term.Node] = []
    
    # Find all devices (specifically ns1:Device type, not routers or BBMDs)
    device_type = BACNET_NS['Device']
    
    for device, _, _ in graph.triples((None, rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), device_type)):
        # Get device properties
        label = None
        instance = None
        address = None
        
        # Extract label
        for _, _, label_value in graph.triples((device, rdflib.URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            label = str(label_value)
            break
        if not label:
            label = str(device)
            
        # Extract device instance
        for _, _, instance_value in graph.triples((device, BACNET_NS['device-instance'], None)):
            instance = str(instance_value)
            break
        if not instance:
            instance = "unknown"
            
        # Extract address
        for _, _, address_value in graph.triples((device, BACNET_NS['address'], None)):
            address = str(address_value)
            break
        if not address:
            address = "unknown"
        
        # Check if device has network connectivity
        has_network = bool(list(graph.triples((device, BACNET_NS['device-on-network'], None))))
        has_subnet = bool(list(graph.triples((device, BACNET_NS['device-on-subnet'], None))))
        
        # Device is orphaned if it has neither network nor subnet connection
        if not has_network and not has_subnet:
            issue: Dict[str, Any] = {
                'issue_type': 'orphaned-device',
                'severity': 'critical',
                'device': str(device),
                'label': label,
                'device_instance': instance,
                'address': address,
                'description': f'Device {label} (instance {instance}) is not connected to any network or subnet'
            }
            
            if verbose:
                # Get all triples for this device to show what properties it has
                device_triples = list(graph.triples((device, None, None)))
                issue['triples'] = [
                    {
                        'subject': str(triple[0]),
                        'predicate': str(triple[1]),
                        'object': str(triple[2])
                    }
                    for triple in device_triples
                ]
                
                issue['verbose_description'] = (
                    f'Device {label} (URI: {device}) has {len(device_triples)} properties '
                    f'but lacks both ns1:device-on-network and ns1:device-on-subnet connections. '
                    f'This device cannot communicate with other devices on the BACnet network.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
    
    return issues, affected_nodes
