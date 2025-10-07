"""
Test suite for invalid device ranges detection.

Tests the check_invalid_device_ranges function to ensure it properly
detects devices with instance IDs outside the valid BACnet range (0-4194303).
"""

from rdflib import Graph
from graph_hopper.graph_checks.invalid_device_ranges import check_invalid_device_ranges


class TestInvalidDeviceRanges:
    """Test class for invalid device ranges detection."""

    def test_module_import(self):
        """Test that the module can be imported correctly."""
        assert check_invalid_device_ranges is not None

    def test_empty_graph(self):
        """Test with empty graph - should return no issues."""
        graph = Graph()
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_valid_device_ranges(self):
        """Test devices with valid instance IDs - should not detect issues."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "0" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1000" ;
            bacnet:address "192.168.1.11" .

        ex:Device3 a bacnet:Device ;
            rdfs:label "Device Max" ;
            bacnet:device-instance "4194303" ;
            bacnet:address "192.168.1.12" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_negative_device_id(self):
        """Test device with negative instance ID - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Invalid Device" ;
            bacnet:device-instance "-1" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'invalid-device-ranges'
        assert issue['severity'] == 'critical'
        assert issue['device_instance'] == -1  # Integer, not string
        assert issue['label'] == 'Invalid Device'
        assert 'outside valid BACnet range' in issue['description']
        
        assert len(affected_nodes) == 1

    def test_device_id_too_large(self):
        """Test device with instance ID above maximum - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Oversized Device" ;
            bacnet:device-instance "4194304" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'invalid-device-ranges'
        assert issue['severity'] == 'critical'
        assert issue['device_instance'] == 4194304  # Integer, not string
        assert issue['label'] == 'Oversized Device'
        assert 'outside valid BACnet range' in issue['description']
        
        assert len(affected_nodes) == 1

    def test_multiple_invalid_ranges(self):
        """Test multiple devices with invalid ranges."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Negative Device" ;
            bacnet:device-instance "-5" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Valid Device" ;
            bacnet:device-instance "1000" ;
            bacnet:address "192.168.1.11" .

        ex:Device3 a bacnet:Device ;
            rdfs:label "Too Large Device" ;
            bacnet:device-instance "5000000" ;
            bacnet:address "192.168.1.12" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 2  # Only invalid devices
        assert len(affected_nodes) == 2
        
        # Check both issue types are detected
        device_instances = [issue['device_instance'] for issue in issues]
        assert -5 in device_instances  # Integer, not string
        assert 5000000 in device_instances

    def test_boundary_values(self):
        """Test boundary values (0 and 4194303) - should be valid."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:MinDevice a bacnet:Device ;
            rdfs:label "Minimum Device" ;
            bacnet:device-instance "0" ;
            bacnet:address "192.168.1.10" .

        ex:MaxDevice a bacnet:Device ;
            rdfs:label "Maximum Device" ;
            bacnet:device-instance "4194303" ;
            bacnet:address "192.168.1.11" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_non_numeric_device_instance(self):
        """Test device with non-numeric instance ID - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Text Device" ;
            bacnet:device-instance "abc123" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'invalid-device-ranges'
        assert issue['severity'] == 'critical'
        assert issue['device_instance'] == 'abc123'  # String for non-numeric
        assert 'not a valid number' in issue['description']

    def test_device_without_instance_ignored(self):
        """Test that devices without instance IDs are ignored."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "No Instance Device" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Valid Device" ;
            bacnet:device-instance "1000" ;
            bacnet:address "192.168.1.11" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        # Only devices with instances are checked
        assert issues == []
        assert affected_nodes == []

    def test_verbose_output(self):
        """Test verbose output includes detailed descriptions."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "HVAC Controller" ;
            bacnet:device-instance "-10" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph, verbose=True)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert 'verbose_description' in issue
        verbose_desc = issue['verbose_description']
        assert 'BACnet device instances must be' in verbose_desc
        assert 'HVAC Controller' in verbose_desc
        assert 'outside the valid BACnet range' in verbose_desc

    def test_edge_case_just_outside_bounds(self):
        """Test values just outside valid bounds."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Just Below" ;
            bacnet:device-instance "-1" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Just Above" ;
            bacnet:device-instance "4194304" ;
            bacnet:address "192.168.1.11" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 2
        assert len(affected_nodes) == 2
        
        # Verify both boundary violations are caught
        instances = [issue['device_instance'] for issue in issues]
        assert -1 in instances  # Integer, not string
        assert 4194304 in instances

    def test_float_device_instance(self):
        """Test device with float instance ID - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Float Device" ;
            bacnet:device-instance "123.456" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_invalid_device_ranges(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'invalid-device-ranges'
        assert issue['device_instance'] == '123.456'
        # Should be treated as invalid format since BACnet requires integers


def test_invalid_device_ranges_integration():
    """Integration test to verify the function works with real TTL structure."""
    ttl_content = """
    @prefix ex: <http://example.org/> .
    @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    # Building automation system with various device ranges
    ex:ValidHVAC a bacnet:Device ;
        rdfs:label "Main HVAC Controller" ;
        bacnet:device-instance "100001" ;
        bacnet:address "10.0.1.100" ;
        bacnet:vendor-id "123" .

    ex:InvalidNegative a bacnet:Device ;
        rdfs:label "Misconfigured Sensor" ;
        bacnet:device-instance "-1" ;
        bacnet:address "10.0.1.101" ;
        bacnet:vendor-id "456" .

    ex:ValidLighting a bacnet:Device ;
        rdfs:label "Floor 1 Lighting" ;
        bacnet:device-instance "200001" ;
        bacnet:address "10.0.2.50" ;
        bacnet:vendor-id "789" .

    ex:InvalidTooLarge a bacnet:Device ;
        rdfs:label "Oversized Device ID" ;
        bacnet:device-instance "99999999" ;
        bacnet:address "10.0.2.51" ;
        bacnet:vendor-id "999" .

    ex:ValidMax a bacnet:Device ;
        rdfs:label "Maximum Valid Device" ;
        bacnet:device-instance "4194303" ;
        bacnet:address "10.0.3.100" ;
        bacnet:vendor-id "111" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_content, format="turtle")
    
    issues, affected_nodes = check_invalid_device_ranges(graph, verbose=True)
    
    # Should find exactly two invalid devices
    assert len(issues) == 2
    assert len(affected_nodes) == 2
    
    # Check the specific invalid instances are detected
    invalid_instances = [issue['device_instance'] for issue in issues]
    assert -1 in invalid_instances  # Integer, not string
    assert 99999999 in invalid_instances
    
    # Verify verbose descriptions are present
    for issue in issues:
        assert 'verbose_description' in issue
        assert 'BACnet device instances must be' in issue['verbose_description']
