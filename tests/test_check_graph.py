#!/usr/bin/env python3
"""
Tests for the check-graph command
"""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from graph_hopper import cli


class TestCheckGraphCommand:
    """Test cases for the check-graph command"""
    
    runner: CliRunner

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def create_test_ttl_with_duplicate_device_ids(self, directory: Path):
        """Create test TTL file with duplicate device ID issue"""
        file1 = directory / "test_network.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Device with ID 123 on Network1
<bacnet://123> a ns1:Device ;
    rdfs:label "bacnet://123" ;
    ns1:address "19103:7" ;
    ns1:device-instance 123 ;
    ns1:device-on-network <bacnet://network/19103> ;
    ns1:vendor-id <bacnet://vendor/5> .

# Same device ID 123 on Network2 (duplicate!)
<bacnet://123-duplicate> a ns1:Device ;
    rdfs:label "bacnet://123-duplicate" ;
    ns1:address "9103:123" ;
    ns1:device-instance 123 ;
    ns1:device-on-network <bacnet://network/9103> ;
    ns1:vendor-id <bacnet://vendor/127> .

# Device with ID 456 on Subnet1
<bacnet://456> a ns1:Device ;
    rdfs:label "bacnet://456" ;
    ns1:address "10.21.86.22" ;
    ns1:device-instance 456 ;
    ns1:device-on-subnet <bacnet://subnet/10.21.86.0/24> ;
    ns1:vendor-id <bacnet://vendor/306> .

# Same device ID 456 on MSTP Network (duplicate!)
<bacnet://456-dup> a ns1:Device ;
    rdfs:label "bacnet://456-dup" ;
    ns1:address "19229:19" ;
    ns1:device-instance 456 ;
    ns1:device-on-network <bacnet://network/19229> ;
    ns1:vendor-id <bacnet://vendor/133> .

# Valid device (ID 789, only on one network)
<bacnet://789> a ns1:Device ;
    rdfs:label "bacnet://789" ;
    ns1:address "19103:1" ;
    ns1:device-instance 789 ;
    ns1:device-on-network <bacnet://network/19103> ;
    ns1:vendor-id <bacnet://vendor/10> .
