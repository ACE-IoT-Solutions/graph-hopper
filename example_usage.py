#!/usr/bin/env python3
"""
Example usage script for the Graph Hopper CLI

This script demonstrates how to use the CLI programmatically
to retrieve graphs from a Grasshopper API instance.
"""

import subprocess
import json
import sys
from typing import List, Dict, Any


def run_command(cmd: List[str]) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_graphs_from_grasshopper(host_url: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve the top N graphs from a Grasshopper instance
    
    Args:
        host_url: Host URL of the Grasshopper instance (flexible format)
        limit: Number of graphs to retrieve (default: 5)
    
    Returns:
        List of graph information dictionaries including both TTL files and comparisons
    """
    # First check if the API is accessible
    print(f"Checking connection to Grasshopper at {host_url}...")
    
    status_cmd = ["uv", "run", "graph-hopper", "-h", host_url, "status"]
    exit_code, stdout, stderr = run_command(status_cmd)
    
    if exit_code != 0:
        print("Error: Cannot connect to Grasshopper API")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return []
    
    print("✓ Connected successfully!")
    print(stdout.strip())
    
    all_files = []
    
    # Get TTL network files
    print("\nRetrieving TTL network files...")
    ttl_cmd = [
        "uv", "run", "graph-hopper", 
        "-h", host_url,
        "list-graphs", 
        "--limit", str(limit),
        "--json"
    ]
    
    exit_code, stdout, stderr = run_command(ttl_cmd)
    if exit_code == 0:
        try:
            ttl_files = json.loads(stdout)
            all_files.extend(ttl_files)
            print(f"✓ Found {len(ttl_files)} TTL network files")
        except json.JSONDecodeError as e:
            print(f"Error parsing TTL files JSON: {e}")
    else:
        print("Error retrieving TTL files:")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
    
    # Get comparison files
    print("Retrieving comparison files...")
    compare_cmd = [
        "uv", "run", "graph-hopper", 
        "-h", host_url,
        "list-compares", 
        "--limit", str(limit),
        "--json"
    ]
    
    exit_code, stdout, stderr = run_command(compare_cmd)
    if exit_code == 0:
        try:
            compare_files = json.loads(stdout)
            all_files.extend(compare_files)
            print(f"✓ Found {len(compare_files)} comparison files")
        except json.JSONDecodeError as e:
            print(f"Error parsing comparison files JSON: {e}")
    else:
        print("Error retrieving comparison files:")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
    
    # Sort by filename and limit total results
    all_files.sort(key=lambda x: x['filename'])
    return all_files[:limit]


def main():
    """Main example function"""
    # Example usage - replace with your Grasshopper instance URL
    host_url = "192.168.1.100"  # Change this to your Grasshopper host
    
    if len(sys.argv) > 1:
        host_url = sys.argv[1]
    
    print("Graph Hopper CLI Example")
    print("========================")
    print(f"Target: {host_url}")
    print()
    
    # Get the top 5 graphs
    graphs = get_graphs_from_grasshopper(host_url, limit=5)
    
    if not graphs:
        print("No graphs found or connection failed.")
        return
    
    print(f"\nFound {len(graphs)} graphs:")
    print("-" * 50)
    
    for i, graph in enumerate(graphs, 1):
        print(f"{i}. {graph['filename']}")
        print(f"   Type: {graph['type']}")
        print(f"   Description: {graph['description']}")
        print()
    
    # Example: Get network data for the first graph (if any)
    if graphs:
        first_graph = graphs[0]['filename']
        print(f"Getting network data for '{first_graph}'...")
        
        network_cmd = [
            "uv", "run", "graph-hopper",
            "-h", host_url,
            "get-network", first_graph
        ]
        
        exit_code, stdout, stderr = run_command(network_cmd)
        
        if exit_code == 0:
            try:
                network_data = json.loads(stdout)
                print(f"✓ Retrieved network data ({len(stdout)} characters)")
                print(f"  Keys in network data: {list(network_data.keys()) if isinstance(network_data, dict) else 'Not a dict'}")
            except json.JSONDecodeError:
                print(f"✓ Retrieved network data (raw format, {len(stdout)} characters)")
        else:
            print("✗ Failed to get network data:")
            print(f"  stderr: {stderr}")


if __name__ == "__main__":
    main()
