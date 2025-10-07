"""
Oversized Networks Check - Phase 3.1

Detects networks with too many devices that can impact performance.
Network-type-aware thresholds based on BACnet best practices:
- MSTP Networks: Warning: 15+ devices, Critical: 30+ devices (due to token-passing constraints)
- IP Networks: Warning: 50+ devices, Critical: 100+ devices (higher capacity)
- Other Networks: Warning: 25+ devices, Critical: 50+ devices (conservative default)
"""

from typing import List, Set, Dict, Tuple, Any
from rdflib import Graph, URIRef
from collections import defaultdict


def check_oversized_networks(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Check for networks with too many devices that could impact performance.
    
    Network-type-aware BACnet best practices:
    - MSTP Networks: Warning: 15+ devices, Critical: 30+ devices (token-passing limitations)
    - IP Networks: Warning: 50+ devices, Critical: 100+ devices (higher capacity)
    - Other Networks: Warning: 25+ devices, Critical: 50+ devices (conservative default)
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = set()
    
    # Build network device count mapping
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    network_class = bacnet_ns + "BACnetNetwork"
    device_on_network = bacnet_ns + "device-on-network"
    device_on_subnet = bacnet_ns + "device-on-subnet"
    subnet_of_network = bacnet_ns + "subnet-of-network"
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Find all networks
    networks = set()
    for network, _, _ in graph.triples((None, rdf_type, network_class)):
        networks.add(network)
    
    if not networks:
        return issues, affected_nodes
    
    # Count devices per network
    network_device_counts = defaultdict(set)  # Use set to avoid double-counting
    
    # Count devices directly on networks
    for device, _, network in graph.triples((None, device_on_network, None)):
        if network in networks:
            network_device_counts[network].add(device)
    
    # Count devices on subnets (these count toward the parent network)
    for device, _, subnet in graph.triples((None, device_on_subnet, None)):
        # Find which network this subnet belongs to
        for _, _, network in graph.triples((subnet, subnet_of_network, None)):
            if network in networks:
                network_device_counts[network].add(device)
    
    # Analyze each network for oversizing with network-type-aware thresholds
    for network, devices in network_device_counts.items():
        device_count = len(devices)
        
        # Detect network type and set appropriate thresholds
        network_type = _detect_network_type(graph, network, devices)
        warning_threshold, critical_threshold = _get_thresholds_for_type(network_type)
        
        if device_count >= critical_threshold:
            severity = 'critical'
            performance_impact = 'severe'
            description = f'{network_type.upper()} network has {device_count} devices (critically high - performance severely impacted)'
            issue_type = 'oversized-networks-critical'
            threshold = critical_threshold
        elif device_count >= warning_threshold:
            severity = 'warning'
            performance_impact = 'moderate'
            description = f'{network_type.upper()} network has {device_count} devices (high - performance may be impacted)'
            issue_type = 'oversized-networks-warning'
            threshold = warning_threshold
        else:
            continue  # No issue
        
        network_name = _get_network_name(graph, network)
        
        issue = {
            'issue_type': issue_type,
            'severity': severity,
            'network': str(network),
            'network_name': network_name,
            'network_type': network_type,
            'device_count': device_count,
            'threshold': threshold,
            'description': description,
            'details': {
                'warning_threshold': warning_threshold,
                'critical_threshold': critical_threshold,
                'performance_impact': performance_impact,
                'recommendation': _get_recommendation(device_count, network_type, warning_threshold, critical_threshold),
                'device_breakdown': _get_device_breakdown(graph, devices) if verbose else None
            }
        }
        
        if verbose:
            issue['verbose_description'] = (
                f'{network_type.upper()} network {network_name} contains {device_count} devices, which exceeds '
                f'BACnet best practice recommendations for {network_type.upper()} networks (>{warning_threshold}). '
                f'{network_type.upper()} networks with more than {warning_threshold} devices can experience '
                f'increased broadcast traffic, slower response times, and potential network congestion. '
                f'Consider segmenting this network or implementing additional subnets to improve performance.'
            )
        
        issues.append(issue)
        affected_nodes.add(str(network))
    
    return issues, affected_nodes


def _get_network_name(graph: Graph, network) -> str:
    """Get human-readable name for a network."""
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    
    # Try to get the label
    for _, _, label_value in graph.triples((network, rdfs_label, None)):
        return str(label_value)
    
    # Try to get network number
    for _, _, number_value in graph.triples((network, bacnet_ns + "network-number", None)):
        return f"Network {number_value}"
    
    # Fallback to URI
    return str(network).split('/')[-1] if '/' in str(network) else str(network)


def _detect_network_type(graph: Graph, network, devices: Set) -> str:
    """
    Detect the network type based on network properties and device addresses.
    
    Detection methods (in order of preference):
    1. Explicit network-type property
    2. Network label analysis (contains "MSTP", "IP", "Ethernet", etc.)
    3. Network URI analysis (path contains network type indicators)
    4. Device address pattern analysis (IP addresses vs numeric addresses)
    
    Returns:
        Network type: 'mstp', 'ip', 'ethernet', or 'other'
    """
    bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Method 1: Check for explicit network-type property
    network_type_prop = bacnet_ns + "network-type"
    for _, _, type_value in graph.triples((network, network_type_prop, None)):
        type_str = str(type_value).lower()
        if 'mstp' in type_str or 'master-slave' in type_str or 'token-passing' in type_str:
            return 'mstp'
        elif 'ip' in type_str or 'ethernet' in type_str or 'bacnet/ip' in type_str:
            return 'ip'
        elif 'arcnet' in type_str:
            return 'arcnet'
        elif 'ptp' in type_str or 'point-to-point' in type_str:
            return 'ptp'
    
    # Method 2: Analyze network label
    for _, _, label_value in graph.triples((network, rdfs_label, None)):
        label_str = str(label_value).lower()
        if 'mstp' in label_str or 'master-slave' in label_str or 'token' in label_str:
            return 'mstp'
        elif 'ip' in label_str or 'ethernet' in label_str or 'tcp' in label_str:
            return 'ip'
        elif 'arcnet' in label_str:
            return 'arcnet'
        elif 'ptp' in label_str or 'point-to-point' in label_str:
            return 'ptp'
    
    # Method 3: Analyze network URI
    network_uri = str(network).lower()
    if 'mstp' in network_uri or 'master-slave' in network_uri:
        return 'mstp'
    elif 'ip' in network_uri or 'ethernet' in network_uri:
        return 'ip'
    elif 'arcnet' in network_uri:
        return 'arcnet'
    elif 'ptp' in network_uri:
        return 'ptp'
    
    # Method 4: Analyze device addresses to infer network type
    device_addresses = []
    address_prop = bacnet_ns + "address"
    
    for device in devices:
        for _, _, addr_value in graph.triples((device, address_prop, None)):
            device_addresses.append(str(addr_value))
    
    if device_addresses:
        ip_addresses = 0
        numeric_addresses = 0
        
        for addr in device_addresses[:10]:  # Sample first 10 addresses
            # Check if it looks like an IP address (contains dots and numbers)
            if '.' in addr and any(c.isdigit() for c in addr):
                # More sophisticated IP address check
                parts = addr.split('.')
                if len(parts) == 4:
                    try:
                        all([0 <= int(p) <= 255 for p in parts])
                        ip_addresses += 1
                        continue
                    except ValueError:
                        pass
                # Could be IP:port format like "192.168.1.1:47808"
                elif ':' in addr:
                    ip_part = addr.split(':')[0]
                    parts = ip_part.split('.')
                    if len(parts) == 4:
                        try:
                            all([0 <= int(p) <= 255 for p in parts])
                            ip_addresses += 1
                            continue
                        except ValueError:
                            pass
            
            # Check if it's a simple numeric address (typical for MSTP)
            if addr.isdigit() and 1 <= int(addr) <= 127:
                numeric_addresses += 1
        
        # If most addresses are IP-like, probably an IP network
        if ip_addresses > numeric_addresses:
            return 'ip'
        # If most addresses are simple numeric (1-127), likely MSTP
        elif numeric_addresses > 0 and numeric_addresses >= ip_addresses:
            return 'mstp'
    
    # Default fallback
    return 'other'


def _get_thresholds_for_type(network_type: str) -> Tuple[int, int]:
    """
    Get warning and critical thresholds based on network type.
    
    Thresholds based on BACnet best practices:
    - MSTP: Limited by token-passing protocol, typically max 127 addresses, practical limit much lower
    - IP: Higher capacity, limited mainly by broadcast domain size
    - ARCNET: Similar to MSTP with token-passing constraints  
    - PTP: Point-to-point connections, should only have 2 devices
    - Other: Conservative defaults
    
    Returns:
        Tuple of (warning_threshold, critical_threshold)
    """
    thresholds = {
        'mstp': (15, 30),      # MSTP networks - token passing limitations
        'ip': (50, 100),       # IP networks - higher capacity 
        'ethernet': (50, 100), # Ethernet networks - treat like IP
        'arcnet': (15, 25),    # ARCNET - token passing like MSTP
        'ptp': (2, 3),         # Point-to-point - should only have 2 devices
        'other': (25, 50)      # Conservative default for unknown types
    }
    
    return thresholds.get(network_type, thresholds['other'])


def _get_recommendation(device_count: int, network_type: str, warning_threshold: int, critical_threshold: int) -> str:
    """Generate network-type-aware recommendations for oversized networks."""
    
    if network_type == 'mstp':
        if device_count >= critical_threshold:
            return (
                f"CRITICAL: MSTP networks with {device_count} devices severely impact token passing performance. "
                f"Immediately segment this network. MSTP best practices recommend max 15-20 devices per segment. "
                f"Consider splitting into multiple MSTP segments or migrating high-traffic devices to IP networks. "
                f"Token circulation time increases exponentially with device count."
            )
        else:  # warning level
            return (
                f"MSTP network approaching capacity limits. Consider segmentation before reaching {critical_threshold} devices. "
                f"MSTP token-passing protocol becomes increasingly inefficient with more devices. "
                f"Monitor response times and consider splitting the network if delays are observed."
            )
    
    elif network_type == 'ip':
        if device_count >= critical_threshold:
            return (
                f"Immediately segment this IP network. Consider implementing VLANs or subnets with {warning_threshold//2}-{warning_threshold} devices each. "
                f"Use routers to connect segments and implement BBMD (BACnet Broadcast Management Device) "
                f"to control broadcast traffic across network boundaries."
            )
        else:  # warning level
            return (
                f"Consider segmenting this IP network before reaching {critical_threshold} devices. "
                f"Target {warning_threshold//2}-{warning_threshold//1.5:.0f} devices per subnet for optimal performance. "
                f"Monitor broadcast traffic and network response times."
            )
    
    elif network_type == 'ptp':
        return (
            f"Point-to-Point networks should only have 2 devices. "
            f"Current configuration with {device_count} devices indicates a network topology issue. "
            f"Verify network configuration and consider using a different network type."
        )
    
    else:  # other/unknown network types
        if device_count >= critical_threshold:
            return (
                f"Network has reached critical device density. Implement network segmentation immediately. "
                f"Consider splitting into segments with {warning_threshold//2}-{warning_threshold} devices each. "
                f"Use appropriate routing/bridging based on the physical network type."
            )
        else:  # warning level
            return (
                f"Monitor network performance and consider segmentation as device count approaches {critical_threshold}. "
                f"Network type '{network_type}' may have specific constraints - consult vendor documentation."
            )


def _get_device_breakdown(graph: Graph, devices: Set) -> Dict[str, Any]:
    """Get detailed breakdown of devices on the network."""
    device_types = defaultdict(int)
    device_list = []
    
    for device in devices:
        # Get device type/name
        device_name = str(device).split('/')[-1] if '/' in str(device) else str(device)
        device_list.append(device_name)
        
        # Count by type (simplified - could be enhanced with more specific device type detection)
        device_types['BACnetDevice'] += 1
    
    return {
        'total_devices': len(devices),
        'device_types': dict(device_types),
        'sample_devices': device_list[:10],  # Show first 10 as sample
        'truncated': len(device_list) > 10
    }
