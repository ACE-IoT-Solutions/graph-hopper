# Graph Hopper CLI Development Guide

## Project Architecture

**Graph Hopper CLI** is a Python CLI tool for retrieving BACnet network graphs from the Grasshopper API. It supports both raw TTL (Turtle/RDF) files and processed JSON network data.

**Core Components:**
- `src/graph_hopper/__init__.py` - Single-file CLI implementation using Click framework
- `context/openapi.json` - API specification (note: TTL endpoints support undocumented `text/turtle` Accept headers)
- `agentic-sessions.md` - Development history and change tracking

## Essential Development Workflows

### Environment Setup
```bash
# Python 3.13+ with uv package manager
uv sync                    # Install dependencies
uv run pytest tests/      # Run test suite (52+ tests)
uv run graph-hopper -h localhost --help  # CLI entry point
```

### API Integration Patterns
- **TTL Raw Files**: Use `Accept: text/turtle` header on `/api/operations/ttl_file/{filename}` (default behavior)
- **JSON Network Data**: Use `/api/operations/ttl_network/{filename}` with `--json` flag
- **Host URL Parsing**: `parse_host_url()` handles flexible formats (localhost, IPs, URLs, IPv6)

### Command Structure (5 core commands)
All commands require `-h <host>` parameter and support flexible URL formats:
- `status` - API health check
- `list-graphs` / `list-compares` - File listings with `--limit` and `--json` options  
- `get-network <filename>` - Retrieve single file (TTL default, `--json` for network data)
- `download-recent` - Bulk download recent files (TTL default, `--json` for network data)

## Critical Development Patterns

### Testing Strategy (Test-First Development)
- **Always implement tests before features** - provide test scenarios for user approval first
- Use `pytest` with `click.testing.CliRunner` for CLI testing
- Mock `GrasshopperClient` methods in tests
- Test files: `test_cli.py`, `test_url_parsing.py`, `test_download_recent.py`, `test_get_network_updated.py`

### API Response Handling
The TTL list endpoint returns inconsistent formats - implement defensive parsing:
```python
# Handle multiple possible response formats
if isinstance(data, dict):
    if 'file_list' in data: return data['file_list']
    elif 'files' in data: return data['files']
    elif len(data) == 1: return list(data.values())[0] if isinstance(list(data.values())[0], list) else []
```

### File Format Conventions
- **Default TTL mode**: Download raw turtle files with `.ttl` extension
- **JSON mode**: Process network data with `--json` flag, save as `.json`
- **Filename patterns**: `{base_name}_{timestamp}.{ttl|json}` for downloads

## Project-Specific Requirements

### Change Tracking
- **Update `agentic-sessions.md`** after each feature completion with summary of changes
- **Check session history** to avoid repeating work or breaking existing functionality

### API Specification Usage
- **Reference `context/openapi.json`** for endpoint documentation
- **TTL endpoints support more headers** than documented - use `text/turtle` Accept header for raw files
- **Grasshopper API** manages BACnet device detection and network topology

### URL Flexibility
The CLI accepts various host formats with intelligent defaults:
- `localhost` → `http://localhost:8000`
- `192.168.1.100:9000` → `http://192.168.1.100:9000`  
- `https://api.example.com` → `https://api.example.com:443`
- IPv6: `[::1]` → `http://[::1]:8000`

### Error Handling Patterns
- Use `click.echo(..., err=True)` for error messages
- Return appropriate exit codes (`sys.exit(1)` for failures)
- Handle `httpx.RequestError` and `httpx.HTTPStatusError` separately
- Provide verbose error details with `--verbose` flag where available