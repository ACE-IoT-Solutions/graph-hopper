# Graph Hopper CLI

A command-line interface for retrieving graphs from the Grasshopper API, which manages BACnet device detection and TTL (Turtle) network files.

## Documentation

- **[Architecture & Roadmap](architecture.md)** - Project structure, development roadmap, and implementation guidelines
- **[Development Sessions](agentic-sessions.md)** - Detailed change history and development notes

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Make sure you have `uv` installed.

```bash
# Install dependencies
uv sync

# Or if you want to install the package
uv pip install -e .
```

## Usage

### Basic Commands

The CLI accepts flexible host formats for your Grasshopper instance. All commands follow this pattern:

```bash
uv run graph-hopper -h <HOST> [OPTIONS] COMMAND [ARGS]...
```

**Supported host formats:**
- Simple hostname: `localhost` → `http://localhost:8000`
- IP address: `192.168.1.100` → `http://192.168.1.100:8000`
- With port: `localhost:9000` → `http://localhost:9000`
- HTTP URL: `http://api.example.com` → `http://api.example.com:8000`
- HTTPS URL: `https://api.example.com` → `https://api.example.com:443`
- Full URL: `http://192.168.1.100:9000` → `http://192.168.1.100:9000`
- IPv6: `[::1]` → `http://[::1]:8000`

### Available Commands

#### 1. Check API Status

```bash
uv run graph-hopper -h 192.168.1.100 status
# or with full URL
uv run graph-hopper -h http://192.168.1.100:9000 status
```

This command verifies that the Grasshopper API is accessible and responding.

#### 2. List Available Graphs

```bash
# Get top 5 TTL network files (default)
uv run graph-hopper -h localhost list-graphs

# Get top 10 TTL network files
uv run graph-hopper -h https://api.example.com list-graphs --limit 10

# Output TTL files as JSON
uv run graph-hopper -h localhost list-graphs --json
```

#### 3. List Available Comparison Files

```bash
# Get top 5 comparison files (default)
uv run graph-hopper -h localhost list-compares

# Get top 10 comparison files
uv run graph-hopper -h 192.168.1.100:9000 list-compares --limit 10

# Output comparison files as JSON
uv run graph-hopper -h localhost list-compares --json
```

#### 4. Get Data for a Specific Graph

```bash
# Display raw TTL content to stdout (default)
uv run graph-hopper -h localhost get-network "my_network.ttl"

# Get network data as JSON instead
uv run graph-hopper -h localhost get-network "my_network.ttl" --json

# Save TTL content to a file
uv run graph-hopper -h http://192.168.1.100 get-network "my_network.ttl" --output network_data.ttl

# Save JSON network data to a file
uv run graph-hopper -h localhost get-network "my_network.ttl" --json --output network_data.json
```

#### 5. Download Recent Network Graphs

```bash
# Download 5 most recent TTL files (default)
uv run graph-hopper -h localhost download-recent

# Download 5 most recent as JSON network data instead
uv run graph-hopper -h localhost download-recent --json

# Download 10 most recent TTL files to custom directory
uv run graph-hopper -h 192.168.1.100:9000 download-recent --count 10 --output-dir /path/to/snapshots

# Download with verbose output
uv run graph-hopper -h localhost download-recent --verbose
```

#### 6. Merge Multiple TTL Files

```bash
# Merge all TTL files from a directory
uv run graph-hopper -h localhost merge-graphs --input-dir /path/to/ttl/files --output merged_network.ttl

# Merge with custom file pattern and verbose output
uv run graph-hopper -h localhost merge-graphs -i ./data/network_snapshots -p "network_*.ttl" -o combined.ttl --verbose

# Merge specific pattern of files
uv run graph-hopper -h localhost merge-graphs --input-dir ./snapshots --input-pattern "*_2024_*.ttl" --output yearly_summary.ttl
```

### Options

- `-h, --host`: Grasshopper instance URL (required) - supports various formats
- `--help`: Show help message

### Command-Specific Options

**list-graphs:**
- `-l, --limit`: Number of TTL files to retrieve (default: 5)
- `--json`: Output results as JSON

**list-compares:**
- `-l, --limit`: Number of comparison files to retrieve (default: 5)
- `--json`: Output results as JSON

**get-network:**
- `-o, --output`: Output file path (default: stdout)
- `--json`: Output network data as JSON instead of raw TTL

**download-recent:**
- `-c, --count`: Number of recent graphs to download (default: 5)
- `-d, --output-dir`: Output directory for downloaded files (default: data/network_snapshots)
- `--json`: Download network data as JSON instead of raw TTL files
- `-v, --verbose`: Show detailed progress information

**merge-graphs:**
- `-i, --input-dir`: Directory containing TTL files to merge (required)
- `-p, --input-pattern`: File pattern to match (default: *.ttl)
- `-o, --output`: Output file path for merged graph (required)
- `-v, --verbose`: Show verbose output including statistics

## Examples

### Example 1: Basic Usage

```bash
# Check if the API is accessible
uv run graph-hopper -h 192.168.1.100 status

# Get the top 5 TTL network files
uv run graph-hopper -h localhost list-graphs

# Get the top 5 comparison files
uv run graph-hopper -h localhost list-compares

# Download the 5 most recent TTL files
uv run graph-hopper -h localhost download-recent

# Get raw TTL data for a specific file
uv run graph-hopper -h https://api.grasshopper.local get-network "network_scan_2024.ttl"
```

### Example 2: Programmatic Usage

See `example_usage.py` for a complete example of how to use the CLI programmatically:

```bash
# Run the example (replace IP address as needed)
python example_usage.py 192.168.1.100
```

### Example 3: Merge Multiple TTL Files

```bash
# Download recent network snapshots
uv run graph-hopper -h localhost download-recent --count 10 --verbose

# Merge all downloaded TTL files into a single graph
uv run graph-hopper -h localhost merge-graphs \
    --input-dir data/network_snapshots \
    --output data/merged_network.ttl \
    --verbose

# Merge only files matching a specific pattern
uv run graph-hopper -h localhost merge-graphs \
    -i ./snapshots \
    -p "network_2024_*.ttl" \
    -o yearly_networks.ttl \
    --verbose
```

### Example 4: Data Pipeline

```bash
# Get list of available TTL files in JSON format
uv run graph-hopper -h localhost list-graphs --json > available_graphs.json

# Get list of available comparison files
uv run graph-hopper -h localhost list-compares --json > available_compares.json

# Get network data for the first few TTL files
for graph in $(jq -r '.[].filename' available_graphs.json | head -3); do
    echo "Retrieving $graph..."
    uv run graph-hopper -h localhost get-network "$graph" --output "data/$graph.json"
done
```

## API Endpoints Used

The CLI interacts with the following Grasshopper API endpoints:

- `GET /api/operations/hello` - Health check
- `GET /api/operations/ttl` - List TTL files
- `GET /api/operations/ttl_compare` - List TTL comparison files
- `GET /api/operations/ttl_network/{filename}` - Get network data for a TTL file

## Error Handling

The CLI provides helpful error messages for common issues:

- Network connectivity problems
- Invalid IP addresses or ports
- Missing files
- API errors

All errors are written to stderr, while data output goes to stdout.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff format
uv run ruff check
```

## Dependencies

- `click` - Command-line interface framework
- `httpx` - HTTP client for API requests

## License

[Add your license information here]