""")
        return file1

    def create_test_ttl_no_duplicates(self, directory: Path):
        """Create test TTL file with no duplicate device ID issues"""
        file1 = directory / "clean_network.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Each device has unique ID across all networks
<bacnet://100> a ns1:Device ;
    rdfs:label "bacnet://100" ;
    ns1:address "19103:7" ;
    ns1:device-instance 100 ;
    ns1:device-on-network <bacnet://network/19103> ;
    ns1:vendor-id <bacnet://vendor/5> .

<bacnet://200> a ns1:Device ;
    rdfs:label "bacnet://200" ;
    ns1:address "9103:200" ;
    ns1:device-instance 200 ;
    ns1:device-on-network <bacnet://network/9103> ;
    ns1:vendor-id <bacnet://vendor/127> .

<bacnet://300> a ns1:Device ;
    rdfs:label "bacnet://300" ;
    ns1:address "10.21.86.22" ;
    ns1:device-instance 300 ;
    ns1:device-on-subnet <bacnet://subnet/10.21.86.0/24> ;
    ns1:vendor-id <bacnet://vendor/306> .
""")
        return file1

    def test_check_graph_duplicate_device_ids_detected(self):
        """Test detection of duplicate device IDs across networks"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = self.create_test_ttl_with_duplicate_device_ids(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(test_file),
                '--issue', 'duplicate-device-id'
            ])
            
            assert result.exit_code == 1  # Should exit with error when issues found
            # Should detect 2 duplicate device ID issues (123 and 456)
            assert "duplicate-device-id" in result.output or "duplicate device id" in result.output
            assert "Device ID 123" in result.output or "device_id" in result.output
            assert "Device ID 456" in result.output or "device_id" in result.output
            # Should mention the networks they conflict across
            assert "network/19103" in result.output or "network/9103" in result.output
            assert "subnet" in result.output or "network/19229" in result.output

    def test_check_graph_no_duplicate_device_ids(self):
        """Test when no duplicate device IDs are found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = self.create_test_ttl_no_duplicates(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(test_file),
                '--issue', 'duplicate-device-id'
            ])
            
            assert result.exit_code == 0
            assert "No duplicate device ID issues found" in result.output or "✓" in result.output

    def test_check_graph_all_issues_by_default(self):
        """Test that all issues are checked by default when no --issue specified"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = self.create_test_ttl_with_duplicate_device_ids(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(test_file)
            ])
            
            assert result.exit_code == 1  # Should exit with error when issues found
            # Should check all available issues
            assert "duplicate-device-id" in result.output or "duplicate device id" in result.output

    def test_check_graph_verbose_output(self):
        """Test verbose output shows all affected triples"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = self.create_test_ttl_with_duplicate_device_ids(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(test_file),
                '--issue', 'duplicate-device-id',
                '--verbose'
            ])
            
            assert result.exit_code == 1  # Should exit with error when issues found
            # Verbose should show the specific triples involved
            assert "ns1:device-instance" in result.output or "device-instance" in result.output
            assert "ns1:device-on-network" in result.output or "device-on-network" in result.output or "device-on-subnet" in result.output

    def test_check_graph_output_formats(self):
        """Test different output formats (human-readable vs structured)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = self.create_test_ttl_with_duplicate_device_ids(temp_path)
            
            # Test human-readable output (default)
            result = self.runner.invoke(cli, [
                'check-graph',
                str(test_file),
                '--issue', 'duplicate-device-id'
            ])
            
            assert result.exit_code == 1  # Should exit with error when issues found
            assert "Device ID" in result.output or "duplicate" in result.output
            
            # Test structured output
            result_json = self.runner.invoke(cli, [
                'check-graph',
                str(test_file),
                '--issue', 'duplicate-device-id',
                '--json'
            ])
            
            assert result_json.exit_code == 1  # Should exit with error when issues found
            # Should contain JSON structure
            assert "{" in result_json.output and "}" in result_json.output

    def test_check_graph_help_message(self):
        """Test the help message for check-graph command"""
        result = self.runner.invoke(cli, [
            'check-graph',
            '--help'
        ])
        
        assert result.exit_code == 0
        assert "Analyze TTL graphs for common BACnet network issues" in result.output
        assert "--issue" in result.output
        assert "duplicate-device-id" in result.output
        assert "--verbose" in result.output
        assert "--json" in result.output

    def test_check_graph_invalid_ttl_file(self):
        """Test error handling for invalid TTL files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            invalid_file = temp_path / "invalid.ttl"
            invalid_file.write_text("This is not valid TTL content")
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(invalid_file),
                '--issue', 'duplicate-device-id'
            ])
            
            # Should exit with error code for parsing failure
            assert result.exit_code == 1
            assert "Error parsing TTL file" in result.output or "parse" in result.output.lower()

    def test_check_graph_nonexistent_file(self):
        """Test error handling for nonexistent files"""
        result = self.runner.invoke(cli, [
            'check-graph',
            '/nonexistent/file.ttl',
            '--issue', 'duplicate-device-id'
        ])
        
        assert result.exit_code == 2  # CLI framework returns 2 for missing files
        assert "not found" in result.output or "does not exist" in result.output

    def test_check_graph_duplicate_networks_detection(self):
        """Test detection of duplicate networks across routers"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_networks(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_networks.ttl"),
                '--issue', 'duplicate-network'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "duplicate network" in result.output
            assert "Network bacnet://network/19202" in result.output
            assert "routers in different subnets" in result.output

    def test_check_graph_duplicate_routers_detection(self):
        """Test detection of duplicate routers in same subnet"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_networks(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_networks.ttl"),
                '--issue', 'duplicate-router'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "duplicate router" in result.output
            assert "Network bacnet://network/19101" in result.output
            assert "routers in the same subnet" in result.output

    def test_check_graph_all_issues_detection(self):
        """Test detection of all issue types together"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_all_issues(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph', 
                str(temp_path / "test_all_issues.ttl"),
                '--issue', 'all'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "duplicate device id" in result.output
            assert "duplicate network" in result.output
            assert "duplicate router" in result.output

    def test_check_graph_json_output(self):
        """Test JSON output format for duplicate issues"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_networks(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_networks.ttl"),
                '--issue', 'all',
                '--json'
            ])
            
            assert result.exit_code == 1  # Issues found
            
            # Check JSON structure
            import json
            output_json = json.loads(result.output)
            assert "duplicate-device-id" in output_json
            assert "duplicate-network" in output_json
            assert "duplicate-router" in output_json
            assert len(output_json["duplicate-network"]) > 0
            assert len(output_json["duplicate-router"]) > 0

    def create_test_ttl_with_duplicate_networks(self, directory: Path):
        """Create test TTL file with duplicate network issues"""
        file1 = directory / "test_duplicate_networks.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .

