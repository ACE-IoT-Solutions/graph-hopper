"""
Tests for Subnet Mismatches Check - Phase 2.3

Tests the detection of device subnets that don't match their network topology.
"""

from rdflib import Graph
from graph_hopper.graph_checks.subnet_mismatches import check_subnet_mismatches


def test_empty_graph():
    """Test empty graph returns no issues."""
    graph = Graph()
    issues, affected_triples, affected_nodes = check_subnet_mismatches(graph)
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_module_import():
    """Verify the module can be imported and function exists."""
    from graph_hopper.graph_checks.subnet_mismatches import check_subnet_mismatches
    assert callable(check_subnet_mismatches)


def test_no_subnet_mismatches_ttl():
    """Test devices with IP addresses matching their subnet ranges."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with proper subnet
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://subnet/192.168.1.0/24> a ns1:Subnet ;
        rdfs:label "Main Subnet" ;
        ns1:subnet-of-network <bacnet://network/1000> ;
        ns1:subnet-address "192.168.1.0/24" .
    
    # Device with IP in correct subnet range
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "192.168.1.100" .
    
    # Another device with IP in correct subnet range  
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "192.168.1.200" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_subnet_mismatches(graph)
    
    # Should find no issues - all devices are in correct subnet ranges
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_subnet_mismatch_detection_ttl():
    """Test detection of devices with IP addresses outside their subnet range."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with subnet 192.168.1.0/24
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://subnet/192.168.1.0/24> a ns1:Subnet ;
        rdfs:label "Main Subnet" ;
        ns1:subnet-of-network <bacnet://network/1000> ;
        ns1:subnet-address "192.168.1.0/24" .
    
    # Device with IP OUTSIDE subnet range (should be flagged)
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "10.0.1.100" .
    
    # Device with IP in correct range
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "192.168.1.200" .
        
    # Another device with IP OUTSIDE subnet range (should be flagged)
    <bacnet://device/300> a ns1:Device ;
        rdfs:label "Device 300" ;
        ns1:device-instance 300 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "172.16.1.100" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_subnet_mismatches(graph)
    
    # Should find 2 mismatched devices
    assert len(issues) == 2
    assert all(issue['issue_type'] == 'subnet-mismatches' for issue in issues)
    assert all(issue['severity'] == 'medium' for issue in issues)
    assert len(affected_nodes) == 2


def test_multiple_subnets_mixed_issues_ttl():
    """Test scenario with multiple subnets, some with mismatches."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with first subnet
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://subnet/192.168.1.0/24> a ns1:Subnet ;
        rdfs:label "Subnet A" ;
        ns1:subnet-of-network <bacnet://network/1000> ;
        ns1:subnet-address "192.168.1.0/24" .
    
    <bacnet://subnet/10.0.1.0/24> a ns1:Subnet ;
        rdfs:label "Subnet B" ;
        ns1:subnet-of-network <bacnet://network/1000> ;
        ns1:subnet-address "10.0.1.0/24" .
    
    # Correct device on subnet A
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "192.168.1.100" .
    
    # Incorrect device on subnet A (IP from subnet B range)  
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "10.0.1.200" .
        
    # Correct device on subnet B
    <bacnet://device/300> a ns1:Device ;
        rdfs:label "Device 300" ;
        ns1:device-instance 300 ;
        ns1:device-on-subnet <bacnet://subnet/10.0.1.0/24> ;
        ns1:address "10.0.1.100" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_subnet_mismatches(graph)
    
    # Should find 1 mismatched device (Device 200)
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'subnet-mismatches'
    assert issues[0]['device_label'] == 'Device 200'
    assert issues[0]['device_address'] == '10.0.1.200'
    assert issues[0]['subnet_address'] == '192.168.1.0/24'
    assert len(affected_nodes) == 1


def test_invalid_ip_addresses_ttl():
    """Test handling of malformed or invalid IP addresses."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://subnet/192.168.1.0/24> a ns1:Subnet ;
        rdfs:label "Main Subnet" ;
        ns1:subnet-of-network <bacnet://network/1000> ;
        ns1:subnet-address "192.168.1.0/24" .
    
    # Device with valid IP
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "192.168.1.100" .
    
    # Device with invalid IP address format
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "not-an-ip-address" .
        
    # Device with BACnet address (not IP) - should be skipped  
    <bacnet://device/300> a ns1:Device ;
        rdfs:label "Device 300" ;
        ns1:device-instance 300 ;
        ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
        ns1:address "1001:5" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_subnet_mismatches(graph)
    
    # Should skip invalid IP addresses and only check valid ones
    # Device 100 is correct, devices 200 and 300 should be skipped due to invalid/non-IP addresses
    assert len(issues) == 0
    assert len(affected_nodes) == 0
