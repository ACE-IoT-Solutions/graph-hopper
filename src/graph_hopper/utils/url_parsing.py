"""
URL parsing utilities for Graph Hopper CLI.

This module provides functions for parsing and normalizing host URLs.
"""

from urllib.parse import urlparse
import re
from typing import Optional


def parse_host_url(host_input: Optional[str]) -> str:
    """
    Parse host input and return a complete URL with defaults.
    
    Supports various input formats:
    - Simple hostname/IP: "localhost" -> "http://localhost:8000"
    - With port: "localhost:9000" -> "http://localhost:9000" 
    - With scheme: "http://localhost" -> "http://localhost:8000"
    - Full URL: "http://localhost:9000" -> "http://localhost:9000"
    - HTTPS: "https://api.example.com:8443" -> "https://api.example.com:8443"
    - Trailing slash handling: "localhost/" -> "http://localhost:8000"
    
    Args:
        host_input: The host string to parse
        
    Returns:
        Complete URL string with scheme, host, and port
        
    Raises:
        ValueError: If the host input is invalid or empty
    """
    if not host_input or not host_input.strip():
        raise ValueError("Host URL cannot be empty")
    
    host_input = host_input.strip()
    
    # Check if it's already a complete URL with scheme
    if '://' in host_input:
        parsed = urlparse(host_input)
        
        # Validate that we have a valid scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid host URL: {host_input}")
        
        # Remove trailing slash if it's just "/" (no actual path)
        path = parsed.path
        if path == "/":
            path = ""
        
        # If no port specified, add default port
        if not parsed.port:
            default_port = 443 if parsed.scheme == 'https' else 8000
            return f"{parsed.scheme}://{parsed.hostname}:{default_port}{path}"
        else:
            return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    # Remove trailing slash for simple hostnames
    if host_input.endswith('/'):
        host_input = host_input[:-1]
    
    # IPv6 address handling (with or without port)
    ipv6_pattern = r'^\[([a-fA-F0-9:]+)\](?::(\d+))?$'
    ipv6_match = re.match(ipv6_pattern, host_input)
    if ipv6_match:
        ipv6_addr = ipv6_match.group(1)
        port = ipv6_match.group(2) or '8000'
        return f"http://[{ipv6_addr}]:{port}"
    
    # Simple IPv6 without brackets
    if ':' in host_input and not host_input.count(':') == 1:
        # Likely IPv6 - wrap in brackets with default port
        if host_input.startswith('[') and host_input.endswith(']'):
            return f"http://{host_input}:8000"
        else:
            return f"http://[{host_input}]:8000"
    
    # Check for port in the format "host:port"
    if ':' in host_input:
        host_part, port_part = host_input.rsplit(':', 1)
        if port_part.isdigit():
            return f"http://{host_input}"
        else:
            # Not a valid port, treat the whole thing as hostname
            return f"http://{host_input}:8000"
    
    # Simple hostname/IP without port
    return f"http://{host_input}:8000"
