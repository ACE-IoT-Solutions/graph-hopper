"""
Registry of available graph checks and their metadata.

This module provides a centralized registry of all available check types,
allowing for dynamic CLI option generation and automatic check execution.
"""

from typing import Dict, List, Tuple, Any
from rdflib import Graph
import rdflib

# Import all check functions
from .duplicate_devices import check_duplicate_device_ids
from .duplicate_networks import check_duplicate_networks  
from .duplicate_bbmds import check_duplicate_bbmds
from .orphaned_devices import check_orphaned_devices
from .invalid_device_ranges import check_invalid_device_ranges
from .device_address_conflicts import check_device_address_conflicts
from .missing_vendor_ids import check_missing_vendor_ids
from .unreachable_networks import check_unreachable_networks
from .missing_routers import check_missing_routers
from .subnet_mismatches import check_subnet_mismatches
from .network_loops import check_network_loops
from .oversized_networks import check_oversized_networks
from .broadcast_domains import check_broadcast_domains
from .routing_inefficiencies import check_routing_inefficiencies


class CheckRegistry:
    """Registry for all available graph checks."""
    
    def __init__(self):
        # Registry mapping issue type name to check function and metadata
        self._checks: Dict[str, Dict[str, Any]] = {
            'duplicate-device-id': {
                'function': check_duplicate_device_ids,
                'description': 'Detect devices with same ID across different networks/subnets',
                'category': 'device-conflicts',
                'single_check': True  # Returns issues for one type only
            },
            'orphaned-devices': {
                'function': check_orphaned_devices,
                'description': 'Detect devices not connected to any network or subnet',
                'category': 'connectivity',
                'single_check': True  # Returns issues for one type only
            },
            'invalid-device-ranges': {
                'function': check_invalid_device_ranges,
                'description': 'Detect devices with instance IDs outside valid BACnet range (0-4194303)',
                'category': 'device-validation',
                'single_check': True  # Returns issues for one type only
            },
            'device-address-conflicts': {
                'function': check_device_address_conflicts,
                'description': 'Detect devices with same address on same network/subnet',
                'category': 'device-conflicts',
                'single_check': True  # Returns issues for one type only
            },
            'missing-vendor-ids': {
                'function': check_missing_vendor_ids,
                'description': 'Detect devices without vendor identification or invalid vendor formats',
                'category': 'device-validation',
                'single_check': True  # Returns issues for one type only
            },
            'unreachable-networks': {
                'function': check_unreachable_networks,
                'description': 'Detect networks isolated without routing paths to other networks',
                'category': 'network-topology',
                'single_check': True  # Returns issues for one type only
            },
            'missing-routers': {
                'function': check_missing_routers,
                'description': 'Detect multi-network setups without proper routing infrastructure',
                'category': 'network-topology',
                'single_check': True  # Returns issues for one type only
            },
            'network-loops': {
                'function': check_network_loops,
                'description': 'Detect circular routing dependencies that can cause broadcast storms',
                'category': 'network-topology',
                'single_check': True  # Returns issues for one type only
            },
            'subnet-mismatches': {
                'function': check_subnet_mismatches,
                'description': 'Detect devices with IP addresses outside their configured subnet ranges',
                'category': 'network-topology',
                'single_check': True  # Returns issues for one type only
            },
            'oversized-networks': {
                'function': check_oversized_networks,
                'description': 'Detect networks with too many devices that can impact performance',
                'category': 'network-performance',
                'single_check': False,  # Returns multiple types (warning and critical)
                'related_types': ['oversized-networks-warning', 'oversized-networks-critical']
            },
            'oversized-networks-warning': {
                'function': check_oversized_networks,
                'description': 'Detect networks with moderately high device counts (performance warning)',
                'category': 'network-performance',
                'single_check': False,
                'related_types': ['oversized-networks', 'oversized-networks-critical']
            },
            'oversized-networks-critical': {
                'function': check_oversized_networks,
                'description': 'Detect networks with critically high device counts (severe performance impact)',
                'category': 'network-performance', 
                'single_check': False,
                'related_types': ['oversized-networks', 'oversized-networks-warning']
            },
            'duplicate-network': {
                'function': check_duplicate_networks,
                'description': 'Detect network numbers on routers in different subnets',
                'category': 'network-topology', 
                'single_check': False,  # Returns multiple types
                'related_types': ['duplicate-router']  # Other types returned by same function
            },
            'duplicate-router': {
                'function': check_duplicate_networks,
                'description': 'Detect network numbers on multiple routers in same subnet',
                'category': 'network-topology',
                'single_check': False,
                'related_types': ['duplicate-network']
            },
            'duplicate-bbmd-warning': {
                'function': check_duplicate_bbmds,
                'description': 'Detect multiple BBMDs on same subnet (not all have BDT entries)',
                'category': 'bbmd-configuration',
                'single_check': False,
                'related_types': ['duplicate-bbmd-error']
            },
            'duplicate-bbmd-error': {
                'function': check_duplicate_bbmds,  
                'description': 'Detect multiple BBMDs with BDT entries on same subnet',
                'category': 'bbmd-configuration',
                'single_check': False,
                'related_types': ['duplicate-bbmd-warning']
            },
            'broadcast-domain-warning': {
                'function': check_broadcast_domains,
                'description': 'Detect large broadcast domains that may impact performance',
                'category': 'network-performance',
                'single_check': False,
                'related_types': ['broadcast-domain-critical', 'missing-bbmd-coverage', 'broadcast-domain-overlap']
            },
            'broadcast-domain-critical': {
                'function': check_broadcast_domains,
                'description': 'Detect critically large broadcast domains causing severe performance impact',
                'category': 'network-performance',
                'single_check': False,
                'related_types': ['broadcast-domain-warning', 'missing-bbmd-coverage', 'broadcast-domain-overlap']
            },
            'missing-bbmd-coverage': {
                'function': check_broadcast_domains,
                'description': 'Detect complex broadcast domains lacking BBMD management',
                'category': 'bbmd-configuration',
                'single_check': False,
                'related_types': ['broadcast-domain-warning', 'broadcast-domain-critical', 'broadcast-domain-overlap']
            },
            'broadcast-domain-overlap': {
                'function': check_broadcast_domains,
                'description': 'Detect overlapping broadcast domains that may cause conflicts',
                'category': 'network-topology',
                'single_check': False,
                'related_types': ['broadcast-domain-warning', 'broadcast-domain-critical', 'missing-bbmd-coverage']
            },
            'routing-loop': {
                'function': check_routing_inefficiencies,
                'description': 'Detect routing loops that cause packet circulation and instability',
                'category': 'routing-topology',
                'single_check': False,
                'related_types': ['suboptimal-routing-path', 'router-single-point-failure', 'asymmetric-routing', 'missing-redundancy']
            },
            'suboptimal-routing-path': {
                'function': check_routing_inefficiencies,
                'description': 'Detect inefficient routing paths with excessive hops',
                'category': 'routing-performance',
                'single_check': False,
                'related_types': ['routing-loop', 'router-single-point-failure', 'asymmetric-routing', 'missing-redundancy']
            },
            'router-single-point-failure': {
                'function': check_routing_inefficiencies,
                'description': 'Detect routers that represent single points of failure',
                'category': 'routing-reliability',
                'single_check': False,
                'related_types': ['routing-loop', 'suboptimal-routing-path', 'asymmetric-routing', 'missing-redundancy']
            },
            'asymmetric-routing': {
                'function': check_routing_inefficiencies,
                'description': 'Detect asymmetric routing configurations causing connectivity issues',
                'category': 'routing-topology',
                'single_check': False,
                'related_types': ['routing-loop', 'suboptimal-routing-path', 'router-single-point-failure', 'missing-redundancy']
            },
            'missing-redundancy': {
                'function': check_routing_inefficiencies,
                'description': 'Detect networks lacking redundant routing paths',
                'category': 'routing-reliability',
                'single_check': False,
                'related_types': ['routing-loop', 'suboptimal-routing-path', 'router-single-point-failure', 'asymmetric-routing']
            }
        }
    
    def get_all_issue_types(self) -> List[str]:
        """Get list of all available issue types."""
        return list(self._checks.keys())
    
    def get_cli_choices(self) -> List[str]:
        """Get list of choices for CLI option, including 'all'."""
        return self.get_all_issue_types() + ['all']
    
    def get_issue_description(self, issue_type: str) -> str:
        """Get description for an issue type."""
        return self._checks.get(issue_type, {}).get('description', 'Unknown issue type')
    
    def resolve_issues_to_check(self, requested_issue: str) -> List[str]:
        """
        Resolve the requested issue into a list of issues to check.
        
        Args:
            requested_issue: The issue type requested (could be 'all' or specific type)
            
        Returns:
            List of issue types to actually check
        """
        if requested_issue == 'all':
            return self.get_all_issue_types()
        elif requested_issue in self._checks:
            # For multi-type checks, we need to include related types
            check_info = self._checks[requested_issue]
            if check_info['single_check']:
                return [requested_issue]
            else:
                # Include all related types for multi-type functions
                related = check_info.get('related_types', [])
                return [requested_issue] + related
        else:
            return [requested_issue]  # Let it fail downstream if invalid
    
    def execute_checks(self, issues_to_check: List[str], graph: Graph, verbose: bool = False) -> Tuple[Dict[str, List[Dict[str, Any]]], List[rdflib.term.Node]]:
        """
        Execute all requested checks, handling multi-type functions efficiently.
        
        Args:
            issues_to_check: List of issue types to check for
            graph: The RDF graph to analyze  
            verbose: Whether to include verbose output
            
        Returns:
            Tuple of (all_issues_dict, all_affected_nodes)
        """
        all_issues: Dict[str, List[Dict[str, Any]]] = {}
        all_affected_triples = []
        executed_functions = set()  # Track which functions we've already called
        
        for issue_type in issues_to_check:
            if issue_type not in self._checks:
                continue
                
            check_info = self._checks[issue_type]
            function_id = id(check_info['function'])  # Unique function identifier
            
            if check_info['single_check']:
                # Single-type check - execute directly
                if function_id not in executed_functions:
                    issues, affected_triples = check_info['function'](graph, verbose)
                    all_issues[issue_type] = issues
                    all_affected_triples.extend(affected_triples)
                    executed_functions.add(function_id)
            else:
                # Multi-type check - execute once and separate results
                if function_id not in executed_functions:
                    issues, affected_triples = check_info['function'](graph, verbose)
                    
                    # Separate issues by type for multi-type functions
                    related_types = [issue_type] + check_info.get('related_types', [])
                    for related_type in related_types:
                        type_issues = [i for i in issues if i.get('issue_type') == related_type]
                        all_issues[related_type] = type_issues
                    
                    all_affected_triples.extend(affected_triples)
                    executed_functions.add(function_id)
        
        return all_issues, all_affected_triples
    
    def get_issues_by_category(self, category: str) -> List[str]:
        """Get all issue types in a specific category."""
        return [
            issue_type for issue_type, info in self._checks.items()
            if info.get('category') == category
        ]
    
    def is_single_check(self, issue_type: str) -> bool:
        """Check if an issue type returns only one type of issue."""
        return self._checks.get(issue_type, {}).get('single_check', True)


# Global registry instance
ISSUE_REGISTRY = CheckRegistry()
