"""
Broadcast Domain Analysis - Phase 3.2

Analyzes BACnet broadcast domains for performance issues and configuration problems.
Identifies inefficient BBMD configurations, large broadcast domains, and potential 
broadcast storm risks.
"""

from typing import List, Set, Dict, Tuple, Any
from rdflib import Graph, URIRef
from collections import defaultdict
import ipaddress


def check_broadcast_domains(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Analyze BACnet broadcast domains for performance and configuration issues.
    
    Checks for:
    1. Large broadcast domains (many subnets without proper segmentation)
    2. Missing BBMD (BACnet Broadcast Management Device) configurations
    3. Inefficient BBMD placements
    4. Overlapping broadcast domains
    5. IP subnet broadcast scope issues
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = set()
    
    # Build broadcast domain mapping
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Find networks, subnets, and BBMDs
    networks = set()
    subnets = set()
    bbmds = set()
    
    network_class = bacnet_ns + "BACnetNetwork"
    subnet_class = bacnet_ns + "Subnet"
    bbmd_class = bacnet_ns + "BBMD"
    
    for network, _, _ in graph.triples((None, rdf_type, network_class)):
        networks.add(network)
    
    for subnet, _, _ in graph.triples((None, rdf_type, subnet_class)):
        subnets.add(subnet)
    
    for bbmd, _, _ in graph.triples((None, rdf_type, bbmd_class)):
        bbmds.add(bbmd)
    
    # Analyze broadcast domains
    broadcast_domains = _analyze_broadcast_domains(graph, networks, subnets, bbmds)
    
    # Check for various broadcast domain issues
    issues.extend(_check_large_broadcast_domains(broadcast_domains, verbose))
    issues.extend(_check_missing_bbmd_coverage(graph, broadcast_domains, verbose))
    issues.extend(_check_inefficient_bbmd_placement(graph, broadcast_domains, bbmds, verbose))
    issues.extend(_check_broadcast_domain_overlap(broadcast_domains, verbose))
    
    # Add affected nodes
    for issue in issues:
        if 'network' in issue:
            affected_nodes.add(issue['network'])
        if 'subnet' in issue:
            affected_nodes.add(issue['subnet'])
        if 'affected_networks' in issue.get('details', {}):
            affected_nodes.update(issue['details']['affected_networks'])
    
    return issues, affected_nodes


def _analyze_broadcast_domains(graph: Graph, networks: Set, subnets: Set, bbmds: Set) -> Dict[str, Dict[str, Any]]:
    """
    Analyze the structure of broadcast domains in the network.
    
    Returns:
        Dictionary containing broadcast domain analysis
    """
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    subnet_of_network = bacnet_ns + "subnet-of-network"
    device_on_network = bacnet_ns + "device-on-network"
    device_on_subnet = bacnet_ns + "device-on-subnet"
    bbmd_on_subnet = bacnet_ns + "bbmd-on-subnet"
    address_prop = bacnet_ns + "address"
    
    domains: Dict[str, Dict[str, Any]] = {}
    
    # Map subnets to networks
    subnet_to_network = {}
    network_subnets = defaultdict(set)
    
    for subnet, _, network in graph.triples((None, subnet_of_network, None)):
        if subnet in subnets and network in networks:
            subnet_to_network[subnet] = network
            network_subnets[network].add(subnet)
    
    # Analyze each network as a potential broadcast domain
    for network in networks:
        network_str = str(network)
        devices_set: Set[str] = set()
        bbmds_set: Set[str] = set()
        
        # Count devices on network and subnets
        for device, _, _ in graph.triples((None, device_on_network, network)):
            devices_set.add(str(device))
        
        for subnet in network_subnets[network]:
            for device, _, _ in graph.triples((None, device_on_subnet, subnet)):
                devices_set.add(str(device))
        
        # Find BBMDs in this domain
        for subnet in network_subnets[network]:
            for bbmd, _, _ in graph.triples((None, bbmd_on_subnet, subnet)):
                if bbmd in bbmds:
                    bbmds_set.add(str(bbmd))
        
        # Analyze IP ranges for subnet scope
        device_addresses = []
        for device_str in devices_set:
            device_uri = URIRef(device_str)
            for _, _, addr in graph.triples((device_uri, address_prop, None)):
                device_addresses.append(str(addr))
        
        ip_ranges = _extract_ip_ranges(device_addresses)
        
        domain_info = {
            'network': network_str,
            'subnets': list(network_subnets[network]),
            'subnet_count': len(network_subnets[network]),
            'devices': devices_set,
            'bbmds': bbmds_set,
            'ip_ranges': ip_ranges,
            'broadcast_scope': _determine_broadcast_scope(ip_ranges),
            'device_count': len(devices_set)
        }
        
        domains[network_str] = domain_info
    
    return domains


def _extract_ip_ranges(addresses: List[str]) -> Set[str]:
    """Extract IP network ranges from device addresses."""
    ip_networks = set()
    
    for addr in addresses:
        # Handle various address formats
        if ':' in addr:
            # Could be IP:port format
            ip_part = addr.split(':')[0]
        else:
            ip_part = addr
        
        # Check if it looks like an IP address
        if '.' in ip_part and any(c.isdigit() for c in ip_part):
            try:
                ip = ipaddress.IPv4Address(ip_part)
                # Assume /24 subnet for analysis (common in BACnet)
                network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                ip_networks.add(str(network))
            except (ipaddress.AddressValueError, ValueError):
                pass
    
    return ip_networks


def _determine_broadcast_scope(ip_ranges: Set[str]) -> str:
    """Determine the broadcast scope based on IP ranges."""
    if not ip_ranges:
        return 'local'  # No IP addresses, likely MSTP or local
    
    range_count = len(ip_ranges)
    if range_count == 1:
        return 'subnet'
    elif range_count <= 3:
        return 'moderate'
    else:
        return 'wide'


def _check_large_broadcast_domains(domains: Dict[str, Dict[str, Any]], verbose: bool) -> List[Dict[str, Any]]:
    """Check for broadcast domains that are too large for efficient operation."""
    issues = []
    
    # Thresholds for broadcast domain sizes
    SUBNET_WARNING_THRESHOLD = 5  # subnets in one broadcast domain
    SUBNET_CRITICAL_THRESHOLD = 10
    DEVICE_WARNING_THRESHOLD = 200  # devices in one broadcast domain
    DEVICE_CRITICAL_THRESHOLD = 500
    
    for domain_id, domain in domains.items():
        subnet_count = domain['subnet_count']
        device_count = domain['device_count']
        
        # Check subnet count thresholds
        if subnet_count >= SUBNET_CRITICAL_THRESHOLD or device_count >= DEVICE_CRITICAL_THRESHOLD:
            severity = 'critical'
            issue_type = 'broadcast-domain-critical'
        elif subnet_count >= SUBNET_WARNING_THRESHOLD or device_count >= DEVICE_WARNING_THRESHOLD:
            severity = 'warning'
            issue_type = 'broadcast-domain-warning'
        else:
            continue  # Domain size is acceptable
        
        network_name = _get_network_name_from_uri(domain_id)
        
        issue = {
            'issue_type': issue_type,
            'severity': severity,
            'network': domain_id,
            'network_name': network_name,
            'subnet_count': subnet_count,
            'device_count': device_count,
            'broadcast_scope': domain['broadcast_scope'],
            'description': f"Large broadcast domain: {subnet_count} subnets, {device_count} devices",
            'details': {
                'subnet_threshold': SUBNET_WARNING_THRESHOLD if severity == 'warning' else SUBNET_CRITICAL_THRESHOLD,
                'device_threshold': DEVICE_WARNING_THRESHOLD if severity == 'warning' else DEVICE_CRITICAL_THRESHOLD,
                'performance_impact': _get_broadcast_performance_impact(subnet_count, device_count, severity),
                'recommendation': _get_broadcast_domain_recommendation(subnet_count, device_count, severity),
                'affected_subnets': [str(s) for s in domain['subnets']],
                'ip_ranges': list(domain['ip_ranges'])
            }
        }
        
        if verbose:
            issue['verbose_description'] = (
                f"Broadcast domain {network_name} spans {subnet_count} subnets with {device_count} devices. "
                f"Large broadcast domains can cause network congestion due to broadcast traffic "
                f"propagation. Consider implementing BBMD (BACnet Broadcast Management Device) or network "
                f"segmentation to reduce broadcast scope and improve performance."
            )
        
        issues.append(issue)
    
    return issues


def _check_missing_bbmd_coverage(graph: Graph, domains: Dict[str, Dict[str, Any]], verbose: bool) -> List[Dict[str, Any]]:
    """Check for broadcast domains that should have BBMD coverage but don't."""
    issues = []
    
    for domain_id, domain in domains.items():
        subnet_count = domain['subnet_count']
        device_count = domain['device_count']
        bbmd_count = len(domain['bbmds'])
        scope = domain['broadcast_scope']
        
        # Determine if BBMD is needed based on domain characteristics
        needs_bbmd = (
            subnet_count > 2 or  # Multiple subnets suggest inter-subnet communication
            device_count > 100 or  # Large device count benefits from broadcast management
            scope in ['moderate', 'wide'] or  # Multiple IP ranges need coordination
            len(domain['ip_ranges']) > 1  # Multiple IP networks
        )
        
        if needs_bbmd and bbmd_count == 0:
            network_name = _get_network_name_from_uri(domain_id)
            
            issue = {
                'issue_type': 'missing-bbmd-coverage',
                'severity': 'warning',
                'network': domain_id,
                'network_name': network_name,
                'subnet_count': subnet_count,
                'device_count': device_count,
                'broadcast_scope': scope,
                'description': f"Missing BBMD coverage for complex broadcast domain ({subnet_count} subnets, {device_count} devices)",
                'details': {
                    'why_needed': _explain_bbmd_need(subnet_count, device_count, scope),
                    'recommendation': _get_bbmd_placement_recommendation(domain),
                    'affected_subnets': [str(s) for s in domain['subnets']],
                    'performance_risk': 'Broadcast storms and inefficient device discovery'
                }
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f"Broadcast domain {network_name} lacks BBMD (BACnet Broadcast Management Device) coverage. "
                    f"With {subnet_count} subnets and {device_count} devices across {scope} broadcast scope, "
                    f"BBMD implementation would improve broadcast efficiency and prevent network congestion."
                )
            
            issues.append(issue)
    
    return issues


def _check_inefficient_bbmd_placement(graph: Graph, domains: Dict[str, Dict[str, Any]], bbmds: Set, verbose: bool) -> List[Dict[str, Any]]:
    """Check for inefficient BBMD placements that could be optimized."""
    issues = []
    
    # This is a placeholder for more sophisticated BBMD placement analysis
    # Could check for:
    # - BBMDs on edge subnets vs central subnets
    # - Redundant BBMD configurations
    # - Missing BBMD redundancy in critical domains
    
    return issues


def _check_broadcast_domain_overlap(domains: Dict[str, Dict[str, Any]], verbose: bool) -> List[Dict[str, Any]]:
    """Check for overlapping broadcast domains that could cause conflicts."""
    issues = []
    
    # Group domains by IP ranges to find overlaps
    ip_range_to_domains = defaultdict(list)
    
    for domain_id, domain in domains.items():
        for ip_range in domain['ip_ranges']:
            ip_range_to_domains[ip_range].append(domain_id)
    
    # Check for overlaps
    for ip_range, domain_list in ip_range_to_domains.items():
        if len(domain_list) > 1:
            # Multiple domains share the same IP range - potential conflict
            issue = {
                'issue_type': 'broadcast-domain-overlap',
                'severity': 'warning',
                'ip_range': ip_range,
                'overlapping_domains': [_get_network_name_from_uri(d) for d in domain_list],
                'domain_count': len(domain_list),
                'description': f"Broadcast domain overlap: {len(domain_list)} domains share IP range {ip_range}",
                'details': {
                    'affected_networks': domain_list,
                    'conflict_risk': 'Potential broadcast conflicts and address confusion',
                    'recommendation': 'Review network segmentation and ensure proper VLAN/subnet isolation'
                }
            }
            
            if verbose:
                domain_names = [_get_network_name_from_uri(d) for d in domain_list]
                issue['verbose_description'] = (
                    f"Networks {', '.join(domain_names)} have overlapping broadcast domains in IP range {ip_range}. "
                    f"This can cause broadcast traffic conflicts and device discovery issues."
                )
            
            issues.append(issue)
    
    return issues


def _get_network_name_from_uri(network_uri: str) -> str:
    """Extract a readable name from network URI."""
    if '/' in network_uri:
        return network_uri.split('/')[-1]
    return network_uri


def _get_broadcast_performance_impact(subnet_count: int, device_count: int, severity: str) -> str:
    """Describe the performance impact of large broadcast domains."""
    if severity == 'critical':
        return f"Severe broadcast traffic with {device_count} devices across {subnet_count} subnets causing network congestion"
    else:
        return f"Moderate broadcast overhead with {device_count} devices affecting network performance"


def _get_broadcast_domain_recommendation(subnet_count: int, device_count: int, severity: str) -> str:
    """Generate recommendations for large broadcast domains."""
    if severity == 'critical':
        return (
            f"Immediately implement network segmentation. Deploy BBMD to manage broadcast traffic across "
            f"{subnet_count} subnets. Consider VLANs or physical network separation to reduce broadcast scope. "
            f"Target maximum 3-4 subnets per broadcast domain."
        )
    else:
        return (
            "Consider implementing BBMD for better broadcast management. Monitor network performance and "
            "plan for segmentation if device count exceeds 300 or subnet count exceeds 6."
        )


def _explain_bbmd_need(subnet_count: int, device_count: int, scope: str) -> str:
    """Explain why BBMD is needed for this domain."""
    reasons = []
    
    if subnet_count > 2:
        reasons.append(f"{subnet_count} subnets require inter-subnet broadcast coordination")
    
    if device_count > 100:
        reasons.append(f"{device_count} devices generate significant broadcast traffic")
    
    if scope in ['moderate', 'wide']:
        reasons.append(f"{scope} broadcast scope spans multiple IP ranges")
    
    return "; ".join(reasons)


def _get_bbmd_placement_recommendation(domain: Dict[str, Any]) -> str:
    """Recommend optimal BBMD placement for a domain."""
    subnet_count = domain['subnet_count']
    
    if subnet_count <= 3:
        return "Deploy 1 BBMD on the central subnet with BDT entries for all subnets"
    elif subnet_count <= 6:
        return "Deploy 2 BBMDs for redundancy on central subnets with overlapping BDT coverage"
    else:
        return f"Deploy {(subnet_count + 2) // 3} BBMDs distributed across subnets for optimal coverage"
