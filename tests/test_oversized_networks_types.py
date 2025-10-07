"""
Additional tests for network-type-aware oversized networks detection.
"""

from rdflib import Graph
from graph_hopper.graph_checks.oversized_networks import check_oversized_networks


def test_mstp_network_type_detection():
    """Test that MSTP networks are properly detected and use lower thresholds."""
    # Create TTL data with MSTP network (17 devices - exceeds MSTP warning threshold of 15)
    devices = []
    for i in range(1, 18):  # 17 devices
        devices.append(f"""
    <http://example.com/device/mstp{i}> a ns1:Device ;
        ns1:device-instance {i} ;
        ns1:address "{i}" ;
        ns1:device-on-network <http://example.com/network/mstp-test> ;
        rdfs:label "MSTP Device {i}" .""")

    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    <http://example.com/network/mstp-test> a ns1:BACnetNetwork ;
        rdfs:label "MSTP Network Test" .
    {"".join(devices)}
    """

    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')

    issues, affected_nodes = check_oversized_networks(graph)

    # Should detect MSTP network warning (17 > 15 threshold)
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'oversized-networks-warning'
    assert issues[0]['network_type'] == 'mstp'
    assert issues[0]['device_count'] == 17
    assert issues[0]['threshold'] == 15
    assert issues[0]['details']['critical_threshold'] == 30
    
    # Check that recommendation mentions MSTP-specific concerns
    recommendation = issues[0]['details']['recommendation']
    assert 'token' in recommendation.lower()


def test_ip_network_type_detection():
    """Test that IP networks are properly detected and use higher thresholds."""
    # Create TTL data with IP network (60 devices - exceeds IP warning threshold of 50)
    devices = []
    for i in range(1, 61):  # 60 devices
        devices.append(f"""
    <http://example.com/device/ip{i}> a ns1:Device ;
        ns1:device-instance {1000+i} ;
        ns1:address "192.168.1.{i}" ;
        ns1:device-on-network <http://example.com/network/ip-test> ;
        rdfs:label "IP Device {i}" .""")

    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    <http://example.com/network/ip-test> a ns1:BACnetNetwork ;
        rdfs:label "IP Network Test" .
    {"".join(devices)}
    """

    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')

    issues, affected_nodes = check_oversized_networks(graph)

    # Should detect IP network warning (60 > 50 threshold)  
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'oversized-networks-warning'
    assert issues[0]['network_type'] == 'ip'
    assert issues[0]['device_count'] == 60
    assert issues[0]['threshold'] == 50
    assert issues[0]['details']['critical_threshold'] == 100
    
    # Check that recommendation mentions IP-specific concerns
    recommendation = issues[0]['details']['recommendation']
    assert 'vlan' in recommendation.lower() or 'subnet' in recommendation.lower()


def test_network_type_comparison():
    """Test that MSTP and IP networks have different thresholds for same device count."""
    # Create identical device count (25 devices) on both MSTP and IP networks
    
    # MSTP network with 25 devices
    mstp_devices = []
    for i in range(1, 26):
        mstp_devices.append(f"""
    <http://example.com/device/mstp{i}> a ns1:Device ;
        ns1:device-instance {i} ;
        ns1:address "{i}" ;
        ns1:device-on-network <http://example.com/network/mstp-compare> .""")

    # IP network with 25 devices  
    ip_devices = []
    for i in range(1, 26):
        ip_devices.append(f"""
    <http://example.com/device/ip{i}> a ns1:Device ;
        ns1:device-instance {100+i} ;
        ns1:address "10.0.0.{i}" ;
        ns1:device-on-network <http://example.com/network/ip-compare> .""")

    ttl_data = f"""
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    <http://example.com/network/mstp-compare> a ns1:BACnetNetwork ;
        rdfs:label "MSTP Compare Network" .
        
    <http://example.com/network/ip-compare> a ns1:BACnetNetwork ;
        rdfs:label "IP Compare Network" .
        
    {"".join(mstp_devices)}
    {"".join(ip_devices)}
    """

    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')

    issues, affected_nodes = check_oversized_networks(graph)

    # Should have 1 issue: MSTP network triggers warning (25 > 15), IP network doesn't (25 < 50)
    assert len(issues) == 1
    assert issues[0]['network_type'] == 'mstp'
    assert issues[0]['issue_type'] == 'oversized-networks-warning'
    assert issues[0]['device_count'] == 25
