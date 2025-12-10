"""
Tests for Missing Routers Check - Phase 2.2

Tests the detection of multi-network setups without proper routing infrastructure.
"""

from rdflib import Graph
from graph_hopper.graph_checks.missing_routers import check_missing_routers


def test_empty_graph():
    """Test empty graph returns no issues."""
    graph = Graph()
    issues, affected_triples, affected_nodes = check_missing_routers(graph)
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_module_import():
    """Verify the module can be imported and function exists."""
    from graph_hopper.graph_checks.missing_routers import check_missing_routers
    assert callable(check_missing_routers)


def test_single_network_ttl():
    """Test single network with devices - no routing needed."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:address "192.168.1.100" .
    
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:address "192.168.1.200" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_missing_routers(graph)
    
    # Single network - no routing needed
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_multiple_networks_no_routers_ttl():
    """Test multiple networks with devices but no routers - should detect missing routers."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with devices
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:address "192.168.1.100" .
    
    # Network 2000 with devices
    <bacnet://network/2000> a ns1:BACnetNetwork ;
        rdfs:label "Network 2000" .
    
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:address "10.0.1.200" .
        
    # Network 3000 with devices
    <bacnet://network/3000> a ns1:BACnetNetwork ;
        rdfs:label "Network 3000" .
    
    <bacnet://device/300> a ns1:Device ;
        rdfs:label "Device 300" ;
        ns1:device-instance 300 ;
        ns1:device-on-network <bacnet://network/3000> ;
        ns1:address "172.16.1.100" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_missing_routers(graph)
    
    # Should find 3 networks that need routing but have no routers
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'missing-routers'
    assert issues[0]['severity'] == 'medium'
    assert len(issues[0]['isolated_networks']) == 3
    assert issues[0]['total_networks'] == 3
    assert len(affected_nodes) == 3  # The three networks


def test_multiple_networks_with_routers_ttl():
    """Test multiple networks with proper router connections - should be clean."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with devices
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:address "192.168.1.100" .
    
    # Network 2000 with devices
    <bacnet://network/2000> a ns1:BACnetNetwork ;
        rdfs:label "Network 2000" .
    
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:address "10.0.1.200" .
        
    # Router connecting networks 1000 and 2000
    <bacnet://router/1> a ns1:Router ;
        rdfs:label "Router 1" ;
        ns1:device-instance 1001 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> ;
        ns1:address "192.168.1.1" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_missing_routers(graph)
    
    # Networks are connected by router - no missing router issues
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_partial_routing_coverage_ttl():
    """Test scenario with some networks connected but others isolated."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1000 with devices
    <bacnet://network/1000> a ns1:BACnetNetwork ;
        rdfs:label "Network 1000" .
    
    <bacnet://device/100> a ns1:Device ;
        rdfs:label "Device 100" ;
        ns1:device-instance 100 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:address "192.168.1.100" .
    
    # Network 2000 with devices
    <bacnet://network/2000> a ns1:BACnetNetwork ;
        rdfs:label "Network 2000" .
    
    <bacnet://device/200> a ns1:Device ;
        rdfs:label "Device 200" ;
        ns1:device-instance 200 ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:address "10.0.1.200" .
        
    # Network 3000 with devices (isolated)
    <bacnet://network/3000> a ns1:BACnetNetwork ;
        rdfs:label "Network 3000" .
    
    <bacnet://device/300> a ns1:Device ;
        rdfs:label "Device 300" ;
        ns1:device-instance 300 ;
        ns1:device-on-network <bacnet://network/3000> ;
        ns1:address "172.16.1.100" .
        
    # Network 4000 with devices (isolated)
    <bacnet://network/4000> a ns1:BACnetNetwork ;
        rdfs:label "Network 4000" .
    
    <bacnet://device/400> a ns1:Device ;
        rdfs:label "Device 400" ;
        ns1:device-instance 400 ;
        ns1:device-on-network <bacnet://network/4000> ;
        ns1:address "172.20.1.100" .
        
    # Router connecting only networks 1000 and 2000
    <bacnet://router/1> a ns1:Router ;
        rdfs:label "Router 1" ;
        ns1:device-instance 1001 ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> ;
        ns1:address "192.168.1.1" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_missing_routers(graph)
    
    # Should find isolated networks 3000 and 4000
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'missing-routers'
    assert issues[0]['severity'] == 'medium'
    assert len(issues[0]['isolated_networks']) == 2  # Networks 3000 and 4000
    assert issues[0]['total_networks'] == 4
    assert len(affected_nodes) == 2  # Networks 3000 and 4000
