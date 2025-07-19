"""
Tests for URL parsing functionality
"""

import pytest
from graph_hopper import parse_host_url


class TestURLParsing:
    """Test cases for the URL parsing functionality"""
    
    def test_simple_hostname(self):
        """Test parsing simple hostname"""
        result = parse_host_url("localhost")
        assert result == "http://localhost:8000"
    
    def test_simple_ip(self):
        """Test parsing simple IP address"""
        result = parse_host_url("192.168.1.100")
        assert result == "http://192.168.1.100:8000"
    
    def test_hostname_with_port(self):
        """Test parsing hostname with port"""
        result = parse_host_url("localhost:9000")
        assert result == "http://localhost:9000"
    
    def test_ip_with_port(self):
        """Test parsing IP with port"""
        result = parse_host_url("192.168.1.100:9000")
        assert result == "http://192.168.1.100:9000"
    
    def test_http_scheme_only(self):
        """Test parsing with HTTP scheme only"""
        result = parse_host_url("http://localhost")
        assert result == "http://localhost:8000"
    
    def test_https_scheme_only(self):
        """Test parsing with HTTPS scheme only"""
        result = parse_host_url("https://localhost")
        assert result == "https://localhost:443"
    
    def test_full_http_url(self):
        """Test parsing full HTTP URL"""
        result = parse_host_url("http://localhost:9000")
        assert result == "http://localhost:9000"
    
    def test_full_https_url(self):
        """Test parsing full HTTPS URL"""
        result = parse_host_url("https://api.example.com:8443")
        assert result == "https://api.example.com:8443"
    
    def test_complex_hostname(self):
        """Test parsing complex hostname"""
        result = parse_host_url("api.grasshopper.local")
        assert result == "http://api.grasshopper.local:8000"
    
    def test_ipv6_address(self):
        """Test parsing IPv6 address"""
        result = parse_host_url("[::1]")
        assert result == "http://[::1]:8000"
    
    def test_ipv6_with_port(self):
        """Test parsing IPv6 address with port"""
        result = parse_host_url("[::1]:9000")
        assert result == "http://[::1]:9000"
    
    def test_invalid_url_raises_error(self):
        """Test that invalid URLs raise appropriate errors"""
        with pytest.raises(ValueError, match="Invalid host URL"):
            parse_host_url("not-a-valid-url://")
    
    def test_empty_string_raises_error(self):
        """Test that empty string raises error"""
        with pytest.raises(ValueError, match="Host URL cannot be empty"):
            parse_host_url("")
    
    def test_none_raises_error(self):
        """Test that None raises error"""
        with pytest.raises(ValueError, match="Host URL cannot be empty"):
            parse_host_url(None)
    
    def test_simple_hostname_with_trailing_slash(self):
        """Test parsing simple hostname with trailing slash"""
        result = parse_host_url("localhost/")
        assert result == "http://localhost:8000"
    
    def test_ip_with_trailing_slash(self):
        """Test parsing IP with trailing slash"""
        result = parse_host_url("192.168.1.100/")
        assert result == "http://192.168.1.100:8000"
    
    def test_hostname_with_port_and_trailing_slash(self):
        """Test parsing hostname with port and trailing slash"""
        result = parse_host_url("localhost:9000/")
        assert result == "http://localhost:9000"
    
    def test_http_url_with_trailing_slash(self):
        """Test parsing HTTP URL with trailing slash"""
        result = parse_host_url("http://localhost/")
        assert result == "http://localhost:8000"
    
    def test_https_url_with_trailing_slash(self):
        """Test parsing HTTPS URL with trailing slash"""
        result = parse_host_url("https://localhost/")
        assert result == "https://localhost:443"
    
    def test_full_url_with_trailing_slash(self):
        """Test parsing full URL with trailing slash"""
        result = parse_host_url("http://localhost:9000/")
        assert result == "http://localhost:9000"
    
    def test_url_with_actual_path_preserved(self):
        """Test that actual paths (not just trailing slash) are preserved"""
        result = parse_host_url("http://localhost:9000/api/v1")
        assert result == "http://localhost:9000/api/v1"
    
    def test_ipv6_with_trailing_slash(self):
        """Test parsing IPv6 with trailing slash"""
        result = parse_host_url("[::1]/")
        assert result == "http://[::1]:8000"


class TestCLIWithNewHostOption:
    """Test CLI commands with the new host option"""
    
    def test_cli_with_simple_host(self):
        """Test CLI with simple hostname"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'status'])
        # Should fail to connect but not have argument parsing errors
        assert result.exit_code == 1
        assert 'Cannot connect' in result.output
        assert 'http://localhost:8000' in result.output
    
    def test_cli_with_full_url(self):
        """Test CLI with full URL"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'http://localhost:9000', 'status'])
        # Should fail to connect but not have argument parsing errors
        assert result.exit_code == 1
        assert 'Cannot connect' in result.output
        assert 'http://localhost:9000' in result.output
    
    def test_cli_with_https_url(self):
        """Test CLI with HTTPS URL"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'https://api.example.com:8443', 'status'])
        # Should fail to connect but not have argument parsing errors
        assert result.exit_code == 1
        assert 'Cannot connect' in result.output
        assert 'https://api.example.com:8443' in result.output
    
    def test_cli_requires_host(self):
        """Test that CLI still requires host parameter"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()
    
    def test_cli_help_shows_host_option(self):
        """Test that help shows the new host option"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert '-h, --host' in result.output
        assert 'Grasshopper instance URL' in result.output or 'host' in result.output.lower()
    
    def test_list_graphs_only_shows_ttl_files(self):
        """Test that list-graphs only shows TTL files, not comparison files"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'list-graphs'])
        # Command should run successfully even if no connection (graceful error handling)
        assert result.exit_code == 0
        assert 'TTL files' in result.output or 'No TTL network files found' in result.output
    
    def test_list_compares_command_exists(self):
        """Test that list-compares command exists"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'list-compares'])
        # Command should run successfully even if no connection (graceful error handling)
        assert result.exit_code == 0
        assert 'comparison files' in result.output.lower() or 'No comparison files found' in result.output
    
    def test_list_compares_help(self):
        """Test that list-compares help works"""
        from click.testing import CliRunner
        from graph_hopper import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['-h', 'localhost', 'list-compares', '--help'])
        assert result.exit_code == 0
        assert 'List available comparison files' in result.output or 'comparison' in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__])
