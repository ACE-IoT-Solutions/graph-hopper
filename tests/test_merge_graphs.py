#!/usr/bin/env python3
"""
Tests for the merge-graphs command
"""
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
import rdflib
from graph_hopper import cli


class TestMergeGraphsCommand:
    """Test cases for the merge-graphs command"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def create_test_ttl_files(self, directory: Path):
        """Create test TTL files for testing"""
        # File 1: Simple BACnet devices
        file1 = directory / "network_20240117_180000_20250718_143022.ttl"
        file1.write_text("""@prefix bacnet: <http://bacnet.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/Device1> a bacnet:BACnetDevice ;
    bacnet:deviceId "1"^^xsd:integer .

<http://example.org/Network1> a bacnet:BACnetNetwork ;
    bacnet:containsDevice <http://example.org/Device1> .
""")

        # File 2: More devices (with some overlapping triples)
        file2 = directory / "network_20240118_100000_20250718_143022.ttl"
        file2.write_text("""@prefix bacnet: <http://bacnet.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/Device1> a bacnet:BACnetDevice ;
    bacnet:deviceId "1"^^xsd:integer ;
    bacnet:deviceName "Device One" .

<http://example.org/Device2> a bacnet:BACnetDevice ;
    bacnet:deviceId "2"^^xsd:integer .

<http://example.org/Network1> a bacnet:BACnetNetwork ;
    bacnet:containsDevice <http://example.org/Device1> ;
    bacnet:containsDevice <http://example.org/Device2> .

<http://example.org/Property1> a bacnet:BACnetProperty ;
    bacnet:belongsToDevice <http://example.org/Device1> .
""")

        # File 3: Additional device
        file3 = directory / "network_20240118_120000_20250718_143022.ttl"
        file3.write_text("""@prefix bacnet: <http://bacnet.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/Device3> a bacnet:BACnetDevice ;
    bacnet:deviceId "3"^^xsd:integer .

<http://example.org/Network2> a bacnet:BACnetNetwork ;
    bacnet:containsDevice <http://example.org/Device3> .

<http://example.org/Property2> a bacnet:BACnetProperty ;
    bacnet:belongsToDevice <http://example.org/Device3> .

<http://example.org/Property3> a bacnet:BACnetProperty ;
    bacnet:belongsToDevice <http://example.org/Device3> .
""")

    def test_merge_graphs_basic_functionality(self):
        """Test basic merge functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create test files
            self.create_test_ttl_files(input_dir)
            output_file = output_dir / "merged_graph.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-dir', str(input_dir),
                '--output', str(output_file),
                '--verbose'
            ])
            
            assert result.exit_code == 0
            assert "Successfully merged" in result.output
            assert "Found 3 TTL files" in result.output
            assert output_file.exists()
            
            # Verify merged content
            merged_graph = rdflib.Graph()
            merged_graph.parse(output_file, format='turtle')
            
            # Should have all devices from all files
            devices_query = """
            PREFIX bacnet: <http://bacnet.org/>
            SELECT ?device WHERE {
                ?device a bacnet:BACnetDevice .
            }
            """
            devices = list(merged_graph.query(devices_query))
            assert len(devices) == 3  # Device1, Device2, Device3

    # def test_merge_graphs_default_directories(self):
    #     """Test merge with default input/output directories"""
    #     # This test is not implemented as the CLI requires explicit input/output paths
    #     pass

    def test_merge_graphs_glob_pattern(self):
        """Test merge with glob pattern for file selection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            input_dir.mkdir()
            
            # Create test files with different patterns
            self.create_test_ttl_files(input_dir)
            
            # Add a file that shouldn't match the pattern
            other_file = input_dir / "other_data.ttl"
            other_file.write_text("@prefix ex: <http://example.org/> .")
            
            output_file = temp_path / "merged_network.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-pattern', 'network_*.ttl',
                '--input-dir', str(input_dir),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Should only process network_*.ttl files (not other_data.ttl)
            assert "Successfully merged 3 TTL files" in result.output

    def test_merge_graphs_empty_directory(self):
        """Test handling of empty input directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            empty_dir = temp_path / "empty"
            empty_dir.mkdir()
            output_file = temp_path / "output.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-dir', str(empty_dir),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "No TTL files found" in result.output
            # Output file should still be created but empty
            assert output_file.exists()

    def test_merge_graphs_invalid_ttl_files(self):
        """Test handling of invalid TTL files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            input_dir.mkdir()
            
            # Create a valid TTL file
            valid_file = input_dir / "valid.ttl"
            valid_file.write_text("@prefix ex: <http://example.org/> . ex:Device1 a ex:BACnetDevice .")
            
            # Create an invalid TTL file
            invalid_file = input_dir / "invalid.ttl"
            invalid_file.write_text("This is not valid TTL content!")
            
            output_file = temp_path / "output.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-dir', str(input_dir),
                '--output', str(output_file),
                '--verbose'
            ])
            
            assert result.exit_code == 0  # Should still succeed with partial files
            assert "Failed to parse" in result.output
            assert output_file.exists()

    def test_merge_graphs_duplicate_handling(self):
        """Test that duplicate triples are properly handled"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            input_dir.mkdir()
            
            # Create files with duplicate triples
            file1 = input_dir / "file1.ttl"
            file1.write_text("""@prefix ex: <http://example.org/> .
ex:Device1 a ex:BACnetDevice .
ex:Device1 ex:deviceId "123" .
""")
            
            file2 = input_dir / "file2.ttl"
            file2.write_text("""@prefix ex: <http://example.org/> .
ex:Device1 a ex:BACnetDevice .
ex:Device2 a ex:BACnetDevice .
""")
            
            output_file = temp_path / "merged.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-dir', str(input_dir),
                '--output', str(output_file),
                '--verbose'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify deduplication
            merged_graph = rdflib.Graph()
            merged_graph.parse(output_file, format='turtle')
            
            # Count specific triples to ensure no duplicates
            from rdflib import RDF
            device_triples = list(merged_graph.triples((None, RDF.type, None)))
            assert len(device_triples) == 2  # Should have Device1 and Device2

    def test_merge_graphs_statistics(self):
        """Test verbose output with merge statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            input_dir.mkdir()
            
            # Create test files
            self.create_test_ttl_files(input_dir)
            output_file = temp_path / "merged.ttl"
            
            result = self.runner.invoke(cli, [
                'merge-graphs',
                '--input-dir', str(input_dir),
                '--output', str(output_file),
                '--verbose'
            ])
            
            assert result.exit_code == 0
            assert "Found 3 TTL files" in result.output
            assert "Total triples processed" in result.output
            assert "✓ Successfully merged" in result.output

    def test_merge_graphs_help(self):
        """Test the help message for merge-graphs command"""
        result = self.runner.invoke(cli, [
            'merge-graphs',
            '--help'
        ])
        
        assert result.exit_code == 0
        assert "Merge multiple TTL files into a single RDF graph" in result.output
