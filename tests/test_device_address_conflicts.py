"""
Test suite for device address conflicts detection.

Tests the check_device_address_conflicts function to ensure it properly
detects devices with the same address on the same network/subnet.
"""

from rdflib import Graph
from graph_hopper.graph_checks.device_address_conflicts import check_device_address_conflicts


class TestDeviceAddressConflicts:
    """Test class for device address conflicts detection."""

    def test_module_import(self):
        """Test that the module can be imported correctly."""
        assert check_device_address_conflicts is not None

    def test_empty_graph(self):
        """Test with empty graph - should return no issues."""
        graph = Graph()
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_single_device_no_conflicts(self):
        """Test with single device - should not detect any conflicts."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_multiple_devices_different_addresses(self):
        """Test multiple devices with different addresses - no conflicts."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.11" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_address_conflict_same_network(self):
        """Test devices with same address on same network - should detect conflict."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['issue_type'] == 'device-address-conflicts'
        assert issue['severity'] == 'critical'
        assert issue['network_type'] == 'network'
        assert issue['address'] == '192.168.1.10'
        assert issue['device_count'] == 2
        assert len(issue['devices']) == 2
        
        # Check device information
        device_names = [dev['device_name'] for dev in issue['devices']]
        assert 'Device One' in device_names
        assert 'Device Two' in device_names
        
        # Check affected nodes
        assert len(affected_nodes) == 2

    def test_address_conflict_same_subnet(self):
        """Test devices with same address on same subnet - should detect conflict."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-subnet ex:Subnet1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-subnet ex:Subnet1 .

        ex:Subnet1 a bacnet:Subnet .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['issue_type'] == 'device-address-conflicts'
        assert issue['severity'] == 'critical'
        assert issue['network_type'] == 'subnet'
        assert issue['address'] == '192.168.1.10'
        assert issue['device_count'] == 2
        
        # Check affected nodes
        assert len(affected_nodes) == 2

    def test_same_address_different_networks_no_conflict(self):
        """Test devices with same address on different networks - no conflict."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network2 .

        ex:Network1 a bacnet:Network .
        ex:Network2 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        # Should be no conflicts since devices are on different networks
        assert issues == []
        assert affected_nodes == []

    def test_three_devices_same_address_conflict(self):
        """Test three devices with same address - should detect conflict."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device3 a bacnet:Device ;
            rdfs:label "Device Three" ;
            bacnet:device-instance "1003" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['device_count'] == 3
        assert len(issue['devices']) == 3
        assert len(affected_nodes) == 3

    def test_verbose_output(self):
        """Test verbose output includes detailed descriptions."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "HVAC Controller" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Lighting Panel" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph, verbose=True)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert 'verbose_description' in issue
        verbose_desc = issue['verbose_description']
        assert 'Address conflict detected' in verbose_desc
        assert 'HVAC Controller' in verbose_desc
        assert 'Lighting Panel' in verbose_desc
        assert 'communication failures' in verbose_desc

    def test_devices_without_addresses_ignored(self):
        """Test that devices without addresses are ignored."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Network1 a bacnet:Network .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        # No conflicts because Device1 has no address
        assert issues == []
        assert affected_nodes == []

    def test_mixed_network_and_subnet_conflicts(self):
        """Test complex scenario with both network and subnet conflicts."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        # Network conflict
        ex:Device1 a bacnet:Device ;
            rdfs:label "Network Device 1" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Network Device 2" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.10" ;
            bacnet:device-on-network ex:Network1 .

        # Subnet conflict
        ex:Device3 a bacnet:Device ;
            rdfs:label "Subnet Device 1" ;
            bacnet:device-instance "1003" ;
            bacnet:address "192.168.2.20" ;
            bacnet:device-on-subnet ex:Subnet1 .

        ex:Device4 a bacnet:Device ;
            rdfs:label "Subnet Device 2" ;
            bacnet:device-instance "1004" ;
            bacnet:address "192.168.2.20" ;
            bacnet:device-on-subnet ex:Subnet1 .

        ex:Network1 a bacnet:Network .
        ex:Subnet1 a bacnet:Subnet .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_triples, affected_nodes = check_device_address_conflicts(graph)
        
        # Should detect both conflicts
        assert len(issues) == 2
        assert len(affected_nodes) == 4
        
        # Check both conflict types are present
        network_types = [issue['network_type'] for issue in issues]
        assert 'network' in network_types
        assert 'subnet' in network_types


def test_device_address_conflicts_integration():
    """Integration test to verify the function works with real TTL structure."""
    ttl_content = """
    @prefix ex: <http://example.org/> .
    @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    # Building automation system with address conflicts
    ex:HVACController a bacnet:Device ;
        rdfs:label "Main HVAC Controller" ;
        bacnet:device-instance "100001" ;
        bacnet:address "10.0.1.100" ;
        bacnet:device-on-network ex:HVACNetwork .

    ex:BackupController a bacnet:Device ;
        rdfs:label "Backup HVAC Controller" ;
        bacnet:device-instance "100002" ;
        bacnet:address "10.0.1.100" ;  # Conflict!
        bacnet:device-on-network ex:HVACNetwork .

    ex:LightingPanel a bacnet:Device ;
        rdfs:label "Floor 1 Lighting" ;
        bacnet:device-instance "200001" ;
        bacnet:address "10.0.2.50" ;
        bacnet:device-on-subnet ex:LightingSubnet .

    ex:HVACNetwork a bacnet:Network .
    ex:LightingSubnet a bacnet:Subnet .
    """
    
    graph = Graph()
    graph.parse(data=ttl_content, format="turtle")
    
    issues, affected_triples, affected_nodes = check_device_address_conflicts(graph, verbose=True)
    
    # Should find exactly one conflict
    assert len(issues) == 1
    issue = issues[0]
    
    assert issue['issue_type'] == 'device-address-conflicts'
    assert issue['severity'] == 'critical'
    assert issue['address'] == '10.0.1.100'
    assert issue['device_count'] == 2
    
    # Verify device information
    device_names = [dev['device_name'] for dev in issue['devices']]
    assert 'Main HVAC Controller' in device_names
    assert 'Backup HVAC Controller' in device_names
    
    # Verify verbose description
    assert 'verbose_description' in issue
    assert 'Main HVAC Controller' in issue['verbose_description']
    assert 'Backup HVAC Controller' in issue['verbose_description']
