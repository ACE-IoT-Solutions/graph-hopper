"""
Tests for missing properties check functionality.
"""

import pytest
from rdflib import Graph, URIRef, Literal
from graph_hopper.graph_checks.missing_properties import check_missing_properties
from graph_hopper.graph_checks.utils import BACNET_NS


def test_check_missing_properties_all_present():
    """Test device with all essential properties present."""
    graph = Graph()
    
    # Device with all essential properties
    device = URIRef("bacnet://device/1234")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Add device type
    graph.add((device, rdf_type, device_type))
    
    # Add device label
    graph.add((device, rdfs_label, Literal("Test Device")))
    
    # Add all essential properties
    graph.add((device, BACNET_NS['device-instance'], Literal("1234")))
    graph.add((device, BACNET_NS['address'], Literal("192.168.1.100")))
    graph.add((device, BACNET_NS['vendor-id'], Literal("bacnet://vendor/8")))
    graph.add((device, BACNET_NS['model-name'], Literal("TestModel")))
    graph.add((device, BACNET_NS['device-name'], Literal("Test Device Name")))
    graph.add((device, BACNET_NS['firmware-revision'], Literal("1.0.0")))
    graph.add((device, BACNET_NS['device-on-network'], URIRef("bacnet://network/1")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    # Should have no issues since all properties are present
    assert len(issues) == 0
    assert len(affected_nodes) == 0


def test_check_missing_properties_critical_missing():
    """Test device missing critical properties."""
    graph = Graph()
    
    # Device missing critical properties
    device = URIRef("bacnet://device/1234")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Add device type
    graph.add((device, rdf_type, device_type))
    
    # Add device label
    graph.add((device, rdfs_label, Literal("Test Device")))
    
    # Only add device-instance, missing address and vendor-id (critical)
    graph.add((device, BACNET_NS['device-instance'], Literal("1234")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    assert len(issues) == 1
    assert len(affected_nodes) == 1
    
    issue = issues[0]
    assert issue['issue_type'] == 'missing-properties'
    assert issue['severity'] == 'critical'  # Missing critical properties
    assert issue['device_name'] == 'Test Device'
    assert issue['device_instance'] == '1234'
    assert issue['missing_count'] == 6  # Missing 6 out of 7 essential properties
    assert 'address' in issue['missing_properties']
    assert 'vendor-id' in issue['missing_properties']
    assert 'device-instance' in issue['present_properties']


def test_check_missing_properties_major_missing():
    """Test device with major missing properties."""
    graph = Graph()
    
    device = URIRef("bacnet://device/5678")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Add device type and label
    graph.add((device, rdf_type, device_type))
    graph.add((device, rdfs_label, Literal("Test Device 2")))
    
    # Add only critical properties (3) - missing 4 others = major
    graph.add((device, BACNET_NS['device-instance'], Literal("5678")))
    graph.add((device, BACNET_NS['address'], Literal("192.168.1.101")))
    graph.add((device, BACNET_NS['vendor-id'], Literal("bacnet://vendor/10")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    assert len(issues) == 1
    issue = issues[0]
    assert issue['severity'] == 'major'  # Missing 4 properties (>=4 threshold met)
    assert issue['missing_count'] == 4
    assert len(issue['present_properties']) == 3


def test_check_missing_properties_warning():
    """Test device with warning level missing properties."""
    graph = Graph()
    
    device = URIRef("bacnet://device/9999")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Add device type and label
    graph.add((device, rdf_type, device_type))
    graph.add((device, rdfs_label, Literal("Test Device 3")))
    
    # Add 5 properties, missing 2 = warning level
    graph.add((device, BACNET_NS['device-instance'], Literal("9999")))
    graph.add((device, BACNET_NS['address'], Literal("192.168.1.102")))
    graph.add((device, BACNET_NS['vendor-id'], Literal("bacnet://vendor/15")))
    graph.add((device, BACNET_NS['model-name'], Literal("TestModel")))
    graph.add((device, BACNET_NS['device-name'], Literal("Test Device Name")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    assert len(issues) == 1
    issue = issues[0]
    assert issue['severity'] == 'warning'  # Missing exactly 2 properties
    assert issue['missing_count'] == 2
    assert len(issue['present_properties']) == 5


def test_check_missing_properties_grasshopper_ignored():
    """Test that Grasshopper devices are ignored."""
    graph = Graph()
    
    # Regular device
    device1 = URIRef("bacnet://device/1234")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    graph.add((device1, rdf_type, device_type))
    graph.add((device1, rdfs_label, Literal("Regular Device")))
    # Only add device-instance (missing 6 properties)
    graph.add((device1, BACNET_NS['device-instance'], Literal("1234")))
    
    # Grasshopper device (should be ignored)
    device2 = URIRef("bacnet://device/grasshopper")
    graph.add((device2, rdf_type, device_type))
    graph.add((device2, rdfs_label, Literal("Grasshopper Device")))
    graph.add((device2, BACNET_NS['device-instance'], Literal("5555")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    # Should only find issues with regular device, not Grasshopper
    assert len(issues) == 1
    assert issues[0]['device_name'] == 'Regular Device'


def test_check_missing_properties_verbose():
    """Test verbose output includes additional details."""
    graph = Graph()
    
    device = URIRef("bacnet://device/1234")
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    rdfs_label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
    
    # Add device type and label
    graph.add((device, rdf_type, device_type))
    graph.add((device, rdfs_label, Literal("Test Device")))
    
    # Add only critical properties
    graph.add((device, BACNET_NS['device-instance'], Literal("1234")))
    graph.add((device, BACNET_NS['address'], Literal("192.168.1.100")))
    graph.add((device, BACNET_NS['vendor-id'], Literal("bacnet://vendor/8")))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph, verbose=True)
    
    assert len(issues) == 1
    issue = issues[0]
    
    # Check verbose fields are present
    assert 'verbose_description' in issue
    assert 'all_properties' in issue
    assert len(issue['all_properties']) > 0
    
    # Should contain type, label, and the 3 properties we added
    assert len(issue['all_properties']) >= 5  # type, label, + 3 BACnet properties


def test_check_missing_properties_no_devices():
    """Test with graph containing no devices."""
    graph = Graph()
    
    # Add some non-device entities
    router = URIRef("bacnet://router/1")
    router_type = BACNET_NS['Router']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    graph.add((router, rdf_type, router_type))
    
    issues, affected_triples, affected_nodes = check_missing_properties(graph)
    
    assert len(issues) == 0
    assert len(affected_nodes) == 0


if __name__ == '__main__':
    pytest.main([__file__])