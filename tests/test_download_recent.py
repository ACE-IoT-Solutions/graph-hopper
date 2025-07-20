#!/usr/bin/env python3
"""
Tests for the download-recent command
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner
from graph_hopper import cli


class TestDownloadRecentCommand:
    """Test cases for the download-recent command"""
    
    runner: CliRunner
    mock_client: Mock

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        self.mock_client = Mock()

    def test_download_recent_basic_functionality(self):
        """Test basic functionality with 5 files (default TTL format)"""
        # Mock TTL file list
        mock_ttl_files = [
            "network_20240118_120000.ttl",
            "network_20240118_100000.ttl", 
            "network_20240117_180000.ttl",
            "network_20240117_160000.ttl",
            "network_20240117_140000.ttl",
            "network_20240116_120000.ttl",  # Should not be included (6th oldest)
        ]
        
        # Mock TTL file content
        mock_ttl_content = """@prefix ex: <http://example.org/> .
ex:Device1 a ex:BACnetDevice ;
    ex:deviceId 1234 ;
    ex:deviceName "Test Device" ."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_file.return_value = mock_ttl_content
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--output-dir', temp_dir,
                    '--verbose'
                ])
                
                assert result.exit_code == 0
                assert "✓ Successfully downloaded 5 TTL files" in result.output
                
                # Check that files were created
                output_path = Path(temp_dir)
                ttl_files = list(output_path.glob("*.ttl"))
                assert len(ttl_files) == 5
                
                # Verify file content
                for ttl_file in ttl_files:
                    with open(ttl_file) as f:
                        data = f.read()
                        assert data == mock_ttl_content

    def test_download_recent_fewer_than_requested(self):
        """Test when there are fewer files available than requested"""
        mock_ttl_files = [
            "network_20240118_120000.ttl",
            "network_20240117_180000.ttl",
        ]
        
        mock_ttl_content = "@prefix ex: <http://example.org/> ."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_file.return_value = mock_ttl_content
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--count', '5',
                    '--output-dir', temp_dir
                ])
                
                assert result.exit_code == 0
                assert "✓ Successfully downloaded 2 TTL files" in result.output
                
                # Check that only 2 files were created
                output_path = Path(temp_dir)
                ttl_files = list(output_path.glob("*.ttl"))
                assert len(ttl_files) == 2

    def test_download_recent_no_files_available(self):
        """Test when no TTL files are available"""
        with patch('graph_hopper.GrasshopperClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_ttl_list.return_value = []
            
            result = self.runner.invoke(cli, [
                '-h', 'localhost:8000',
                'download-recent'
            ])
            
            assert result.exit_code == 0
            assert "No TTL files found on the server." in result.output

    def test_download_recent_network_errors(self):
        """Test handling of network errors during download"""
        mock_ttl_files = [
            "network_20240118_120000.ttl",
            "network_20240117_180000.ttl",
        ]
        
        mock_ttl_content = "@prefix ex: <http://example.org/> ."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                # First call succeeds, second fails
                mock_instance.get_ttl_file.side_effect = [
                    mock_ttl_content,
                    None  # Simulate network error
                ]
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--output-dir', temp_dir,
                    '--verbose'
                ])
                
                assert result.exit_code == 0
                assert "✓ Successfully downloaded 1 TTL files" in result.output
                assert "⚠ 1 files failed to download" in result.output
                
                # Check that only 1 file was created
                output_path = Path(temp_dir)
                ttl_files = list(output_path.glob("*.ttl"))
                assert len(ttl_files) == 1

    def test_download_recent_custom_count(self):
        """Test custom count parameter"""
        mock_ttl_files = [
            "network_20240118_120000.ttl",
            "network_20240117_180000.ttl",
            "network_20240116_160000.ttl",
        ]
        
        mock_ttl_content = "@prefix ex: <http://example.org/> ."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_file.return_value = mock_ttl_content
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--count', '2',
                    '--output-dir', temp_dir
                ])
                
                assert result.exit_code == 0
                assert "✓ Successfully downloaded 2 TTL files" in result.output
                
                # Check that only 2 files were created
                output_path = Path(temp_dir)
                ttl_files = list(output_path.glob("*.ttl"))
                assert len(ttl_files) == 2

    def test_download_recent_directory_creation_error(self):
        """Test error handling when output directory cannot be created"""
        mock_ttl_files = ["network_20240118_120000.ttl"]
        
        with patch('graph_hopper.GrasshopperClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_ttl_list.return_value = mock_ttl_files
            
            # Use a directory that requires root permissions (should fail on most systems)
            invalid_dir = "/root/restricted/path"
            
            result = self.runner.invoke(cli, [
                '-h', 'localhost:8000',
                'download-recent',
                '--output-dir', invalid_dir
            ])
            
            # The command should exit with code 1 due to permission error
            assert result.exit_code == 1
            assert "Error creating output directory" in result.output

    def test_download_recent_file_sorting(self):
        """Test that files are sorted correctly (most recent first)"""
        mock_ttl_files = [
            "network_20240116_120000.ttl",  # Oldest
            "network_20240118_120000.ttl",  # Newest
            "network_20240117_180000.ttl",  # Middle
        ]
        
        mock_network_data = {"nodes": [], "edges": []}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_network.return_value = mock_network_data
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--count', '2',
                    '--output-dir', temp_dir,
                    '--verbose'
                ])
                
                assert result.exit_code == 0
                
                # Should download the 2 most recent files (2024-01-18 and 2024-01-17)
                # The verbose output should show which files were selected
                assert "network_20240118_120000.ttl" in result.output
                assert "network_20240117_180000.ttl" in result.output
                # The oldest file should not be mentioned in the selection
                # (it might appear in the "Found X files" message though)

    def test_download_recent_filename_formatting(self):
        """Test that output filenames are formatted correctly"""
        mock_ttl_files = ["network_test.ttl", "UPPERCASE.TTL"]
        mock_ttl_content = "@prefix ex: <http://example.org/> ."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_file.return_value = mock_ttl_content
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--output-dir', temp_dir
                ])
                
                assert result.exit_code == 0
                
                # Check filename formatting
                output_path = Path(temp_dir)
                ttl_files = list(output_path.glob("*.ttl"))
                assert len(ttl_files) == 2
                
                # Files should have timestamp appended and .ttl extension
                filenames = [f.name for f in ttl_files]
                
                # Should have network_test_TIMESTAMP.ttl and UPPERCASE_TIMESTAMP.ttl
                assert any("network_test_" in name and name.endswith(".ttl") for name in filenames)
                assert any("UPPERCASE_" in name and name.endswith(".ttl") for name in filenames)

    def test_download_recent_help(self):
        """Test the help message for download-recent command"""
        result = self.runner.invoke(cli, [
            '-h', 'localhost:8000',
            'download-recent',
            '--help'
        ])
        
        assert result.exit_code == 0
        assert "Download the most recent network graph files" in result.output
        assert "--count" in result.output
        assert "--output-dir" in result.output
        assert "--json" in result.output
        assert "--verbose" in result.output

    def test_download_recent_json_format(self):
        """Test downloading files in JSON format using --json flag"""
        mock_ttl_files = [
            "network_20240118_120000.ttl",
            "network_20240117_180000.ttl",
        ]
        
        mock_network_data = {
            "nodes": [{"id": 1, "name": "Device1"}],
            "edges": [{"source": 1, "target": 2}]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_list.return_value = mock_ttl_files
                mock_instance.get_ttl_network.return_value = mock_network_data
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'download-recent',
                    '--json',
                    '--output-dir', temp_dir
                ])
                
                assert result.exit_code == 0
                assert "✓ Successfully downloaded 2 JSON files" in result.output
                
                # Check that JSON files were created
                output_path = Path(temp_dir)
                json_files = list(output_path.glob("*.json"))
                assert len(json_files) == 2
                
                # Verify JSON content
                for json_file in json_files:
                    with open(json_file) as f:
                        import json
                        data = json.load(f)
                        assert data == mock_network_data


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
