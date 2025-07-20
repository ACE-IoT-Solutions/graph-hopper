"""
Check for duplicate BBMDs on the same subnet.
"""

import click
from typing import List, Dict, Any, Tuple
import rdflib
from rdflib import Graph

from .utils import BACNET_NS


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
