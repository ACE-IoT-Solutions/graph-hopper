"""
Network Loops Check - Phase 2.4

Detects circular routing dependencies that can cause broadcast storms in BACnet networks.
Uses Depth-First Search (DFS) to detect cycles in the network topology graph.
"""

from typing import List, Set, Dict, Tuple, Any
from rdflib import Graph, URIRef
from collections import defaultdict


def check_network_loops(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Detect network loops that could cause broadcast storms.
    
    A network loop occurs when there are multiple routing paths between networks,
    which can cause broadcast storms. This is different from a simple bidirectional
    connection which is normal.
    
    Args:
        graph: RDFLib graph containing BACnet network topology
        
    Returns:
        tuple: (list of issues, set of affected node URIs)
    """
    issues = []
    affected_nodes = set()
    affected_triples = []
    
    # Build network adjacency graph from routers
    network_graph, router_connections = _build_network_graph_with_routers(graph)
    
    if not network_graph or len(network_graph) < 2:
        # Need at least 2 networks to have a loop
        return issues, affected_triples, affected_nodes
    
    # Special case: check for 2-network loops (mutual routing)
    if len(network_graph) == 2:
        networks = list(network_graph.keys())
        net1, net2 = networks[0], networks[1]
        
        # Check if both networks connect to each other (bidirectional)
        if (net2 in network_graph.get(net1, []) and 
            net1 in network_graph.get(net2, [])):
            
            # Find the routers causing this loop
            loop_routers = _find_routers_in_loop([net1, net2], router_connections)
            
            issue = {
                'issue_type': 'network-loops',
                'severity': 'critical',
                'description': 'Network loop detected involving 2 networks',
                'loop_size': 2,
                'loop_path': [net1, net2, net1],
                'details': {
                    'networks_in_loop': [net1, net2],
                    'routers_causing_loop': loop_routers,
                    'broadcast_storm_risk': 'high',
                    'recommendation': 'Remove redundant routing connections or implement spanning tree protocol'
                }
            }
            issues.append(issue)
            affected_nodes.update([net1, net2])
        
        return issues, affected_triples, affected_nodes
    
    # Use Union-Find to detect cycles in the network connectivity
    cycles = _find_cycles_union_find(network_graph)
    
    for cycle in cycles:
        if len(cycle) >= 3:  # Only report cycles of 3+ networks
            # Find the routers causing this loop
            loop_routers = _find_routers_in_loop(cycle, router_connections)
            
            issue = {
                'issue_type': 'network-loops',
                'severity': 'critical',
                'description': f'Network loop detected involving {len(cycle)} networks',
                'loop_size': len(cycle),
                'loop_path': cycle,  # Close the loop for display
                'details': {
                    'networks_in_loop': cycle,
                    'routers_causing_loop': loop_routers,
                    'broadcast_storm_risk': 'high',
                    'recommendation': 'Remove redundant routing connections or implement spanning tree protocol'
                }
            }
            issues.append(issue)
            affected_nodes.update(cycle)
    
    return issues, affected_triples, affected_nodes


def _find_cycles_union_find(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Find cycles using a modified approach that looks for redundant paths.
    
    Args:
        graph: Adjacency list representation of network connectivity
        
    Returns:
        List of cycles found
    """
    cycles = []
    all_nodes = list(graph.keys())
    
    if len(all_nodes) < 3:
        return cycles
    
    # For each possible 3+ node combination, check if they form a cycle
    visited_global = set()
    
    for start_node in all_nodes:
        if start_node in visited_global:
            continue
            
        # DFS to find cycles from this node
        visited = set()
        path = []
        cycle = _dfs_cycle_detection(start_node, graph, visited, path, start_node)
        
        if cycle and len(cycle) >= 3:
            # Normalize the cycle (start with the lexicographically smallest node)
            min_idx = cycle.index(min(cycle))
            normalized_cycle = cycle[min_idx:] + cycle[:min_idx]
            
            # Check if we've already found this cycle
            if not any(set(normalized_cycle) == set(existing) for existing in cycles):
                cycles.append(normalized_cycle)
                visited_global.update(normalized_cycle)
        
        visited_global.add(start_node)
    
    return cycles


def _dfs_cycle_detection(node: str, graph: Dict[str, List[str]], visited: Set[str], 
                        path: List[str], target: str, depth: int = 0) -> List[str]:
    """
    DFS to detect cycles back to target node.
    
    Args:
        node: Current node
        graph: Adjacency list
        visited: Visited nodes in current path
        path: Current path
        target: Target node to find cycle back to
        depth: Current depth
        
    Returns:
        Cycle if found, empty list otherwise
    """
    if depth > 5:  # Prevent infinite recursion
        return []
        
    if node in visited:
        return []
        
    visited.add(node)
    path.append(node)
    
    for neighbor in graph.get(node, []):
        if neighbor == target and len(path) >= 3:
            # Found a cycle back to start
            return path[:]
        elif neighbor not in visited:
            cycle = _dfs_cycle_detection(neighbor, graph, visited.copy(), path[:], target, depth + 1)
            if cycle:
                return cycle
    
    return []


def _build_network_graph_with_routers(graph: Graph) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build adjacency list representation of network connectivity from RDF graph,
    and track which routers connect which networks.
    
    Args:
        graph: RDFLib graph containing router and network relationships
        
    Returns:
        tuple: (network_adjacency_dict, router_connections_dict)
            - network_adjacency_dict: keys are networks, values are connected networks
            - router_connections_dict: maps connection_key -> list of routers connecting them
    """
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    router_class = bacnet_ns + "Router"
    device_on_network = bacnet_ns + "device-on-network"
    serves_network = bacnet_ns + "serves-network"
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    network_graph = defaultdict(list)
    # Track which routers connect which pairs of networks
    router_connections = defaultdict(list)
    
    # Find all routers and their network connections
    for router in graph.subjects(rdf_type, router_class):
        # Get the network this router is on
        source_networks = list(graph.objects(router, device_on_network))
        # Get the networks this router serves
        target_networks = list(graph.objects(router, serves_network))
        
        router_str = str(router)
        
        # Create bidirectional connections between source and target networks
        for source_net in source_networks:
            for target_net in target_networks:
                source_str = str(source_net)
                target_str = str(target_net)
                
                # Add bidirectional edges to network graph
                if target_str not in network_graph[source_str]:
                    network_graph[source_str].append(target_str)
                if source_str not in network_graph[target_str]:
                    network_graph[target_str].append(source_str)
                
                # Track which router connects these networks (both directions)
                connection_key_1 = f"{source_str}→{target_str}"
                connection_key_2 = f"{target_str}→{source_str}"
                
                if router_str not in router_connections[connection_key_1]:
                    router_connections[connection_key_1].append(router_str)
                if router_str not in router_connections[connection_key_2]:
                    router_connections[connection_key_2].append(router_str)
    
    return dict(network_graph), dict(router_connections)


def _find_routers_in_loop(networks_in_loop: List[str], router_connections: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """
    Find the routers that are causing the network loop.
    
    Args:
        networks_in_loop: List of network URIs that form the loop
        router_connections: Dict mapping network connection keys to router lists
        
    Returns:
        List of router information dicts with connection details
    """
    loop_routers = []
    
    # Check connections between adjacent networks in the loop
    for i in range(len(networks_in_loop)):
        current_net = networks_in_loop[i]
        next_net = networks_in_loop[(i + 1) % len(networks_in_loop)]
        
        connection_key = f"{current_net}→{next_net}"
        routers = router_connections.get(connection_key, [])
        
        for router in routers:
            router_info = {
                'router_uri': router,
                'router_name': _get_router_name(router),
                'connects_from': _get_network_name(current_net),
                'connects_to': _get_network_name(next_net),
                'connection_type': 'bidirectional routing'
            }
            
            # Avoid duplicates
            if not any(existing['router_uri'] == router for existing in loop_routers):
                loop_routers.append(router_info)
    
    return loop_routers


def _get_router_name(router_uri: str) -> str:
    """Get human-readable name for a router."""
    # Extract router identifier from URI
    if '/' in router_uri:
        return router_uri.split('/')[-1]
    return router_uri


def _get_network_name(network_uri: str) -> str:
    """Get human-readable name for a network."""
    # Extract network identifier from URI  
    if '/' in network_uri:
        return network_uri.split('/')[-1]
    return network_uri


def _build_network_graph(graph: Graph) -> Dict[str, List[str]]:
    """
    Build adjacency list representation of network connectivity from RDF graph.
    
    Args:
        graph: RDFLib graph containing router and network relationships
        
    Returns:
        dict: adjacency list where keys are networks and values are connected networks
    """
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    router_class = bacnet_ns + "Router"
    device_on_network = bacnet_ns + "device-on-network"
    serves_network = bacnet_ns + "serves-network"
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    network_graph = defaultdict(list)
    
    # Find all routers and their network connections
    for router in graph.subjects(rdf_type, router_class):
        # Get the network this router is on
        source_networks = list(graph.objects(router, device_on_network))
        # Get the networks this router serves
        target_networks = list(graph.objects(router, serves_network))
        
        # Create bidirectional connections between source and target networks
        for source_net in source_networks:
            for target_net in target_networks:
                source_str = str(source_net)
                target_str = str(target_net)
                
                # Add bidirectional edges
                if target_str not in network_graph[source_str]:
                    network_graph[source_str].append(target_str)
                if source_str not in network_graph[target_str]:
                    network_graph[target_str].append(source_str)
    
    return dict(network_graph)