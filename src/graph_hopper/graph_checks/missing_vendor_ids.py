"""
Missing Vendor IDs Check - Phase 1.4

Detects devices without vendor identification or with invalid vendor ID formats.
Missing vendor IDs affect device management, troubleshooting, and interoperability.

BACnet Standard: Each device should have a vendor-id property that identifies
the manufacturer. Vendor IDs should be numeric and registered with ASHRAE.
"""

from typing import List, Tuple, Any, Dict
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_missing_vendor_ids(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for devices missing vendor IDs or with invalid vendor ID formats.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_triples, affected_nodes)
    """
    issues = []
    affected_nodes = []
    affected_triples = []
    
    # Find all devices and check for vendor IDs
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        # Get device properties
        device_name = None
        device_instance = None
        device_address = None
        vendor_id = None
        
        # Extract device name/label
        for _, _, label_value in graph.triples((device, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            device_name = str(label_value)
            break
        
        # Skip Grasshopper nodes - check both URI and label
        device_uri = str(device)
        if (device_name and "Grasshopper" in device_name) or "Grasshopper" in device_uri:
            continue
        
        # Extract device instance
        for _, _, instance_value in graph.triples((device, BACNET_NS['device-instance'], None)):
            device_instance = str(instance_value)
            break
            
        # Extract address
        for _, _, address_value in graph.triples((device, BACNET_NS['address'], None)):
            device_address = str(address_value)
            break
        
        # Extract vendor ID
        vendor_id = None
        vendor_id_numeric = None
        for _, _, vendor_value in graph.triples((device, BACNET_NS['vendor-id'], None)):
            vendor_id = str(vendor_value)
            
            # Extract numeric vendor ID from various formats
            if vendor_id.startswith('bacnet://vendor/'):
                # Handle URI format: bacnet://vendor/123
                try:
                    vendor_id_numeric = int(vendor_id.split('/')[-1])
                except (ValueError, IndexError):
                    vendor_id_numeric = None
            else:
                # Handle simple numeric format: "123"
                try:
                    vendor_id_numeric = int(vendor_id)
                except (ValueError, TypeError):
                    vendor_id_numeric = None
            break
            
        # Use defaults if not found
        final_device_name = device_name if device_name else f"Device {device_instance if device_instance else 'Unknown'}"
        final_device_instance = device_instance if device_instance else 'Unknown'
        final_device_address = device_address if device_address else 'Unknown'
        
        # Check if vendor ID is missing
        if not vendor_id:
            issue = {
                'issue_type': 'missing-vendor-ids',
                'severity': 'medium',
                'device': str(device),
                'label': final_device_name,
                'device_instance': final_device_instance,
                'address': final_device_address,
                'vendor_id': None,
                'description': f'Device {final_device_name} (instance {final_device_instance}) is missing vendor-id property'
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f'Device {final_device_name} (instance {final_device_instance}) at address {final_device_address} '
                    f'does not have a vendor-id property. BACnet devices should include vendor identification '
                    f'to assist with device management, troubleshooting, and interoperability. '
                    f'Vendor IDs should be numeric values registered with ASHRAE.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
            continue
        
        # Validate vendor ID format and value
        if vendor_id_numeric is None:
            # Could not parse a numeric vendor ID
            issue = {
                'issue_type': 'missing-vendor-ids',
                'severity': 'medium',
                'device': str(device),
                'label': final_device_name,
                'device_instance': final_device_instance,
                'address': final_device_address,
                'vendor_id': vendor_id,
                'description': f'Device {final_device_name} (instance {final_device_instance}) has invalid vendor-id format: "{vendor_id}" (must be numeric or bacnet://vendor/N format)'
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f'Device {final_device_name} (instance {final_device_instance}) at address {final_device_address} '
                    f'has an invalid vendor-id "{vendor_id}". BACnet vendor IDs must be positive integers '
                    f'registered with ASHRAE, either as simple numbers like "123" or URI format like "bacnet://vendor/123".'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
            continue
            
        # Check for invalid vendor ID values
        if vendor_id_numeric < 0:
            issue = {
                'issue_type': 'missing-vendor-ids',
                'severity': 'medium',
                'device': str(device),
                'label': final_device_name,
                'device_instance': final_device_instance,
                'address': final_device_address,
                'vendor_id': vendor_id,
                'description': f'Device {final_device_name} (instance {final_device_instance}) has invalid vendor-id: {vendor_id_numeric} (must be positive)'
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f'Device {final_device_name} (instance {final_device_instance}) at address {final_device_address} '
                    f'has an invalid vendor-id value "{vendor_id_numeric}". BACnet vendor IDs must be positive integers '
                    f'registered with ASHRAE. Negative values are not valid vendor identifiers.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
        elif vendor_id_numeric == 0:
            issue = {
                'issue_type': 'missing-vendor-ids',
                'severity': 'medium',
                'device': str(device),
                'label': final_device_name,
                'device_instance': final_device_instance,
                'address': final_device_address,
                'vendor_id': vendor_id,
                'description': f'Device {final_device_name} (instance {final_device_instance}) has invalid vendor-id: 0 (reserved value)'
            }
            
            if verbose:
                issue['verbose_description'] = (
                    f'Device {final_device_name} (instance {final_device_instance}) at address {final_device_address} '
                    f'has vendor-id "0" which is a reserved value. BACnet vendor IDs should be positive integers '
                    f'registered with ASHRAE. Vendor ID 0 is not assigned to any manufacturer.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
        # Note: We could add checks for known vendor ID ranges here if needed
        # For now, we accept any positive integer as potentially valid
    
    return issues, affected_triples, affected_nodes
