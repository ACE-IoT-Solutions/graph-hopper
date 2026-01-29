"""
Missing Routers Check - Phase 2.2

Detects multi-network setups without proper routing infrastructure.
Networks that have devices but lack routing connections to other networks
can cause inter-network communication failures in BACnet systems.

This check identifies networks with devices that are isolated from other 
networks due to missing router connections.
"""

from typing import List, Tuple, Any, Dict
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_missing_routers(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for networks that lack proper routing infrastructure to connect with other networks.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_triples, affected_nodes)
    """
    issues = []
    affected_nodes = []
    affected_triples = []
    
    # Build network topology from the graph
    networks_with_devices = set()
    networks_with_routers = set()
    router_type = BACNET_NS['Router']
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Find all networks that have devices
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        # Check which network this device is on
        for _, _, network in graph.triples((device, BACNET_NS['device-on-network'], None)):
            networks_with_devices.add(network)
            
        # Also check for devices on subnets (get parent network)
        for _, _, subnet in graph.triples((device, BACNET_NS['device-on-subnet'], None)):
            # Find which network this subnet belongs to
            for _, _, network in graph.triples((subnet, BACNET_NS['subnet-of-network'], None)):
                networks_with_devices.add(network)
    
    # Find networks that have routing capability
    for router, _, _ in graph.triples((None, rdf_type, router_type)):
        # Networks where the router is located
        for _, _, network in graph.triples((router, BACNET_NS['device-on-network'], None)):
            networks_with_routers.add(network)
            
        # Networks that the router serves (provides routing to)
        for _, _, network in graph.triples((router, BACNET_NS['serves-network'], None)):
            networks_with_routers.add(network)
            
        # Check for subnet connections (routers can connect subnets within networks)
        for _, _, subnet in graph.triples((router, BACNET_NS['device-on-subnet'], None)):
            # Find which network this subnet belongs to
            for _, _, network in graph.triples((subnet, BACNET_NS['subnet-of-network'], None)):
                networks_with_routers.add(network)
    
    # If there are fewer than 2 networks with devices, no routing is needed
    if len(networks_with_devices) < 2:
        return issues, affected_triples, affected_nodes
    
    # Identify networks with devices but no routing capability
    isolated_networks = networks_with_devices - networks_with_routers
    
    if isolated_networks:
        # Get network labels for better reporting
        network_details = []
        for network in isolated_networks:
            network_label = str(network)
            # Try to get a human-readable label
            for _, _, label in graph.triples((network, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
                network_label = str(label)
                break
            
            network_details.append({
                'network_uri': str(network),
                'network_label': network_label
            })
        
        issue = {
            'issue_type': 'missing-routers',
            'severity': 'medium',
            'message': f'Found {len(isolated_networks)} networks with devices but no routing infrastructure',
            'description': ('Networks with devices that lack router connections to other networks. '
                         'This prevents inter-network communication in multi-network BACnet systems.'),
            'isolated_networks': network_details,
            'total_networks': len(networks_with_devices),
            'routed_networks': len(networks_with_routers)
        }
        
        if verbose:
            issue['verbose_details'] = (
                f'Networks with devices: {len(networks_with_devices)}, '
                f'Networks with routing: {len(networks_with_routers)}, '
                f'Routing coverage: {len(networks_with_routers)}/{len(networks_with_devices)} networks have routing'
            )
        
        issues.append(issue)
        affected_nodes.extend([network['network_uri'] for network in network_details])
    
    return issues, affected_triples, affected_nodes
