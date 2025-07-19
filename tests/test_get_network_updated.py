#!/usr/bin/env python3
"""
Tests for the updated get-network command with TTL/JSON options
"""
import pytest
import tempfile
import json
from unittest.mock import patch
from click.testing import CliRunner
from graph_hopper import cli


class TestGetNetworkUpdated:
    """Test cases for the updated get-network command"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_get_network_default_ttl(self):
        """Test that get-network returns TTL by default"""
        mock_ttl_content = """@prefix ex: <http://example.org/> .
ex:Device1 a ex:BACnetDevice ;
    ex:deviceId 1234 ;
    ex:deviceName "Test Device" ."""
        
        with patch('graph_hopper.GrasshopperClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_ttl_file.return_value = mock_ttl_content
            
            result = self.runner.invoke(cli, [
                '-h', 'localhost:8000',
                'get-network',
                'test_file.ttl'
            ])
            
            assert result.exit_code == 0
            assert mock_ttl_content in result.output
            mock_instance.get_ttl_file.assert_called_once_with('test_file.ttl')

    def test_get_network_json_flag(self):
        """Test that get-network returns JSON with --json flag"""
        mock_network_data = {
            "nodes": [{"id": 1, "name": "Device1"}],
            "edges": [{"source": 1, "target": 2}]
        }
        
        with patch('graph_hopper.GrasshopperClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_ttl_network.return_value = mock_network_data
            
            result = self.runner.invoke(cli, [
                '-h', 'localhost:8000',
                'get-network',
                '--json',
                'test_file.ttl'
            ])
            
            assert result.exit_code == 0
            # Verify JSON content is in output
            assert '"nodes"' in result.output
            assert '"edges"' in result.output
            mock_instance.get_ttl_network.assert_called_once_with('test_file.ttl')

    def test_get_network_ttl_file_output(self):
        """Test saving TTL content to file"""
        mock_ttl_content = "@prefix ex: <http://example.org/> ."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_file.return_value = mock_ttl_content
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'get-network',
                    'test_file.ttl',
                    '--output', temp_path
                ])
                
                assert result.exit_code == 0
                assert "TTL data saved to" in result.output
                
                # Verify file content
                with open(temp_path, 'r') as f:
                    content = f.read()
                    assert content == mock_ttl_content
        finally:
            import os
            os.unlink(temp_path)

    def test_get_network_json_file_output(self):
        """Test saving JSON content to file"""
        mock_network_data = {"nodes": [], "edges": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            with patch('graph_hopper.GrasshopperClient') as MockClient:
                mock_instance = MockClient.return_value
                mock_instance.get_ttl_network.return_value = mock_network_data
                
                result = self.runner.invoke(cli, [
                    '-h', 'localhost:8000',
                    'get-network',
                    '--json',
                    'test_file.ttl',
                    '--output', temp_path
                ])
                
                assert result.exit_code == 0
                assert "JSON data saved to" in result.output
                
                # Verify file content
                with open(temp_path, 'r') as f:
                    data = json.load(f)
                    assert data == mock_network_data
        finally:
            import os
            os.unlink(temp_path)

    def test_get_network_error_handling(self):
        """Test error handling when API calls fail"""
        with patch('graph_hopper.GrasshopperClient') as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.get_ttl_file.return_value = None  # Simulate error
            
            result = self.runner.invoke(cli, [
                '-h', 'localhost:8000',
                'get-network',
                'nonexistent_file.ttl'
            ])
            
            assert result.exit_code == 1

    def test_get_network_help(self):
        """Test the help message for updated get-network command"""
        result = self.runner.invoke(cli, [
            '-h', 'localhost:8000',
            'get-network',
            '--help'
        ])
        
        assert result.exit_code == 0
        assert "Get data for a specific TTL file" in result.output
        assert "--json" in result.output
        assert "raw TTL by default" in result.output


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
