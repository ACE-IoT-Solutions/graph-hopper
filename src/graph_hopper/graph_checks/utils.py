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
        elif issue_type == 'invalid-device-ranges':
            output.append(f"{i}. Invalid device range: {issue['label']} (instance {issue['device_instance']})")
            output.append(f"   Device URI: {issue['device']}")
            output.append(f"   Address: {issue['address']}")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_description' in issue:
                output.append(f"   Details: {issue['verbose_description']}")
            output.append("")
        elif issue_type == 'device-address-conflicts':
            network_type = issue.get('network_type', 'network')
            output.append(f"{i}. Address conflict on {network_type} {issue['network']}: {issue['device_count']} devices share address {issue['address']}")
            for device_info in issue['devices']:
                output.append(f"   • {device_info['device_name']} (instance {device_info['device_instance']})")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_description' in issue:
                output.append(f"   Details: {issue['verbose_description']}")
            output.append("")
        elif issue_type == 'missing-vendor-ids':
            vendor_info = f" (vendor-id: {issue['vendor_id']})" if issue['vendor_id'] else " (no vendor-id)"
            output.append(f"{i}. Missing/Invalid vendor ID: {issue['label']} (instance {issue['device_instance']}){vendor_info}")
            output.append(f"   Device URI: {issue['device']}")
            output.append(f"   Address: {issue['address']}")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_description' in issue:
                output.append(f"   Details: {issue['verbose_description']}")
            output.append("")
        elif issue_type == 'unreachable-networks':
            isolation_type = issue.get('isolation_type', 'unknown')
            if isolation_type == 'isolated':
                output.append(f"{i}. Isolated network: {issue['network_name']} (no routing connections)")
            else:
                reachable = issue.get('reachable_networks', 0)
                total = issue.get('total_networks', 0)
                unreachable = total - reachable - 1  # Exclude self
                output.append(f"{i}. Partially isolated network: {issue['network_name']} (can reach {reachable}/{total-1} other networks)")
                output.append(f"   Cannot reach: {unreachable} networks")
            output.append(f"   Network URI: {issue['network']}")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_description' in issue:
                output.append(f"   Details: {issue['verbose_description']}")
            output.append("")
        elif issue_type == 'missing-routers':
            output.append(f"{i}. Missing routing infrastructure: {len(issue['isolated_networks'])} networks lack router connections")
            output.append(f"   Total networks: {issue['total_networks']}")
            output.append(f"   Networks with routing: {issue['routed_networks']}")
            output.append("   Networks without routing:")
            for network in issue['isolated_networks']:
                output.append(f"     - {network['network_label']} ({network['network_uri']})")
            output.append(f"   Problem: {issue['description']}")
            if verbose and 'verbose_details' in issue:
                output.append(f"   Details: {issue['verbose_details']}")
            output.append("")
    
    return "\n".join(output)


def format_json_output(all_issues: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format issues in JSON format."""
    return json.dumps(all_issues, indent=2)