# Duplicate router scenario - same network on multiple routers in same subnet
<bacnet://router/10.21.1.10> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19101> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.1.0/24> .

<bacnet://router/10.21.1.11> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19101> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.1.0/24> .

# Duplicate network scenario - same network on routers in different subnets
<bacnet://router/10.21.2.20> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19202> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.2.0/24> .

<bacnet://router/10.21.3.30> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19202> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.3.0/24> .
""")

    def create_test_ttl_with_all_issues(self, directory: Path):
        """Create test TTL file with all types of issues"""
        file1 = directory / "test_all_issues.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .

# Duplicate device ID
<bacnet://device1> a ns1:Device ;
    ns1:device-instance 123 ;
    ns1:device-on-network <bacnet://network/19101> .

<bacnet://device2> a ns1:Device ;
    ns1:device-instance 123 ;
    ns1:device-on-network <bacnet://network/19102> .

# Duplicate router
<bacnet://router/10.21.1.10> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19201> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.1.0/24> .

<bacnet://router/10.21.1.11> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19201> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.1.0/24> .

# Duplicate network  
<bacnet://router/10.21.2.20> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19301> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.2.0/24> .

<bacnet://router/10.21.3.30> a ns1:Router ;
    ns1:device-on-network <bacnet://network/19301> ;
    ns1:device-on-subnet <bacnet://subnet/10.21.3.0/24> .
""")

    def test_check_graph_duplicate_bbmd_warning(self):
        """Test detection of multiple BBMDs on same subnet (warning)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_bbmds(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_bbmds.ttl"),
                '--issue', 'duplicate-bbmd-warning'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "duplicate bbmd warning" in result.output
            assert "Multiple BBMDs on the same subnet" in result.output
            assert "BBMDs with BDT entries: 1/2" in result.output

    def test_check_graph_duplicate_bbmd_error(self):
        """Test detection of multiple BBMDs with BDT entries (error)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_bbmds(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_bbmds.ttl"),
                '--issue', 'duplicate-bbmd-error'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "duplicate bbmd error" in result.output
            assert "Multiple BBMDs with BDT entries on the same subnet" in result.output
            assert "BBMDs with BDT entries: 2/2" in result.output

    def test_check_graph_bbmd_json_output(self):
        """Test JSON output format for BBMD issues"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_duplicate_bbmds(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_duplicate_bbmds.ttl"),
                '--issue', 'all',
                '--json'
            ])
            
            assert result.exit_code == 1  # Issues found
            
            # Check JSON structure
            import json
            output_json = json.loads(result.output)
            assert "duplicate-bbmd-warning" in output_json
            assert "duplicate-bbmd-error" in output_json
            assert len(output_json["duplicate-bbmd-warning"]) > 0
            assert len(output_json["duplicate-bbmd-error"]) > 0
            
            # Check specific fields
            warning_issue = output_json["duplicate-bbmd-warning"][0]
            assert warning_issue["severity"] == "warning"
            assert warning_issue["bbmds_with_bdt_count"] == 1
            
            error_issue = output_json["duplicate-bbmd-error"][0]
            assert error_issue["severity"] == "error"
            assert error_issue["bbmds_with_bdt_count"] == 2

    def create_test_ttl_with_duplicate_bbmds(self, directory: Path):
        """Create test TTL file with duplicate BBMD scenarios"""
        file1 = directory / "test_duplicate_bbmds.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .

# Warning scenario - Multiple BBMDs on same subnet, only one has BDT entries
<bacnet://9001> a ns1:BBMD ;
    ns1:address "10.21.1.10" ;
    ns1:bbmd-broadcast-domain <bacnet://subnet/10.21.1.0/24> ;
    ns1:bdt-entry <bacnet://9001> ;
    ns1:device-instance 9001 .

<bacnet://9002> a ns1:BBMD ;
    ns1:address "10.21.1.20" ;
    ns1:bbmd-broadcast-domain <bacnet://subnet/10.21.1.0/24> ;
    ns1:device-instance 9002 .

# Error scenario - Multiple BBMDs on same subnet, both have BDT entries
<bacnet://9101> a ns1:BBMD ;
    ns1:address "10.21.2.10" ;
    ns1:bbmd-broadcast-domain <bacnet://subnet/10.21.2.0/24> ;
    ns1:bdt-entry <bacnet://9101> ;
    ns1:device-instance 9101 .

<bacnet://9102> a ns1:BBMD ;
    ns1:address "10.21.2.20" ;
    ns1:bbmd-broadcast-domain <bacnet://subnet/10.21.2.0/24> ;
    ns1:bdt-entry <bacnet://9102> ;
    ns1:device-instance 9102 .
""")

    def create_test_ttl_with_orphaned_devices(self, directory: Path):
        """Create test TTL file with orphaned device issues"""
        file1 = directory / "test_orphaned_devices.ttl"
        file1.write_text("""@prefix ns1: <http://data.ashrae.org/bacnet/2020#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# Orphaned device - no network or subnet connection
<bacnet://orphaned/100> a ns1:Device ;
    rdfs:label "Orphaned Device 100" ;
    ns1:address "192.168.1.100" ;
    ns1:device-instance 100 ;
    ns1:vendor-id <bacnet://vendor/15> .

# Another orphaned device
<bacnet://orphaned/200> a ns1:Device ;
    rdfs:label "Orphaned Device 200" ;
    ns1:address "10.0.0.200" ;
    ns1:device-instance 200 ;
    ns1:vendor-id <bacnet://vendor/10> .

# Properly connected device (should not be flagged)
<bacnet://connected/300> a ns1:Device ;
    rdfs:label "Connected Device 300" ;
    ns1:address "19103:7" ;
    ns1:device-instance 300 ;
    ns1:device-on-network <bacnet://network/19103> ;
    ns1:vendor-id <bacnet://vendor/5> .

# Router (should not be flagged)
<bacnet://router/400> a ns1:Router ;
    rdfs:label "Router 400" ;
    ns1:address "192.168.1.1" ;
    ns1:device-instance 400 ;
    ns1:device-on-subnet <bacnet://subnet/192.168.1.0/24> ;
    ns1:vendor-id <bacnet://vendor/15> .
""")

    def test_check_graph_orphaned_devices_detection(self):
        """Test detection of orphaned devices"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_orphaned_devices(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_orphaned_devices.ttl"),
                '--issue', 'orphaned-devices'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "orphaned device" in result.output.lower()
            assert "Orphaned Device 100" in result.output
            assert "Orphaned Device 200" in result.output
            # Should NOT include the connected device or router
            assert "Connected Device 300" not in result.output
            assert "Router 400" not in result.output

    def test_check_graph_orphaned_devices_json_output(self):
        """Test JSON output for orphaned devices"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_orphaned_devices(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_orphaned_devices.ttl"),
                '--issue', 'orphaned-devices',
                '--json'
            ])
            
            assert result.exit_code == 1  # Issues found
            
            import json
            output_data = json.loads(result.output)
            
            # Check that orphaned devices are reported
            assert 'orphaned-devices' in output_data
            assert len(output_data['orphaned-devices']) == 2
            
            # Check that both orphaned devices are reported
            orphaned_issues = output_data['orphaned-devices']
            
            # Verify issue details
            device_instances = {issue['device_instance'] for issue in orphaned_issues}
            assert device_instances == {"100", "200"}

    def test_check_graph_orphaned_devices_verbose(self):
        """Test verbose output for orphaned devices"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_with_orphaned_devices(temp_path)
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "test_orphaned_devices.ttl"),
                '--issue', 'orphaned-devices',
                '--verbose'
            ])
            
            assert result.exit_code == 1  # Issues found
            assert "orphaned device" in result.output.lower()
            assert "cannot communicate with other devices" in result.output.lower()
            # Verbose mode should show additional details
            assert "properties" in result.output.lower() or "triples" in result.output.lower()

    def test_check_graph_no_orphaned_devices_clean_network(self):
        """Test that clean networks with no orphaned devices pass"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_ttl_no_duplicates(temp_path)  # Use existing clean network
            
            result = self.runner.invoke(cli, [
                'check-graph',
                str(temp_path / "clean_network.ttl"),
                '--issue', 'orphaned-devices'
            ])
            
            assert result.exit_code == 0  # No issues found
            assert "No orphaned devices issues found" in result.output


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
