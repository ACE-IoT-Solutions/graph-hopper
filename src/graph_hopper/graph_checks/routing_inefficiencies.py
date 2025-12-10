"""
Routing Inefficiencies Detection - Phase 3.3

Analyzes BACnet routing topology for performance issues and configuration problems.
Identifies routing loops, suboptimal paths, missing routers, and topology inefficiencies.
"""

from typing import List, Set, Dict, Tuple, Any
from rdflib import Graph, URIRef
from collections import defaultdict, deque


def check_routing_inefficiencies(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Analyze BACnet routing topology for inefficiencies and configuration issues.
    
    Checks for:
    1. Routing loops (cycles in the routing graph)
    2. Suboptimal routing paths (unnecessary hops)
    3. Router isolation (single points of failure)
    4. Missing redundancy in critical paths
    5. Asymmetric routing configurations
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_triples, affected_nodes)
    """
    issues = []
    affected_nodes = set()
    affected_triples = []
    
    # Build routing topology
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Find routers and networks
    routers = set()
    networks = set()
    
    router_class = bacnet_ns + "Router"
    network_class = bacnet_ns + "BACnetNetwork"
    
    for router, _, _ in graph.triples((None, rdf_type, router_class)):
        routers.add(router)
    
    for network, _, _ in graph.triples((None, rdf_type, network_class)):
        networks.add(network)
    
    # Build routing graph
    routing_graph = _build_routing_graph(graph, routers, networks)
    
    # Check for various routing inefficiencies
    issues.extend(_check_routing_loops(routing_graph, verbose))
    issues.extend(_check_suboptimal_paths(routing_graph, verbose))
    issues.extend(_check_router_isolation(routing_graph, verbose))
    issues.extend(_check_asymmetric_routing(routing_graph, verbose))
    issues.extend(_check_missing_redundancy(routing_graph, verbose))
    
    # Add affected nodes
    for issue in issues:
        if 'router' in issue:
            affected_nodes.add(issue['router'])
        if 'network' in issue:
            affected_nodes.add(issue['network'])
        if 'routers' in issue.get('details', {}):
            affected_nodes.update(issue['details']['routers'])
        if 'networks' in issue.get('details', {}):
            affected_nodes.update(issue['details']['networks'])
        if 'loop_routers' in issue.get('details', {}):
            affected_nodes.update(issue['details']['loop_routers'])
    
    return issues, affected_triples, affected_nodes


def _build_routing_graph(graph: Graph, routers: Set, networks: Set) -> Dict[str, Any]:
    """
    Build a routing graph representation from the RDF data.
    
    Returns:
        Dictionary containing routing topology information
    """
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    device_on_network = bacnet_ns + "device-on-network"
    serves_network = bacnet_ns + "serves-network"
    
    # Router to networks mapping
    router_networks = defaultdict(set)  # Router -> {networks it's on}
    router_serves = defaultdict(set)    # Router -> {networks it serves}
    network_routers = defaultdict(set)  # Network -> {routers on it}
    
    # Build router-network relationships
    for router in routers:
        # Networks the router is directly on
        for _, _, network in graph.triples((router, device_on_network, None)):
            if network in networks:
                router_networks[str(router)].add(str(network))
                network_routers[str(network)].add(str(router))
        
        # Networks the router serves (routes to)
        for _, _, network in graph.triples((router, serves_network, None)):
            if network in networks:
                router_serves[str(router)].add(str(network))
    
    # Build network connectivity graph
    network_connections = defaultdict(set)  # Network -> {connected networks}
    
    for router_str, on_networks in router_networks.items():
        served_networks = router_serves[router_str]
        
        # Each router creates connections between the networks it's on and the networks it serves
        for on_network in on_networks:
            for served_network in served_networks:
                if on_network != served_network:
                    network_connections[on_network].add(served_network)
                    # Routing is typically bidirectional in BACnet
                    network_connections[served_network].add(on_network)
    
    return {
        'routers': router_networks,
        'router_serves': router_serves,
        'network_routers': network_routers,
        'network_connections': network_connections,
        'all_routers': {str(r) for r in routers},
        'all_networks': {str(n) for n in networks}
    }


def _check_routing_loops(routing_graph: Dict[str, Any], verbose: bool) -> List[Dict[str, Any]]:
    """Check for routing loops in the network topology."""
    issues = []
    network_connections = routing_graph['network_connections']
    
    # Use DFS to detect cycles in the network connectivity graph
    visited = set()
    rec_stack = set()
    loops_found = []
    
    def dfs_cycle_detect(network: str, path: List[str]) -> None:
        visited.add(network)
        rec_stack.add(network)
        path.append(network)
        
        for connected_network in network_connections.get(network, set()):
            if connected_network not in visited:
                dfs_cycle_detect(connected_network, path.copy())
            elif connected_network in rec_stack:
                # Found a cycle
                cycle_start = path.index(connected_network)
                cycle = path[cycle_start:] + [connected_network]
                if len(cycle) > 2:  # Avoid trivial 2-node cycles
                    loops_found.append(cycle)
        
        rec_stack.remove(network)
    
    # Check for cycles starting from each unvisited network
    for network in routing_graph['all_networks']:
        if network not in visited:
            dfs_cycle_detect(network, [])
    
    # Process found loops
    processed_loops = set()
    for loop in loops_found:
        # Normalize loop representation (start with lexicographically smallest)
        min_idx = loop.index(min(loop[:-1]))  # Exclude last element which is duplicate
        normalized_loop = loop[min_idx:-1] + loop[:min_idx] + [loop[min_idx]]
        loop_signature = tuple(normalized_loop)
        
        if loop_signature not in processed_loops:
            processed_loops.add(loop_signature)
            
            # Find routers involved in this loop
            loop_routers = set()
            loop_networks = set(normalized_loop[:-1])  # Remove duplicate last element
            
            for i in range(len(normalized_loop) - 1):
                from_net = normalized_loop[i]
                to_net = normalized_loop[i + 1]
                
                # Find routers that connect these networks
                for router_str, on_networks in routing_graph['routers'].items():
                    served_networks = routing_graph['router_serves'][router_str]
                    if from_net in on_networks and to_net in served_networks:
                        loop_routers.add(router_str)
            
            severity = 'critical' if len(loop_networks) <= 4 else 'warning'
            
            issue = {
                'issue_type': 'routing-loop',
                'severity': severity,
                'loop_length': len(loop_networks),
                'description': f"Routing loop detected: {len(loop_networks)} networks in cycle",
                'details': {
                    'loop_networks': list(loop_networks),
                    'loop_routers': list(loop_routers),
                    'loop_path': normalized_loop,
                    'performance_impact': _get_loop_performance_impact(len(loop_networks), severity),
                    'recommendation': _get_loop_recommendation(len(loop_networks), severity),
                    'routing_risk': 'Potential for broadcast storms and routing instability'
                }
            }
            
            if verbose:
                network_names = [_get_network_name_from_uri(n) for n in loop_networks]
                issue['verbose_description'] = (
                    f"Routing loop detected involving networks: {' -> '.join(network_names)} -> {network_names[0]}. "
                    f"This creates a potential for routing instability and broadcast storms. "
                    f"The loop involves {len(loop_routers)} routers and could cause packets to "
                    f"circulate indefinitely without reaching their destination."
                )
            
            issues.append(issue)
    
    return issues


def _check_suboptimal_paths(routing_graph: Dict[str, Any], verbose: bool) -> List[Dict[str, Any]]:
    """Check for suboptimal routing paths between networks."""
    issues = []
    network_connections = routing_graph['network_connections']
    all_networks = routing_graph['all_networks']
    
    # For each pair of networks, find shortest path and check for inefficiencies
    for source in all_networks:
        # Use BFS to find shortest paths from this source
        distances = {source: 0}
        paths = {source: [source]}
        queue = deque([source])
        
        while queue:
            current = queue.popleft()
            current_distance = distances[current]
            
            for neighbor in network_connections.get(current, set()):
                if neighbor not in distances:
                    distances[neighbor] = current_distance + 1
                    paths[neighbor] = paths[current] + [neighbor]
                    queue.append(neighbor)
        
        # Check for paths that seem unnecessarily long
        for target, distance in distances.items():
            if distance > 4:  # Paths longer than 4 hops are potentially inefficient
                path = paths[target]
                
                # Check if there might be a more direct connection missing
                issue = {
                    'issue_type': 'suboptimal-routing-path',
                    'severity': 'warning',
                    'source_network': source,
                    'target_network': target,
                    'path_length': distance,
                    'description': f"Long routing path: {distance} hops from {_get_network_name_from_uri(source)} to {_get_network_name_from_uri(target)}",
                    'details': {
                        'routing_path': path,
                        'networks': path,
                        'performance_impact': f"Increased latency due to {distance}-hop routing path",
                        'recommendation': "Consider adding direct routing connections or intermediate routers to reduce path length",
                        'efficiency_loss': f"Potential {(distance - 1) * 10}% latency increase vs direct connection"
                    }
                }
                
                if verbose:
                    path_names = [_get_network_name_from_uri(n) for n in path]
                    issue['verbose_description'] = (
                        f"Routing path from {path_names[0]} to {path_names[-1]} requires {distance} hops: "
                        f"{' -> '.join(path_names)}. This may indicate missing direct routing connections "
                        f"or suboptimal network topology design."
                    )
                
                issues.append(issue)
    
    return issues


def _check_router_isolation(routing_graph: Dict[str, Any], verbose: bool) -> List[Dict[str, Any]]:
    """Check for routers that represent single points of failure."""
    issues = []
    network_connections = routing_graph['network_connections']
    network_routers = routing_graph['network_routers']
    
    # Find networks with only one router (potential single points of failure)
    for network, routers in network_routers.items():
        if len(routers) == 1:
            router = list(routers)[0]
            connected_networks = network_connections.get(network, set())
            
            if len(connected_networks) > 1:
                # This router is the only connection point for multiple networks
                issue = {
                    'issue_type': 'router-single-point-failure',
                    'severity': 'warning',
                    'router': router,
                    'network': network,
                    'connected_networks_count': len(connected_networks),
                    'description': f"Single router failure point: {_get_router_name_from_uri(router)} is the only router on network {_get_network_name_from_uri(network)}",
                    'details': {
                        'connected_networks': list(connected_networks),
                        'routers': [router],
                        'failure_impact': f"Loss of connectivity to {len(connected_networks)} networks if router fails",
                        'recommendation': "Consider adding redundant routers for high availability",
                        'availability_risk': 'Single point of failure in network topology'
                    }
                }
                
                if verbose:
                    connected_names = [_get_network_name_from_uri(n) for n in connected_networks]
                    issue['verbose_description'] = (
                        f"Router {_get_router_name_from_uri(router)} on network {_get_network_name_from_uri(network)} "
                        f"is a single point of failure. If this router fails, connectivity will be lost to "
                        f"{len(connected_networks)} networks: {', '.join(connected_names)}."
                    )
                
                issues.append(issue)
    
    return issues


def _check_asymmetric_routing(routing_graph: Dict[str, Any], verbose: bool) -> List[Dict[str, Any]]:
    """Check for asymmetric routing configurations."""
    issues = []
    network_connections = routing_graph['network_connections']
    
    # Check for asymmetric connections (A -> B but not B -> A)
    asymmetric_pairs = []
    
    for network_a, connected_networks in network_connections.items():
        for network_b in connected_networks:
            # Check if the reverse connection exists
            reverse_connections = network_connections.get(network_b, set())
            if network_a not in reverse_connections:
                asymmetric_pairs.append((network_a, network_b))
    
    for network_a, network_b in asymmetric_pairs:
        issue = {
            'issue_type': 'asymmetric-routing',
            'severity': 'warning',
            'source_network': network_a,
            'target_network': network_b,
            'description': f"Asymmetric routing: {_get_network_name_from_uri(network_a)} can reach {_get_network_name_from_uri(network_b)} but not vice versa",
            'details': {
                'networks': [network_a, network_b],
                'routing_direction': f"{network_a} -> {network_b}",
                'missing_direction': f"{network_b} -> {network_a}",
                'recommendation': "Verify router configurations to ensure bidirectional connectivity",
                'connectivity_risk': 'Partial network reachability may cause communication failures'
            }
        }
        
        if verbose:
            issue['verbose_description'] = (
                f"Asymmetric routing detected between {_get_network_name_from_uri(network_a)} "
                f"and {_get_network_name_from_uri(network_b)}. Traffic can flow from "
                f"{_get_network_name_from_uri(network_a)} to {_get_network_name_from_uri(network_b)} "
                f"but the reverse path is not configured, which may cause communication failures."
            )
        
        issues.append(issue)
    
    return issues


def _check_missing_redundancy(routing_graph: Dict[str, Any], verbose: bool) -> List[Dict[str, Any]]:
    """Check for missing redundancy in critical network paths."""
    issues = []
    network_connections = routing_graph['network_connections']
    all_networks = routing_graph['all_networks']
    
    # Find articulation points (networks whose removal would disconnect the graph)
    def find_articulation_points():
        visited = set()
        disc = {}
        low = {}
        parent = {}
        articulation_points = set()
        time = [0]  # Use list to modify in nested function
        
        def bridge_util(u):
            children = 0
            visited.add(u)
            disc[u] = low[u] = time[0]
            time[0] += 1
            
            for v in network_connections.get(u, set()):
                if v not in visited:
                    children += 1
                    parent[v] = u
                    bridge_util(v)
                    
                    low[u] = min(low[u], low[v])
                    
                    # u is an articulation point in following cases:
                    # 1. u is root and has more than one child
                    if parent.get(u) is None and children > 1:
                        articulation_points.add(u)
                    
                    # 2. u is not root and low[v] >= disc[u]
                    if parent.get(u) is not None and low[v] >= disc[u]:
                        articulation_points.add(u)
                
                elif v != parent.get(u):
                    low[u] = min(low[u], disc[v])
        
        for network in all_networks:
            if network not in visited:
                bridge_util(network)
        
        return articulation_points
    
    if len(all_networks) > 2:  # Only meaningful for connected graphs with >2 nodes
        articulation_points = find_articulation_points()
        
        for critical_network in articulation_points:
            connected_count = len(network_connections.get(critical_network, set()))
            
            issue = {
                'issue_type': 'missing-redundancy',
                'severity': 'warning',
                'network': critical_network,
                'connected_networks_count': connected_count,
                'description': f"Critical network {_get_network_name_from_uri(critical_network)} lacks redundant paths",
                'details': {
                    'networks': [critical_network],
                    'connected_networks': list(network_connections.get(critical_network, set())),
                    'redundancy_impact': 'Network removal would disconnect the topology',
                    'recommendation': 'Add redundant routing paths to improve network resilience',
                    'availability_risk': 'Single point of failure in network connectivity'
                }
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f"Network {_get_network_name_from_uri(critical_network)} is a critical connection point. "
                    f"If this network becomes unreachable, it would disconnect other parts of the network topology. "
                    f"Consider adding redundant routing paths to improve network resilience."
                )
            
            issues.append(issue)
    
    return issues


def _get_network_name_from_uri(network_uri: str) -> str:
    """Extract a readable name from network URI."""
    if '/' in network_uri:
        return network_uri.split('/')[-1]
    return network_uri


def _get_router_name_from_uri(router_uri: str) -> str:
    """Extract a readable name from router URI."""
    if '/' in router_uri:
        return router_uri.split('/')[-1]
    return router_uri


def _get_loop_performance_impact(loop_length: int, severity: str) -> str:
    """Describe the performance impact of routing loops."""
    if severity == 'critical':
        return f"Severe routing instability with {loop_length}-network loop causing packet circulation"
    else:
        return f"Potential routing inefficiency with {loop_length}-network loop affecting performance"


def _get_loop_recommendation(loop_length: int, severity: str) -> str:
    """Generate recommendations for routing loop resolution."""
    if severity == 'critical':
        return (
            f"Immediately break the {loop_length}-network routing loop by disabling one router connection. "
            f"Implement Spanning Tree Protocol or reconfigure routing tables to prevent loops. "
            f"Verify all router configurations for consistency."
        )
    else:
        return (
            f"Review and optimize the {loop_length}-network routing configuration. "
            f"Consider implementing loop prevention mechanisms and verify routing table consistency."
        )
