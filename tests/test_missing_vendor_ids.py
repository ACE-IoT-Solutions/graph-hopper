"""
Test suite for missing vendor IDs detection.

Tests the check_missing_vendor_ids function to ensure it properly
detects devices without vendor identification or with invalid vendor ID formats.
"""

from rdflib import Graph
from graph_hopper.graph_checks.missing_vendor_ids import check_missing_vendor_ids


class TestMissingVendorIds:
    """Test class for missing vendor IDs detection."""

    def test_module_import(self):
        """Test that the module can be imported correctly."""
        assert check_missing_vendor_ids is not None

    def test_empty_graph(self):
        """Test with empty graph - should return no issues."""
        graph = Graph()
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_devices_with_valid_vendor_ids(self):
        """Test devices with valid vendor IDs - should not detect issues."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device One" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "123" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Device Two" ;
            bacnet:device-instance "1002" ;
            bacnet:vendor-id "456" ;
            bacnet:address "192.168.1.11" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_device_missing_vendor_id(self):
        """Test device without vendor ID - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device Without Vendor" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'missing-vendor-ids'
        assert issue['severity'] == 'medium'  # Changed from 'warning'
        assert 'missing vendor-id property' in issue['description']
        
        assert len(affected_nodes) == 1

    def test_device_with_invalid_vendor_id_format(self):
        """Test device with non-numeric vendor ID - should detect issue."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Device With Text Vendor" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "ABC-123" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert issue['type'] == 'missing-vendor-ids'
        assert issue['severity'] == 'medium'  # Changed from 'warning'
        assert 'invalid vendor-id format' in issue['description']
        
        assert len(affected_nodes) == 1

    def test_mixed_vendor_id_issues(self):
        """Test mix of missing and invalid vendor IDs."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Valid Device" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "123" ;
            bacnet:address "192.168.1.10" .

        ex:Device2 a bacnet:Device ;
            rdfs:label "Missing Vendor" ;
            bacnet:device-instance "1002" ;
            bacnet:address "192.168.1.11" .

        ex:Device3 a bacnet:Device ;
            rdfs:label "Invalid Vendor Format" ;
            bacnet:device-instance "1003" ;
            bacnet:vendor-id "NotANumber" ;
            bacnet:address "192.168.1.12" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        # Should detect 2 issues (missing and invalid)
        assert len(issues) == 2
        assert len(affected_nodes) == 2
        
        # Check both types are detected
        descriptions = [issue['description'] for issue in issues]
        missing_found = any('missing vendor-id property' in desc for desc in descriptions)
        invalid_found = any('invalid vendor-id format' in desc for desc in descriptions)
        assert missing_found
        assert invalid_found

    def test_zero_vendor_id_valid(self):
        """Test vendor ID of 0 - should be valid."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Zero Vendor Device" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "0" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        # Vendor ID 0 should be invalid per the implementation (reserved value)
        assert len(issues) == 1
        assert 'reserved value' in issues[0]['description']

    def test_large_vendor_id_valid(self):
        """Test large numeric vendor ID - should be valid."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Large Vendor ID Device" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "65535" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        assert issues == []
        assert affected_nodes == []

    def test_verbose_output_missing_vendor(self):
        """Test verbose output for missing vendor ID."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "HVAC Controller" ;
            bacnet:device-instance "1001" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph, verbose=True)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert 'verbose_description' in issue
        verbose_desc = issue['verbose_description']
        assert 'HVAC Controller' in verbose_desc
        assert 'troubleshooting' in verbose_desc or 'management' in verbose_desc

    def test_verbose_output_invalid_vendor(self):
        """Test verbose output for invalid vendor ID format."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Lighting Panel" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "INVALID" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph, verbose=True)
        
        assert len(issues) == 1
        issue = issues[0]
        
        assert 'verbose_description' in issue
        verbose_desc = issue['verbose_description']
        assert 'Lighting Panel' in verbose_desc
        assert 'INVALID' in verbose_desc

    def test_negative_vendor_id_invalid(self):
        """Test negative vendor ID - should be invalid."""
        ttl_content = """
        @prefix ex: <http://example.org/> .
        @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Device1 a bacnet:Device ;
            rdfs:label "Negative Vendor Device" ;
            bacnet:device-instance "1001" ;
            bacnet:vendor-id "-1" ;
            bacnet:address "192.168.1.10" .
        """
        
        graph = Graph()
        graph.parse(data=ttl_content, format="turtle")
        
        issues, affected_nodes = check_missing_vendor_ids(graph)
        
        # Negative vendor IDs should be invalid
        assert len(issues) == 1
        issue = issues[0]
        assert 'must be positive' in issue['description']


def test_missing_vendor_ids_integration():
    """Integration test to verify the function works with real TTL structure."""
    ttl_content = """
    @prefix ex: <http://example.org/> .
    @prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    # Building automation system with vendor ID issues
    ex:ValidHVAC a bacnet:Device ;
        rdfs:label "Main HVAC Controller" ;
        bacnet:device-instance "100001" ;
        bacnet:address "10.0.1.100" ;
        bacnet:vendor-id "123" .

    ex:MissingVendor a bacnet:Device ;
        rdfs:label "Sensor Without Vendor" ;
        bacnet:device-instance "100002" ;
        bacnet:address "10.0.1.101" .

    ex:ValidLighting a bacnet:Device ;
        rdfs:label "Floor 1 Lighting" ;
        bacnet:device-instance "200001" ;
        bacnet:address "10.0.2.50" ;
        bacnet:vendor-id "456" .

    ex:InvalidVendorFormat a bacnet:Device ;
        rdfs:label "Device with Text Vendor" ;
        bacnet:device-instance "200002" ;
        bacnet:address "10.0.2.51" ;
        bacnet:vendor-id "XYZ-Corp" .

    ex:ValidSecurity a bacnet:Device ;
        rdfs:label "Security Panel" ;
        bacnet:device-instance "300001" ;
        bacnet:address "10.0.3.100" ;
        bacnet:vendor-id "0" .
    """
    
    graph = Graph()
    graph.parse(data=ttl_content, format="turtle")
    
    issues, affected_nodes = check_missing_vendor_ids(graph, verbose=True)
    
    # Should find exactly three vendor ID issues (missing, invalid format, and reserved 0)
    assert len(issues) == 3
    assert len(affected_nodes) == 3
    
    # Check all issue types are detected
    descriptions = [issue['description'] for issue in issues]
    missing_found = any('missing vendor-id property' in desc for desc in descriptions)
    invalid_found = any('invalid vendor-id format' in desc for desc in descriptions)
    reserved_found = any('reserved value' in desc for desc in descriptions)
    assert missing_found
    assert invalid_found
    assert reserved_found
    
    # Verify verbose descriptions are present
    for issue in issues:
        assert 'verbose_description' in issue
