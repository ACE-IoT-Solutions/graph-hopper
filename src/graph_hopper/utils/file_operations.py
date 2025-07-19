"""
File system utilities for Graph Hopper CLI.

This module provides functions for file operations, path handling, and TTL file processing.
"""

from pathlib import Path
from typing import List
import rdflib


def find_ttl_files(directory: Path, pattern: str = "*.ttl") -> List[Path]:
    """
    Find TTL files matching a pattern in a directory.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match (default: *.ttl)
        
    Returns:
        List of matching file paths
    """
    return list(directory.glob(pattern))


def merge_ttl_files(file_paths: List[Path]) -> tuple[rdflib.Graph, int, List[tuple[str, str]]]:
    """
    Merge multiple TTL files into a single RDF graph.
    
    Args:
        file_paths: List of TTL file paths to merge
        
    Returns:
        Tuple of (merged_graph, total_triples_processed, parse_errors)
        where parse_errors is a list of (filename, error_message) tuples
    """
    merged_graph = rdflib.Graph()
    total_triples = 0
    parse_errors = []
    
    for file_path in file_paths:
        try:
            file_graph = rdflib.Graph()
            file_graph.parse(str(file_path), format='turtle')
            
            # Add triples from this file to merged graph
            for triple in file_graph:
                merged_graph.add(triple)
            
            total_triples += len(file_graph)
            
        except Exception as e:
            parse_errors.append((file_path.name, str(e)))
    
    return merged_graph, total_triples, parse_errors


def save_ttl_graph(graph: rdflib.Graph, output_path: Path) -> None:
    """
    Save an RDF graph to a TTL file.
    
    Args:
        graph: RDF graph to save
        output_path: Path where to save the TTL file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output_path), format='turtle')
