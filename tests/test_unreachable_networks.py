from rdflib import Graph
from graph_hopper.graph_checks.unreachable_networks import check_unreachable_networks


def test_empty_graph():
    """Test behavior with empty graph"""
    g = Graph()
    issues, affected_nodes = check_unreachable_networks(g)
    assert len(issues) == 0


def test_module_import():
    """Test that the module can be imported and function exists"""
    from graph_hopper.graph_checks.unreachable_networks import check_unreachable_networks
    assert callable(check_unreachable_networks)


def test_single_network_ttl():
    """Test with a single network in TTL format"""
    ttl_content = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    <bacnet://network/1> a ns1:BACnetNetwork ;
        rdfs:label "Network 1" .
    
    <bacnet://device/123> a ns1:BACnetDevice ;
        rdfs:label "Device 123" ;
        ns1:device-instance 123 ;
        ns1:device-on-network <bacnet://network/1> .
    """
    
    g = Graph()
    g.parse(data=ttl_content, format='turtle')
    
    issues, affected_nodes = check_unreachable_networks(g)
    # Single network should have no isolation issues
    assert len(issues) == 0


def test_isolated_network_ttl():
    """Test with an isolated network in TTL format"""
    ttl_content = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1 with a device
    <bacnet://network/1> a ns1:BACnetNetwork ;
        rdfs:label "Network 1" .
    
    <bacnet://device/123> a ns1:BACnetDevice ;
        rdfs:label "Device 123" ;
        ns1:device-instance 123 ;
        ns1:device-on-network <bacnet://network/1> .
    
    # Network 2 with a device  
    <bacnet://network/2> a ns1:BACnetNetwork ;
        rdfs:label "Network 2" .
        
    <bacnet://device/456> a ns1:BACnetDevice ;
        rdfs:label "Device 456" ;
        ns1:device-instance 456 ;
        ns1:device-on-network <bacnet://network/2> .
    
    # Isolated network 3 with no router connections
    <bacnet://network/3> a ns1:BACnetNetwork ;
        rdfs:label "Isolated Network" .
        
    <bacnet://device/789> a ns1:BACnetDevice ;
        rdfs:label "Device 789" ;
        ns1:device-instance 789 ;
        ns1:device-on-network <bacnet://network/3> .
    
    # Router connecting only networks 1 and 2
    <bacnet://router/1001> a ns1:Router ;
        rdfs:label "Router 1001" ;
        ns1:device-instance 1001 ;
        ns1:device-on-network <bacnet://network/1> ;
        ns1:device-on-network <bacnet://network/2> .
    """
    
    g = Graph()
    g.parse(data=ttl_content, format='turtle')
    
    issues, affected_nodes = check_unreachable_networks(g)
    
    # Should detect isolation issues
    # Network 3 is completely isolated (1 issue)
    # Networks 1&2 are partially isolated - they can reach each other but not Network 3 (2 issues)
    assert len(issues) == 3
    
    # Find the completely isolated network issue
    isolated_issues = [issue for issue in issues if issue['isolation_type'] == 'isolated']
    partial_issues = [issue for issue in issues if issue['isolation_type'] == 'partial']
    
    assert len(isolated_issues) == 1
    assert len(partial_issues) == 2
    
    # Check the isolated network
    isolated_issue = isolated_issues[0]
    assert "Isolated Network" in isolated_issue['network_name']
    assert isolated_issue['reachable_networks'] == 0


def test_connected_networks_ttl():
    """Test with fully connected networks in TTL format"""
    ttl_content = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Network 1
    <bacnet://network/1> a ns1:BACnetNetwork ;
        rdfs:label "Network 1" .
    
    # Network 2
    <bacnet://network/2> a ns1:BACnetNetwork ;
        rdfs:label "Network 2" .
    
    # Network 3
    <bacnet://network/3> a ns1:BACnetNetwork ;
        rdfs:label "Network 3" .
    
    # Router connecting networks 1 and 2
    <bacnet://router/1001> a ns1:Router ;
        rdfs:label "Router 1001" ;
        ns1:device-instance 1001 ;
        ns1:device-on-network <bacnet://network/1> ;
        ns1:device-on-network <bacnet://network/2> .
    
    # Router connecting networks 2 and 3  
    <bacnet://router/1002> a ns1:Router ;
        rdfs:label "Router 1002" ;
        ns1:device-instance 1002 ;
        ns1:device-on-network <bacnet://network/2> ;
        ns1:device-on-network <bacnet://network/3> .
    """
    
    g = Graph()
    g.parse(data=ttl_content, format='turtle')
    
    issues, affected_nodes = check_unreachable_networks(g)
    # All networks are connected, so no issues
    assert len(issues) == 0
