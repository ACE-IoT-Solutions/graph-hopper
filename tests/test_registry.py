"""
Test the dynamic issue registry system.
"""

import pytest
from graph_hopper.graph_checks import ISSUE_REGISTRY


def test_dynamic_registry():
    """Test that the issue registry provides dynamic functionality."""
    
    # Test getting all issue types
    all_types = ISSUE_REGISTRY.get_all_issue_types()
    assert 'duplicate-device-id' in all_types
    assert 'orphaned-devices' in all_types
    assert 'duplicate-network' in all_types
    assert 'duplicate-router' in all_types
    assert 'duplicate-bbmd-warning' in all_types
    assert 'duplicate-bbmd-error' in all_types
    
    # Test CLI choices include 'all'
    cli_choices = ISSUE_REGISTRY.get_cli_choices()
    assert 'all' in cli_choices
    assert set(all_types).issubset(set(cli_choices))
    
    # Test resolving 'all' returns all issue types
    all_resolved = ISSUE_REGISTRY.resolve_issues_to_check('all')
    assert set(all_resolved) == set(all_types)
    
    # Test resolving specific single-type issue
    orphaned_resolved = ISSUE_REGISTRY.resolve_issues_to_check('orphaned-devices')
    assert orphaned_resolved == ['orphaned-devices']
    
    # Test resolving multi-type issue includes related types
    network_resolved = ISSUE_REGISTRY.resolve_issues_to_check('duplicate-network')
    assert 'duplicate-network' in network_resolved
    assert 'duplicate-router' in network_resolved
    
    # Test getting descriptions
    description = ISSUE_REGISTRY.get_issue_description('orphaned-devices')
    assert 'connected' in description.lower()
    
    # Test single vs multi-check detection
    assert ISSUE_REGISTRY.is_single_check('orphaned-devices')
    assert not ISSUE_REGISTRY.is_single_check('duplicate-network')


def test_registry_extensibility():
    """Test that adding new checks would automatically work."""
    
    # Get current count
    current_types = ISSUE_REGISTRY.get_all_issue_types()
    current_count = len(current_types)
    
    # Verify we have expected minimum count (our current 6 types)
    assert current_count >= 6
    
    # Verify CLI choices has one more than issue types (due to 'all')
    cli_choices = ISSUE_REGISTRY.get_cli_choices()
    assert len(cli_choices) == current_count + 1  # +1 for 'all'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
