"""
Grasshopper API client module.

This module provides the GrasshopperClient class for interacting with the Grasshopper API
to retrieve TTL files, network data, and comparison files.
"""

import httpx
import click
from typing import Optional, List, Dict, Any


class GrasshopperClient:
    """Client for interacting with the Grasshopper API"""
    
    def __init__(self, base_url: str):
        """
        Initialize the Grasshopper API client.
        
        Args:
            base_url: The base URL for the Grasshopper API
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
    
    def get_ttl_list(self) -> List[str]:
        """
        Get list of available TTL files.
        
        Returns:
            List of TTL filenames
        """
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl")
            response.raise_for_status()
            
            data = response.json()
            
            # Handle multiple possible response formats from the API
            if isinstance(data, dict):
                if 'file_list' in data:
                    return data['file_list']
                elif 'files' in data:
                    return data['files']
                # If it's a dict with other keys, try to extract file-like values
                elif len(data) == 1:
                    # Single key dict - might be the file list
                    key = list(data.keys())[0]
                    if isinstance(data[key], list):
                        return data[key]
                # Return empty list for unknown dict formats
                return []
            elif isinstance(data, list):
                return data
            else:
                # For any other type, try to convert to list or return empty
                return []
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return []
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return []
        except Exception as e:
            click.echo(f"Unexpected error parsing response: {e}", err=True)
            return []
    
    def get_ttl_compare_list(self) -> List[str]:
        """
        Get list of available TTL comparison files.
        
        Returns:
            List of comparison filenames
        """
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl_compare")
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and 'file_list' in data:
                return data['file_list']
            else:
                return []
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return []
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return []
    
    def get_ttl_network(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get network data for a specific TTL file (JSON format).
        
        Args:
            filename: The TTL filename to retrieve
            
        Returns:
            Network data as JSON dict, or None on error
        """
        try:
            response = self.client.get(f"{self.base_url}/api/operations/ttl_network/{filename}")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return None
    
    def get_ttl_file(self, filename: str) -> Optional[str]:
        """
        Get raw TTL file content.
        
        Args:
            filename: The TTL filename to retrieve
            
        Returns:
            TTL file content as string, or None on error
        """
        try:
            headers = {"Accept": "text/turtle"}
            response = self.client.get(
                f"{self.base_url}/api/operations/ttl_file/{filename}",
                headers=headers
            )
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return None
    
    def check_health(self) -> bool:
        """
        Check if the API is healthy.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/api/operations/hello")
            response.raise_for_status()
            return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False
    
    def get_health_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed health information from the API.
        
        Returns:
            Health info as dict, or None on error
        """
        try:
            response = self.client.get(f"{self.base_url}/api/operations/hello")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            click.echo(f"Error connecting to Grasshopper API: {e}", err=True)
            return None
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP error {e.response.status_code}: {e.response.text}", err=True)
            return None
    
    def close(self):
        """Close the HTTP client"""
        self.client.close()
