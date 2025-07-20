"""
Check for duplicate network numbers on multiple routers.
"""

import click
from typing import List, Dict, Any, Tuple
import rdflib
from rdflib import Graph

from .utils import BACNET_NS


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
