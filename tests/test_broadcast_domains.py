"""
Tests for broadcast domain analysis functionality.
"""

import pytest
from rdflib import Graph
from graph_hopper.graph_checks.broadcast_domains import check_broadcast_domains


def load_test_graph(filename: str) -> Graph:
    """Load a test TTL file into an RDF graph."""
    graph = Graph()
    graph.parse(f"tests/data/{filename}", format="turtle")
    return graph


class TestBroadcastDomains:
    """Test broadcast domain analysis."""
    
    def test_large_broadcast_domain_warning(self):
        """Test detection of broadcast domains that trigger warnings."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Should detect warning for Network 100 (7 subnets > 5 warning threshold)
        warning_issues = [i for i in issues if i['issue_type'] == 'broadcast-domain-warning']
        assert len(warning_issues) >= 1
        
        # Find the Network 100 warning
        network_100_warning = next((i for i in warning_issues if 'Network_100' in i['network']), None)
        assert network_100_warning is not None
        assert network_100_warning['severity'] == 'warning'
        assert network_100_warning['subnet_count'] == 7
        assert 'Large broadcast domain' in network_100_warning['description']
    
    def test_critical_broadcast_domain(self):
        """Test detection of critically large broadcast domains."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Should detect critical issue for Network 200 (12 subnets > 10 critical threshold)
        critical_issues = [i for i in issues if i['issue_type'] == 'broadcast-domain-critical']
        assert len(critical_issues) >= 1
        
        # Find the Network 200 critical issue
        network_200_critical = next((i for i in critical_issues if 'Network_200' in i['network']), None)
        assert network_200_critical is not None
        assert network_200_critical['severity'] == 'critical'
        assert network_200_critical['subnet_count'] == 12
        assert 'Large broadcast domain' in network_200_critical['description']
    
    def test_missing_bbmd_coverage(self):
        """Test detection of domains needing BBMD coverage."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Should detect missing BBMD for Networks 100 and 200 (complex domains without BBMD)
        bbmd_issues = [i for i in issues if i['issue_type'] == 'missing-bbmd-coverage']
        assert len(bbmd_issues) >= 2
        
        # Check Network 100 needs BBMD
        network_100_bbmd = next((i for i in bbmd_issues if 'Network_100' in i['network']), None)
        assert network_100_bbmd is not None
        assert 'Missing BBMD coverage' in network_100_bbmd['description']
        
        # Check Network 200 needs BBMD  
        network_200_bbmd = next((i for i in bbmd_issues if 'Network_200' in i['network']), None)
        assert network_200_bbmd is not None
    
    def test_no_bbmd_warning_when_present(self):
        """Test that networks with BBMD don't trigger missing BBMD warnings."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Network 300 has BBMD, so should not trigger missing BBMD warning
        bbmd_issues = [i for i in issues if i['issue_type'] == 'missing-bbmd-coverage']
        network_300_bbmd = next((i for i in bbmd_issues if 'Network_300' in i['network']), None)
        assert network_300_bbmd is None  # Should not be flagged
    
    def test_broadcast_domain_overlap(self):
        """Test detection of overlapping broadcast domains."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Should detect overlap between Network 100 and Network 400 (both use 192.168.1.0)
        overlap_issues = [i for i in issues if i['issue_type'] == 'broadcast-domain-overlap']
        assert len(overlap_issues) >= 1
        
        # Check the overlap details
        overlap_issue = overlap_issues[0]
        assert '192.168.1.0/24' in overlap_issue['ip_range']
        assert overlap_issue['domain_count'] == 2
        assert 'Network_100' in overlap_issue['overlapping_domains']
        assert 'Network_400' in overlap_issue['overlapping_domains']
    
    def test_small_networks_not_flagged(self):
        """Test that small networks don't trigger broadcast domain warnings."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Network 500 (MSTP with 2 devices) should not trigger any warnings
        network_500_issues = [i for i in issues if 'Network_500' in i.get('network', '')]
        assert len(network_500_issues) == 0
    
    def test_verbose_output(self):
        """Test that verbose mode provides additional details."""
        graph = load_test_graph("broadcast_domain_test.ttl") 
        issues, affected_nodes = check_broadcast_domains(graph, verbose=True)
        
        # Find a warning issue and check for verbose description
        warning_issues = [i for i in issues if i['issue_type'] == 'broadcast-domain-warning']
        assert len(warning_issues) >= 1
        
        warning_issue = warning_issues[0]
        assert 'verbose_description' in warning_issue
        assert len(warning_issue['verbose_description']) > len(warning_issue['description'])
        assert 'broadcast traffic' in warning_issue['verbose_description'].lower()
    
    def test_affected_nodes_populated(self):
        """Test that affected nodes are properly identified."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Should have affected nodes for the networks with issues
        assert len(affected_nodes) >= 2
        
        # Check that network URIs are in affected nodes
        affected_node_strs = [str(node) for node in affected_nodes]
        assert any('Network_100' in node for node in affected_node_strs)
        assert any('Network_200' in node for node in affected_node_strs)
    
    def test_ip_range_detection(self):
        """Test IP range detection and classification."""
        graph = load_test_graph("broadcast_domain_test.ttl")
        issues, affected_nodes = check_broadcast_domains(graph, verbose=False)
        
        # Find an issue with IP range details
        domain_issues = [i for i in issues if i['issue_type'] in ['broadcast-domain-warning', 'broadcast-domain-critical']]
        assert len(domain_issues) >= 1
        
        # Check that IP ranges are detected
        for issue in domain_issues:
            details = issue.get('details', {})
            ip_ranges = details.get('ip_ranges', [])
            if ip_ranges:  # Some networks might not have IP addresses
                assert isinstance(ip_ranges, list)
                # Should be in CIDR format
                assert any('/' in ip_range for ip_range in ip_ranges)


class TestBroadcastDomainHelpers:
    """Test helper functions for broadcast domain analysis."""
    
    def test_broadcast_scope_classification(self):
        """Test broadcast scope classification logic."""
        from graph_hopper.graph_checks.broadcast_domains import _determine_broadcast_scope
        
        # Test different scope scenarios
        assert _determine_broadcast_scope(set()) == 'local'
        assert _determine_broadcast_scope({'192.168.1.0/24'}) == 'subnet'
        assert _determine_broadcast_scope({'192.168.1.0/24', '192.168.2.0/24'}) == 'moderate'
        assert _determine_broadcast_scope({'192.168.1.0/24', '192.168.2.0/24', '192.168.3.0/24', '192.168.4.0/24'}) == 'wide'
    
    def test_ip_range_extraction(self):
        """Test IP range extraction from addresses."""
        from graph_hopper.graph_checks.broadcast_domains import _extract_ip_ranges
        
        # Test various address formats
        addresses = [
            '192.168.1.10:47808',
            '192.168.1.11',
            '192.168.2.10:47808',
            '10.0.1.5'
        ]
        
        ranges = _extract_ip_ranges(addresses)
        assert '192.168.1.0/24' in ranges
        assert '192.168.2.0/24' in ranges
        assert '10.0.1.0/24' in ranges
        assert len(ranges) == 3
    
    def test_network_name_extraction(self):
        """Test network name extraction from URIs."""
        from graph_hopper.graph_checks.broadcast_domains import _get_network_name_from_uri
        
        # Test URI name extraction
        assert _get_network_name_from_uri('http://example.com/Network_100') == 'Network_100'
        assert _get_network_name_from_uri('Network_200') == 'Network_200'
        assert _get_network_name_from_uri('') == ''


if __name__ == '__main__':
    pytest.main([__file__])
