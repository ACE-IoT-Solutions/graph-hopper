"""
Common utilities for graph checking modules.
"""

import json
from typing import List, Dict, Any
from rdflib import Namespace


# BACnet namespace from the real data
BACNET_NS = Namespace("http://data.ashrae.org/bacnet/2020#")


def format_human_readable(issues: List[Dict[str, Any]], issue_type: str, verbose: bool = False) -> str:
    """Format issues in human-readable format."""
    if not issues:
        return f"✓ No {issue_type.replace('-', ' ')} issues found"
    
    output = []
    
    # Use appropriate emoji and text based on severity
    if issue_type.endswith('-error'):
        icon = "❌"
        issue_label = issue_type.replace('-', ' ').replace('error', 'errors')
    elif issue_type.endswith('-warning'):
        icon = "⚠"
        issue_label = issue_type.replace('-', ' ').replace('warning', 'warnings')
    else:
        icon = "⚠"
        issue_label = issue_type.replace('-', ' ') + " issue(s)"
    
    output.append(f"{icon} Found {len(issues)} {issue_label}:")
    output.append("")
    
    for i, issue in enumerate(issues, 1):
        if issue_type == 'duplicate-device-id':
            output.append(f"{i}. Device ID {issue['device_id']} appears on {issue['device_count']} different devices:")
            for device_info in issue['devices']:
                network_type = device_info['network_type']
                output.append(f"   • {device_info['device']} on {network_type}: {device_info['network']}")
            output.append("")
        elif issue_type in ['duplicate-network', 'duplicate-router']:
            output.append(f"{i}. Network {issue['network']} found on {issue['router_count']} routers:")
            output.append(f"   Description: {issue['description']}")
            for router_info in issue['routers']:
                subnets_str = ', '.join(router_info['subnets']) if router_info['subnets'] else 'No subnet'
                output.append(f"   • {router_info['router']} (subnet: {subnets_str})")
            output.append("")
        elif issue_type in ['duplicate-bbmd-warning', 'duplicate-bbmd-error']:
            output.append(f"{i}. Subnet {issue['subnet']} has {issue['bbmd_count']} BBMDs:")
            output.append(f"   Description: {issue['description']}")
            output.append(f"   BBMDs with BDT entries: {issue['bbmds_with_bdt_count']}/{issue['bbmd_count']}")
            for bbmd_info in issue['bbmds']:
                bdt_status = "with BDT entries" if bbmd_info['has_bdt'] else "without BDT entries"
                bdt_count = len(bbmd_info['bdt_entries'])
                output.append(f"   • {bbmd_info['bbmd']} ({bdt_status}: {bdt_count} entries)")
            output.append("")
        elif issue_type == 'orphaned-devices':
            output.append(f"{i}. Orphaned device: {issue['label']} (instance {issue['device_instance']})")
            output.append(f"   Device URI: {issue['device']}")
            output.append(f"   Address: {issue['address']}")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_description' in issue:
                output.append(f"   Details: {issue['verbose_description']}")
            output.append("")
    
    return "\n".join(output)


def format_json_output(all_issues: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format issues in JSON format."""
    return json.dumps(all_issues, indent=2)
