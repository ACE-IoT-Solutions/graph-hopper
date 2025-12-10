"""
Tests for Network Loops Check - Phase 2.4

Tests the detection of circular routing dependencies that can cause broadcast storms.
"""

from rdflib import Graph
from graph_hopper.graph_checks.network_loops import check_network_loops


def test_empty_graph():
    """Test empty graph returns no issues."""
    graph = Graph()
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_module_import():
    """Verify the module can be imported and function exists."""
    from graph_hopper.graph_checks.network_loops import check_network_loops
    assert callable(check_network_loops)


def test_detects_simple_loop():
    """Test detection of simple 2-router loop."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    
    # Simple loop: Router A <-> Router B
    <bacnet://router/1001> a ns1:Router ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> .

    <bacnet://router/1002> a ns1:Router ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:serves-network <bacnet://network/1000> .

    <bacnet://network/1000> a ns1:BACnetNetwork .
    <bacnet://network/2000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should detect one loop
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'network-loops'
    assert issues[0]['severity'] == 'critical'
    assert issues[0]['loop_size'] == 2
    assert len(affected_nodes) >= 2  # At least the two networks


def test_detects_complex_loop():
    """Test detection of 3-network loop."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # 3-network loop: A -> B -> C -> A
    <bacnet://router/2001> a ns1:Router ;
        ns1:device-on-network <bacnet://network/3000> ;
        ns1:serves-network <bacnet://network/4000> .

    <bacnet://router/2002> a ns1:Router ;
        ns1:device-on-network <bacnet://network/4000> ;
        ns1:serves-network <bacnet://network/5000> .

    <bacnet://router/2003> a ns1:Router ;
        ns1:device-on-network <bacnet://network/5000> ;
        ns1:serves-network <bacnet://network/3000> .

    <bacnet://network/3000> a ns1:BACnetNetwork .
    <bacnet://network/4000> a ns1:BACnetNetwork .
    <bacnet://network/5000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should detect complex loop
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'network-loops' 
    assert issues[0]['loop_size'] == 3
    assert 'network/3000' in str(issues[0]['loop_path'])
    assert 'network/4000' in str(issues[0]['loop_path'])
    assert 'network/5000' in str(issues[0]['loop_path'])


def test_no_loops_clean_network():
    """Test that clean network topology shows no loops."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Linear topology: A -> B -> C (no loops)
    <bacnet://router/1001> a ns1:Router ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> .

    <bacnet://router/1002> a ns1:Router ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:serves-network <bacnet://network/3000> .

    <bacnet://network/1000> a ns1:BACnetNetwork .
    <bacnet://network/2000> a ns1:BACnetNetwork .
    <bacnet://network/3000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should find no loops
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_isolated_networks_no_loops():
    """Test that isolated networks without connections show no loops."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Isolated networks (no routers connecting them)
    <bacnet://network/5000> a ns1:BACnetNetwork .
    <bacnet://network/6000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should find no loops
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_complex_loop_from_file():
    """Test detection of complex 3-network loop from TTL file."""
    from pathlib import Path
    
    # Load the test TTL file
    test_file = Path(__file__).parent / 'data' / 'complex_network_loops.ttl'
    assert test_file.exists(), f"Test file {test_file} does not exist"
    
    graph = Graph()
    graph.parse(str(test_file), format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should detect complex loop
    assert len(issues) == 1
    assert issues[0]['issue_type'] == 'network-loops' 
    assert issues[0]['loop_size'] == 3
    
    # Check that all three networks are in the loop path
    loop_path_str = str(issues[0]['loop_path'])
    assert 'network/3000' in loop_path_str
    assert 'network/4000' in loop_path_str
    assert 'network/5000' in loop_path_str
    
    # Check router information is included
    assert 'routers_causing_loop' in issues[0]['details']
    router_connections = issues[0]['details']['routers_causing_loop']
    assert len(router_connections) == 3  # Should have 3 routers
    
    # Verify the specific router connections
    router_names = [conn['router_name'] for conn in router_connections]
    assert '2001' in router_names
    assert '2002' in router_names  
    assert '2003' in router_names


def test_router_information_included():
    """Test that router information is included in loop detection results."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Simple loop: Router A <-> Router B
    <bacnet://router/1001> a ns1:Router ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> .

    <bacnet://router/1002> a ns1:Router ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:serves-network <bacnet://network/1000> .

    <bacnet://network/1000> a ns1:BACnetNetwork .
    <bacnet://network/2000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should detect one loop with router information
    assert len(issues) == 1
    assert 'routers_causing_loop' in issues[0]['details']
    
    router_connections = issues[0]['details']['routers_causing_loop']
    assert len(router_connections) == 2  # Two routers involved
    
    # Check that router information includes the connection details
    for conn in router_connections:
        assert 'router_name' in conn
        assert 'connects_from' in conn  
        assert 'connects_to' in conn
        assert conn['router_name'] in ['1001', '1002']


def test_router_information_in_output():
    """Test that router information is included in the issue output."""
    ttl_data = """
    @prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
    
    # Simple loop: Router A <-> Router B
    <bacnet://router/1001> a ns1:Router ;
        ns1:device-on-network <bacnet://network/1000> ;
        ns1:serves-network <bacnet://network/2000> .

    <bacnet://router/1002> a ns1:Router ;
        ns1:device-on-network <bacnet://network/2000> ;
        ns1:serves-network <bacnet://network/1000> .

    <bacnet://network/1000> a ns1:BACnetNetwork .
    <bacnet://network/2000> a ns1:BACnetNetwork .
    """
    
    graph = Graph()
    graph.parse(data=ttl_data, format='turtle')
    
    issues, affected_triples, affected_nodes = check_network_loops(graph)
    
    # Should detect one loop
    assert len(issues) == 1
    
    # Check that router information is included
    issue = issues[0]
    assert 'details' in issue
    assert 'routers_causing_loop' in issue['details']
    
    routers_info = issue['details']['routers_causing_loop']
    assert len(routers_info) == 2
    
    # Check that router information has expected fields
    for router_info in routers_info:
        assert 'router_uri' in router_info
        assert 'router_name' in router_info
        assert 'connects_from' in router_info
        assert 'connects_to' in router_info
        assert 'connection_type' in router_info
    
    # Check specific router URIs are present
    router_uris = [r['router_uri'] for r in routers_info]
    assert 'bacnet://router/1001' in router_uris
    assert 'bacnet://router/1002' in router_uris
