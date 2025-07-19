"""
Tests for the Graph Hopper CLI
"""

import pytest
from click.testing import CliRunner
from graph_hopper import cli


class TestCLI:
    """Test cases for the CLI functionality"""
    
    def test_cli_requires_ip(self):
        """Test that CLI requires IP address"""
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()
    
    def test_status_command_with_invalid_ip(self):
        """Test status command with invalid IP (should fail gracefully)"""
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', '127.0.0.1', 'status'])
        assert result.exit_code == 1
        assert 'Cannot connect' in result.output
    
    def test_list_graphs_help(self):
        """Test that list-graphs help works"""
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'list-graphs', '--help'])
        assert result.exit_code == 0
        assert 'List available TTL network files' in result.output
    
    def test_get_network_help(self):
        """Test that get-network help works"""
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'get-network', '--help'])
        assert result.exit_code == 0
        assert 'Get data for a specific TTL file' in result.output
    
    def test_main_help(self):
        """Test main CLI help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Graph Hopper CLI' in result.output
        assert 'Retrieve graphs from Grasshopper API' in result.output


class TestGrasshopperClient:
    """Test the GrasshopperClient class"""
    
    def test_client_initialization(self):
        """Test client can be initialized"""
        from graph_hopper import GrasshopperClient
        
        client = GrasshopperClient("http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
        client.close()
    
    def test_client_strips_trailing_slash(self):
        """Test that client strips trailing slashes from base URL"""
        from graph_hopper import GrasshopperClient
        
        client = GrasshopperClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"
        client.close()


if __name__ == "__main__":
    pytest.main([__file__])
