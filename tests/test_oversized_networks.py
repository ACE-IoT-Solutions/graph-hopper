"""
Tests for Oversized Networks Check - Phase 3.1

Tests the detection of networks with too many devices that can impact performance.
Based on BACnet best practices, networks should typically have 50-100 devices per segment.
"""

from rdflib import Graph
from graph_hopper.graph_checks.oversized_networks import check_oversized_networks


def test_empty_graph():
    """Test empty graph returns no issues."""
    graph = Graph()
    issues, affected_triples, affected_nodes = check_oversized_networks(graph)
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_module_import():
    """Verify the module can be imported and function exists."""
    from graph_hopper.graph_checks.oversized_networks import check_oversized_networks
    assert callable(check_oversized_networks)


def test_normal_sized_networks():
    """Test that networks with normal device counts show no issues."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Network with acceptable number of devices (under 50)
    <bacnet://network/1000> a ns1:BACnetNetwork .
    
    <bacnet://device/1000:1> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/1000> .
    <bacnet://device/1000:2> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/1000> .
    <bacnet://device/1000:3> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/1000> .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_oversized_networks(graph)
    
    # Should find no issues
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_detects_oversized_network():
    """Test detection of networks with too many devices."""
    # Create TTL data with a network containing many devices (over warning threshold)
    # Using 30 devices which exceeds warning threshold of 25 for 'other' network type
    devices = []
    for i in range(1, 31):  # 30 devices - exceeds warning threshold of 25 for 'other' type
        devices.append(f"""
    <bacnet://device/2000:{i}> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/2000> .""")

    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .

    <bacnet://network/2000> a ns1:BACnetNetwork .
    {"".join(devices)}
    """

    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')

    issues, affected_triples, affected_nodes = check_oversized_networks(graph)

    # Should detect oversized network (warning level for 'other' network type)
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'oversized-networks-warning'
    assert issues[0]['severity'] == 'warning'  # Warning level for 25+ devices on 'other' network type
    assert issues[0]['network'] == 'bacnet://network/2000'
    assert issues[0]['device_count'] == 30
    assert 'network/2000' in str(affected_nodes)


def test_detects_critical_oversized_network():
    """Test detection of networks with critically high device counts."""
    # Create TTL data with a network containing too many devices (over critical threshold)
    devices = []
    for i in range(1, 126):  # 125 devices - exceeds critical threshold of 100
        devices.append(f"""
    <bacnet://device/3000:{i}> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/3000> .""")
    
    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    <bacnet://network/3000> a ns1:BACnetNetwork .
    {"".join(devices)}
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_oversized_networks(graph)
    
    # Should detect critically oversized network
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'oversized-networks-critical'
    assert issues[0]['severity'] == 'critical'  # Critical level for 100+ devices
    assert issues[0]['network'] == 'bacnet://network/3000'
    assert issues[0]['device_count'] == 125
    assert 'performance_impact' in issues[0]['details']
    assert 'recommendation' in issues[0]['details']


def test_subnet_device_counting():
    """Test that devices on subnets are counted correctly."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Network with subnet
    <bacnet://network/4000> a ns1:BACnetNetwork .
    <bacnet://subnet/4000:1> a ns1:BACnetSubnet ;
        ns1:subnet-of-network <bacnet://network/4000> .
    
    # Devices on the subnet (should count toward network total)
    <bacnet://device/4000:1> a ns1:BACnetDevice ;
        ns1:device-on-subnet <bacnet://subnet/4000:1> .
    <bacnet://device/4000:2> a ns1:BACnetDevice ;
        ns1:device-on-subnet <bacnet://subnet/4000:1> .
    
    # Devices directly on network
    <bacnet://device/4000:10> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/4000> .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_oversized_networks(graph)
    
    # Should find no issues (only 3 devices total)
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_multiple_networks_mixed_sizes():
    """Test detection with multiple networks of different sizes."""
    # Create data with one normal network and one oversized network
    normal_devices = []
    for i in range(1, 11):  # 10 devices - normal size
        normal_devices.append(f"""
    <bacnet://device/5000:{i}> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/5000> .""")
    
    oversized_devices = []
    for i in range(1, 61):  # 60 devices - over warning threshold
        oversized_devices.append(f"""
    <bacnet://device/6000:{i}> a ns1:BACnetDevice ;
        ns1:device-on-network <bacnet://network/6000> .""")
    
    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    <bacnet://network/5000> a ns1:BACnetNetwork .
    <bacnet://network/6000> a ns1:BACnetNetwork .
    {"".join(normal_devices)}
    {"".join(oversized_devices)}
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_oversized_networks(graph)
    
    # Should detect only the oversized network
    assert len(issues) == 1
    assert issues[0]['network'] == 'bacnet://network/6000'
    assert issues[0]['device_count'] == 60
    assert len(affected_nodes) == 1
