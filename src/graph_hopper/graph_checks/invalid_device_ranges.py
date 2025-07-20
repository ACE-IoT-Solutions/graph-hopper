"""
Invalid Device Ranges Check - Phase 1.2

Detects devices with instance IDs outside the valid BACnet range (0-4,194,303).
Invalid device IDs cause protocol errors and communication failures.

BACnet Standard: Device instance numbers must be in range 0 to 4,194,303 (0x3FFFFF)
"""

from typing import List, Tuple, Any, Dict
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_invalid_device_ranges(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node]]:
    """
    Check for devices with invalid instance ID ranges.
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_nodes)
    """
    issues = []
    affected_nodes = []
    
    # BACnet device instance range: 0 to 4,194,303 (0x3FFFFF)
    MIN_DEVICE_ID = 0
    MAX_DEVICE_ID = 4194303
    
    # Find all device instances using triple patterns
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        # Get device properties
        device_name = None
        device_instance = None
        device_address = None
        
        # Extract device name/label
        for _, _, label_value in graph.triples((device, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            device_name = str(label_value)
            break
        
        # Extract device instance
        for _, _, instance_value in graph.triples((device, BACNET_NS['device-instance'], None)):
            device_instance = str(instance_value)
            break
            
        # Extract address
        for _, _, address_value in graph.triples((device, BACNET_NS['address'], None)):
            device_address = str(address_value)
            break
            
        # Use defaults if not found
        if not device_name:
            device_name = f"Device {device_instance if device_instance else 'Unknown'}"
        if not device_address:
            device_address = "Unknown"
        
        # Skip devices without instance IDs
        if not device_instance:
            continue
            
        # Convert device instance to integer for validation
        try:
            instance_id = int(device_instance)
        except (ValueError, TypeError):
            # Non-numeric device instance
            issue = {
                'type': 'invalid-device-ranges',
                'severity': 'critical',
                'device': str(device),
                'label': device_name,
                'device_instance': device_instance,
                'address': device_address,
                'description': f'Device instance "{device_instance}" is not a valid number. Valid range: {MIN_DEVICE_ID}-{MAX_DEVICE_ID}'
            }
            
            if verbose:
                # Add detailed description for verbose output
                issue['verbose_description'] = (
                    f'Device {device_name} (instance {device_instance}) at address {device_address} '
                    f'has an invalid device instance "{device_instance}" which is not a valid number. '
                    f'BACnet device instances must be integers in range {MIN_DEVICE_ID}-{MAX_DEVICE_ID}.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
            continue
        
        # Check if device instance is within valid range
        if instance_id < MIN_DEVICE_ID or instance_id > MAX_DEVICE_ID:
            issue = {
                'type': 'invalid-device-ranges',
                'severity': 'critical',
                'device': str(device),
                'label': device_name,
                'device_instance': instance_id,
                'address': device_address,
                'description': f'Device instance {instance_id} is outside valid BACnet range ({MIN_DEVICE_ID}-{MAX_DEVICE_ID})'
            }
            
            if verbose:
                # Add detailed description for verbose output
                issue['verbose_description'] = (
                    f'Device {device_name} (instance {instance_id}) at address {device_address} '
                    f'has an invalid device instance {instance_id} which is outside the valid BACnet range. '
                    f'BACnet device instances must be in range {MIN_DEVICE_ID}-{MAX_DEVICE_ID}.'
                )
            
            issues.append(issue)
            affected_nodes.append(device)
    
    return issues, affected_nodes
