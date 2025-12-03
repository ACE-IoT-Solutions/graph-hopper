"""
Unreachable Networks Check - Phase 2.1

Detects networks without routing paths to other networks, creating isolated network segments.
Isolated networks prevent inter-network communication in BACnet systems.

This check builds a network topology graph from router connections and uses graph traversal
to identify networks that cannot reach other networks in the system.
"""

from typing import List, Tuple, Any, Dict, Set
from collections import defaultdict, deque
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_unreachable_networks(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for networks that are isolated and cannot reach other networks through routing.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = []
    
    # Build network topology from the graph
    networks = set()
    routers = set()
    router_type = BACNET_NS['Router']
    network_type = BACNET_NS['BACnetNetwork']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Find all networks
    for network, _, _ in graph.triples((None, rdf_type, network_type)):
        networks.add(network)
    
    # Find all routers
    for router, _, _ in graph.triples((None, rdf_type, router_type)):
        routers.add(router)
    
    # If there are fewer than 2 networks, no isolation is possible
    if len(networks) < 2:
        return issues, affected_nodes

    # Build router connectivity map: network -> set of networks reachable via routers
    network_connections: defaultdict[rdflib.term.Node, Set[rdflib.term.Node]] = defaultdict(set)
    router_network_map: defaultdict[rdflib.term.Node, Set[rdflib.term.Node]] = defaultdict(set)    # Map each router to the networks it connects
    for router in routers:
        router_networks = set()
        
        # Get networks this router is connected to
        for _, _, network in graph.triples((router, BACNET_NS['device-on-network'], None)):
            router_networks.add(network)
            networks.add(network)  # Ensure we track all networks
        
        # Also check for subnet connections (routers can connect subnets within networks)
        for _, _, subnet in graph.triples((router, BACNET_NS['device-on-subnet'], None)):
            # Find which network this subnet belongs to
            for _, _, network in graph.triples((subnet, BACNET_NS['subnet-of-network'], None)):
                router_networks.add(network)
                networks.add(network)
        
        router_network_map[router] = router_networks
        
        # If this router connects multiple networks, create bidirectional connections
        router_networks_list = list(router_networks)
        for i, network1 in enumerate(router_networks_list):
            for j, network2 in enumerate(router_networks_list):
                if i != j:
                    network_connections[network1].add(network2)

    # Use graph traversal to find reachable networks from each network
    def get_reachable_networks(start_network: rdflib.term.Node) -> Set[rdflib.term.Node]:
        """Find all networks reachable from the start network via routing."""
        reachable = set()
        queue = deque([start_network])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            reachable.add(current)
            
            # Add all directly connected networks to the queue
            for connected in network_connections[current]:
                if connected not in visited:
                    queue.append(connected)
        
        return reachable
    
    # Find network islands (groups of networks that can reach each other)
    network_islands = []
    processed_networks = set()
    
    for network in networks:
        if network in processed_networks:
            continue
            
        # Find all networks reachable from this network
        reachable = get_reachable_networks(network)
        network_islands.append(reachable)
        processed_networks.update(reachable)

    # If there's more than one island, we have unreachable networks
    if len(network_islands) > 1:
        for i, island in enumerate(network_islands):
            if len(island) == 1:
                # Single isolated network
                network = list(island)[0]
                network_name = _get_network_name(graph, network)
                
                issue = {
                    'issue_type': 'unreachable-networks',
                    'severity': 'high',
                    'network': str(network),
                    'network_name': network_name,
                    'isolation_type': 'isolated',
                    'description': f'Network {network_name} is completely isolated with no routing connections',
                    'total_networks': len(networks),
                    'reachable_networks': 0,
                    'network_islands': len(network_islands)
                }
                
                if verbose:
                    other_networks = [_get_network_name(graph, net) for other_island in network_islands if other_island != island for net in other_island]
                    issue['verbose_description'] = (
                        f'Network {network_name} is completely isolated and cannot communicate with '
                        f'{len(networks) - 1} other networks in the system: {", ".join(other_networks[:5])}{"..." if len(other_networks) > 5 else ""}. '
                        f'This network needs router connections to enable inter-network communication.'
                    )
                
                issues.append(issue)
                affected_nodes.append(network)
            else:
                # Island with multiple networks - they can reach each other but not others
                island_networks = list(island)
                island_names = [_get_network_name(graph, net) for net in island_networks]
                
                for network in island_networks:
                    network_name = _get_network_name(graph, network)
                    unreachable_count = len(networks) - len(island)
                    
                    issue = {
                        'issue_type': 'unreachable-networks',
                        'severity': 'high',
                        'network': str(network),
                        'network_name': network_name,
                        'isolation_type': 'partial',
                        'description': f'Network {network_name} cannot reach {unreachable_count} other networks',
                        'total_networks': len(networks),
                        'reachable_networks': len(island) - 1,  # Exclude self
                        'network_islands': len(network_islands),
                        'island_networks': [str(net) for net in island_networks]
                    }
                    
                    if verbose:
                        reachable_names = [name for name in island_names if name != network_name]
                        unreachable_networks = [_get_network_name(graph, net) for other_island in network_islands if other_island != island for net in other_island]
                        issue['verbose_description'] = (
                            f'Network {network_name} can only reach {len(reachable_names)} networks '
                            f'({", ".join(reachable_names[:3])}{"..." if len(reachable_names) > 3 else ""}) '
                            f'but cannot reach {unreachable_count} other networks: '
                            f'{", ".join(unreachable_networks[:3])}{"..." if len(unreachable_networks) > 3 else ""}. '
                            f'Additional router connections are needed to bridge network islands.'
                        )
                    
                    issues.append(issue)
                    affected_nodes.append(network)
    
    return issues, affected_nodes


def _get_network_name(graph: Graph, network: rdflib.term.Node) -> str:
    """Get human-readable name for a network."""
    # Try to get the label
    for _, _, label_value in graph.triples((network, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
        return str(label_value)
    
    # Try to get network number
    for _, _, number_value in graph.triples((network, BACNET_NS['network-number'], None)):
        return f"Network {number_value}"
    
    # Fallback to URI
    return str(network).split('/')[-1] if '/' in str(network) else str(network)
