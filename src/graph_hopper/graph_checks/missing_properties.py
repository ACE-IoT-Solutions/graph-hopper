"""
Missing Properties Check - Phase 1.5

Detects devices that lack essential BACnet properties beyond basic identification.
Devices without sufficient properties may indicate configuration issues or incomplete
device discovery.

Based on actual property usage in generated graphs, this check verifies presence of
properties that are consistently included for properly discovered devices.
"""

from typing import List, Tuple, Any, Dict
from rdflib import Graph, URIRef
import rdflib.term
from .utils import BACNET_NS


def check_missing_properties(graph: Graph, verbose: bool = False) -> Tuple[List[Dict[str, Any]], List[rdflib.term.Node], List[rdflib.term.Node]]:
    """
    Check for devices missing essential BACnet properties.
    
    A device with missing properties is defined as a device that:
    - Has type ns1:Device (not Router, BBMD, etc.)
    - Has fewer than expected essential properties or missing critical ones
    
    Essential properties checked (based on actual graph generation):
    - device-instance (object identifier)
    - address (network address) 
    - vendor-id (vendor identification)
    - model-name (device model)
    - device-name (device name/label)
    - firmware-revision (firmware version)
    - device-on-network (network connectivity)
    
    Args:
        graph: RDF graph to analyze
        verbose: Whether to include detailed information
    
    Returns:
        Tuple of (issues_list, affected_triples, affected_nodes)
    """
    issues = []
    affected_nodes = []
    affected_triples = []  # Not used for this check but needed for consistency
    
    # Find all devices
    device_type = BACNET_NS['Device']
    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    
    # Define essential properties to check for (based on actual graph data)
    essential_properties = [
        'device-instance',     # object identifier
        'address',            # network address
        'vendor-id',          # vendor identification  
        'model-name',         # device model
        'device-name',        # device name/label
        'firmware-revision',  # firmware version
        'device-on-network'   # network connectivity
    ]
    
    # Define critical properties (must have at least these)
    critical_properties = [
        'device-instance',
        'address',
        'vendor-id'
    ]
    
    for device, _, _ in graph.triples((None, rdf_type, device_type)):
        # Get device properties
        device_name = None
        device_instance = None
        device_address = None
        
        # Extract device name/label
        for _, _, label_value in graph.triples((device, URIRef("http://www.w3.org/2000/01/rdf-schema#label"), None)):
            device_name = str(label_value)
            break
        
        if not device_name:
            device_name = str(device)
        
        # Skip Grasshopper nodes - check both URI and label
        device_uri = str(device)
        if (device_name and "Grasshopper" in device_name) or "Grasshopper" in device_uri:
            continue
        
        # Extract device instance
        for _, _, instance_value in graph.triples((device, BACNET_NS['device-instance'], None)):
            device_instance = str(instance_value)
            break
            
        if not device_instance:
            device_instance = "unknown"
            
        # Extract address
        for _, _, address_value in graph.triples((device, BACNET_NS['address'], None)):
            device_address = str(address_value)
            break
            
        if not device_address:
            device_address = "unknown"
        
        # Count which essential properties this device has
        present_properties = []
        missing_properties = []
        missing_critical = []
        
        for prop in essential_properties:
            prop_uri = BACNET_NS[prop]
            has_property = bool(list(graph.triples((device, prop_uri, None))))
            
            if has_property:
                present_properties.append(prop)
            else:
                missing_properties.append(prop)
                if prop in critical_properties:
                    missing_critical.append(prop)
        
        # Determine severity based on missing properties  
        severity = 'info'
        total_missing = len(missing_properties)
        
        if missing_critical:
            severity = 'critical'
        elif total_missing >= 4:  # Missing most properties (4+ out of 7)
            severity = 'major'
        elif total_missing >= 2:  # Missing several properties  
            severity = 'warning'
        elif total_missing > 0:   # Missing some properties
            severity = 'info'
        else:
            continue  # Device has all properties, no issue
        
        # Only report devices that are missing properties
        if missing_properties:
            issue = {
                'issue_type': 'missing-properties',
                'severity': severity,
                'device': str(device),
                'device_name': device_name,
                'device_instance': device_instance,
                'address': device_address,
                'missing_count': total_missing,
                'total_essential': len(essential_properties),
                'missing_properties': missing_properties,
                'present_properties': present_properties,
                'description': f'Device {device_name} (instance {device_instance}) is missing {total_missing}/{len(essential_properties)} essential properties'
            }
            
            if verbose:
                # Get all actual properties for this device
                all_device_props = []
                for _, pred, obj in graph.triples((device, None, None)):
                    pred_str = str(pred)
                    # Extract property name from URI
                    if pred_str.startswith(str(BACNET_NS)):
                        prop_name = pred_str.replace(str(BACNET_NS), "")
                    elif pred_str.endswith('#label'):
                        prop_name = 'label'
                    elif pred_str.endswith('#type'):
                        prop_name = 'type'
                    else:
                        prop_name = pred_str.split('/')[-1].split('#')[-1]
                    
                    all_device_props.append({
                        'property': prop_name,
                        'value': str(obj),
                        'full_uri': pred_str
                    })
                
                issue['all_properties'] = all_device_props
                issue['verbose_description'] = (
                    f'Device {device_name} (URI: {device}) has {len(all_device_props)} total properties '
                    f'but is missing {total_missing} essential BACnet properties: {", ".join(missing_properties)}. '
                    f'Present essential properties: {", ".join(present_properties) if present_properties else "none"}.'
                )
                
                if missing_critical:
                    issue['verbose_description'] += f' Critical missing properties: {", ".join(missing_critical)}'
            
            issues.append(issue)
            affected_nodes.append(device)
    
    return issues, affected_triples, affected_nodes
