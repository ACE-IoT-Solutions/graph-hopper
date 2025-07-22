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
