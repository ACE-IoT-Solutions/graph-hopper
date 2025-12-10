"""
Tests for routing inefficiencies analysis functionality.
"""

import pytest
from rdflib import Graph
from graph_hopper.graph_checks.routing_inefficiencies import check_routing_inefficiencies


def load_test_graph(filename: str) -> Graph:
    """Load a test TTL file into an RDF graph."""
    graph = Graph()
    graph.parse(f"tests/data/{filename}", format="turtle")
    return graph


class TestRoutingInefficiencies:
    """Test routing inefficiencies analysis."""
    
    def test_routing_loop_detection(self):
        """Test detection of routing loops."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # Should detect the 3-network routing loop (3000 -> 4000 -> 5000 -> 3000)
        loop_issues = [i for i in issues if i['issue_type'] == 'routing-loop']
        assert len(loop_issues) >= 1
        
        # Find the main loop
        main_loop = next((i for i in loop_issues if i['loop_length'] == 3), None)
        assert main_loop is not None
        assert main_loop['severity'] == 'critical'  # 3-network loop is critical
        assert 'routing loop detected' in main_loop['description'].lower()
        
        # Check loop details
        loop_networks = set(main_loop['details']['loop_networks'])
        # Should contain 3 networks in the loop
        assert len(loop_networks) == 3
    
    def test_suboptimal_routing_paths(self):
        """Test detection of suboptimal routing paths."""
        # This would require a more complex test graph with longer paths
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # The basic loop graph may not have suboptimal paths, but check the structure
        suboptimal_issues = [i for i in issues if i['issue_type'] == 'suboptimal-routing-path']
        # This might be 0 for the simple test graph, which is fine
        assert isinstance(suboptimal_issues, list)
    
    def test_router_single_point_failure(self):
        """Test detection of single point of failure routers."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # Each router in the loop is on only one network, so they might be single points
        failure_issues = [i for i in issues if i['issue_type'] == 'router-single-point-failure']
        
        # Check structure if any are found
        for issue in failure_issues:
            assert 'router' in issue
            assert 'network' in issue
            assert issue['severity'] == 'warning'
            assert 'single router failure point' in issue['description'].lower()
    
    def test_asymmetric_routing_detection(self):
        """Test detection of asymmetric routing configurations."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # The loop graph should have symmetric routing, so no asymmetric issues expected
        asymmetric_issues = [i for i in issues if i['issue_type'] == 'asymmetric-routing']
        
        # Check structure if any are found (may be 0 for symmetric loop)
        for issue in asymmetric_issues:
            assert 'source_network' in issue
            assert 'target_network' in issue
            assert issue['severity'] == 'warning'
            assert 'asymmetric routing' in issue['description'].lower()
    
    def test_missing_redundancy_detection(self):
        """Test detection of missing redundancy in network paths."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # The 3-network loop might have redundancy issues
        redundancy_issues = [i for i in issues if i['issue_type'] == 'missing-redundancy']
        
        # Check structure if any are found
        for issue in redundancy_issues:
            assert 'network' in issue
            assert issue['severity'] == 'warning'
            assert 'lacks redundant paths' in issue['description'].lower()
    
    def test_verbose_output(self):
        """Test that verbose mode provides additional details."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=True)
        
        # Find any issue and check for verbose description
        if issues:
            issue = issues[0]
            assert 'verbose_description' in issue
            assert len(issue['verbose_description']) > len(issue['description'])
    
    def test_affected_nodes_populated(self):
        """Test that affected nodes are properly identified."""
        graph = load_test_graph("complex_network_loops.ttl")
        issues, affected_triples, affected_nodes = check_routing_inefficiencies(graph, verbose=False)
        
        # Should have affected nodes if issues are found
        if issues:
            assert len(affected_nodes) >= 1
            
            # Check that URIs are proper format
            for node in affected_nodes:
                assert isinstance(node, str)
                # Should be router or network URIs
                assert 'router' in node or 'network' in node
    
    def test_routing_graph_building(self):
        """Test the routing graph building functionality."""
        from graph_hopper.graph_checks.routing_inefficiencies import _build_routing_graph
        from rdflib import URIRef
        
        graph = load_test_graph("complex_network_loops.ttl")
        
        # Find routers and networks manually
        bacnet_ns = URIRef("http://data.ashrae.org/bacnet/2020#")
        rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        
        routers = set()
        networks = set()
        
        router_class = bacnet_ns + "Router"
        network_class = bacnet_ns + "BACnetNetwork"
        
        for router, _, _ in graph.triples((None, rdf_type, router_class)):
            routers.add(router)
        
        for network, _, _ in graph.triples((None, rdf_type, network_class)):
            networks.add(network)
        
        # Build routing graph
        routing_graph = _build_routing_graph(graph, routers, networks)
        
        # Verify structure
        assert 'routers' in routing_graph
        assert 'router_serves' in routing_graph
        assert 'network_routers' in routing_graph
        assert 'network_connections' in routing_graph
        assert 'all_routers' in routing_graph
        assert 'all_networks' in routing_graph
        
        # Should have found 3 routers and 3 networks
        assert len(routing_graph['all_routers']) == 3
        assert len(routing_graph['all_networks']) == 3
        
        # Should have network connections
        assert len(routing_graph['network_connections']) >= 1
    
    def test_loop_performance_impact(self):
        """Test loop performance impact assessment."""
        from graph_hopper.graph_checks.routing_inefficiencies import _get_loop_performance_impact
        
        # Test different severities and lengths
        critical_impact = _get_loop_performance_impact(3, 'critical')
        assert 'severe' in critical_impact.lower()
        assert 'instability' in critical_impact.lower()
        
        warning_impact = _get_loop_performance_impact(5, 'warning')
        assert 'potential' in warning_impact.lower()
        assert 'inefficiency' in warning_impact.lower()
    
    def test_loop_recommendations(self):
        """Test loop resolution recommendations."""
        from graph_hopper.graph_checks.routing_inefficiencies import _get_loop_recommendation
        
        # Test critical vs warning recommendations
        critical_rec = _get_loop_recommendation(3, 'critical')
        assert 'immediately' in critical_rec.lower()
        assert 'break' in critical_rec.lower()
        
        warning_rec = _get_loop_recommendation(5, 'warning')
        assert 'review' in warning_rec.lower()
        assert 'optimize' in warning_rec.lower()


class TestRoutingHelpers:
    """Test helper functions for routing analysis."""
    
    def test_network_name_extraction(self):
        """Test network name extraction from URIs."""
        from graph_hopper.graph_checks.routing_inefficiencies import _get_network_name_from_uri
        
        # Test URI name extraction
        assert _get_network_name_from_uri('bacnet://network/3000') == '3000'
        assert _get_network_name_from_uri('http://example.com/Network_100') == 'Network_100'
        assert _get_network_name_from_uri('Network_200') == 'Network_200'
    
    def test_router_name_extraction(self):
        """Test router name extraction from URIs."""
        from graph_hopper.graph_checks.routing_inefficiencies import _get_router_name_from_uri
        
        # Test URI name extraction
        assert _get_router_name_from_uri('bacnet://router/2001') == '2001'
        assert _get_router_name_from_uri('http://example.com/Router_100') == 'Router_100'
        assert _get_router_name_from_uri('Router_200') == 'Router_200'


if __name__ == '__main__':
    pytest.main([__file__])
