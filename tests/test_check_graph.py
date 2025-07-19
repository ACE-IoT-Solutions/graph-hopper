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


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
