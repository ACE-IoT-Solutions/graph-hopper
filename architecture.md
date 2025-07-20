# Graph Hopper - Architecture & Development Roadmap

## 🏗️ **Project Architecture**

### **Overview**
Graph Hopper CLI is a Python CLI tool for retrieving and analyzing BACnet network graphs from the Grasshopper API. It supports both raw TTL (Turtle/RDF) files and processed JSON network data with comprehensive network topology validation.

### **Core Components**

```
src/graph_hopper/
├── __init__.py                 # Main CLI entry point and Click group
├── api/                        # Grasshopper API client
│   ├── __init__.py
│   └── client.py
├── commands/                   # CLI command implementations
│   ├── __init__.py
│   ├── base.py                 # Shared command functionality
│   ├── status.py               # API health check
│   ├── list_commands.py        # list-graphs, list-compares
│   ├── get_network.py          # get-network command
│   ├── download_recent.py      # download-recent command
│   ├── merge_graphs.py         # merge-graphs command
│   └── check_graph.py          # check-graph command
├── graph_checks/               # BACnet network analysis modules
│   ├── __init__.py
│   ├── utils.py                # Common utilities and formatting
│   ├── duplicate_devices.py    # Device ID conflict detection
│   ├── duplicate_networks.py   # Network number conflict detection
│   ├── duplicate_bbmds.py      # BBMD configuration validation
│   └── [future checks...]      # Additional validation modules
└── utils/                      # General utilities
    ├── __init__.py
    ├── url_parsing.py          # Host URL parsing and validation
    └── file_operations.py      # File handling utilities
```

### **Command Architecture**

**Current Commands (7 total):**
- `status` - API health check
- `list-graphs` / `list-compares` - File listings with optional JSON output
- `get-network <filename>` - Retrieve single file (TTL default, JSON optional)
- `download-recent` - Bulk download recent files
- `merge-graphs` - Combine multiple TTL files
- `check-graph` - Network topology validation and issue detection

### **API Integration Patterns**
- **TTL Raw Files**: Use `Accept: text/turtle` header on `/api/operations/ttl_file/{filename}`
- **JSON Network Data**: Use `/api/operations/ttl_network/{filename}` with `--json` flag
- **Host URL Parsing**: Flexible formats (localhost, IPs, URLs, IPv6) with intelligent defaults
- **Error Handling**: Comprehensive `httpx` error handling with user-friendly messages

### **Testing Strategy**
- **Test-First Development**: Implement tests before features
- **CLI Testing**: Use `click.testing.CliRunner` for command testing
- **Mock API**: Mock `GrasshopperClient` methods for isolated testing
- **Data-Driven**: TTL test files for each validation scenario
- **Current Coverage**: 75+ tests with >95% coverage

---

## 🚀 **BACnet Network Analysis Features Roadmap**

### **Current State**
- **5 implemented checks**: duplicate-device-id, duplicate-network, duplicate-router, duplicate-bbmd-warning, duplicate-bbmd-error
- **Test Coverage**: 75 total tests, 15 check-graph tests
- **Architecture**: Modular `graph_checks` package with individual check modules

### **Phase 1: Core Network Validation** (2-3 weeks)
**Priority**: High Impact, Low-Medium Complexity  
**Goal**: Detect fundamental network configuration issues

#### 1.1 Orphaned Devices Check (`orphaned-devices`)
- **Purpose**: Devices not connected to any network/subnet
- **Impact**: Critical - orphaned devices can't communicate
- **Complexity**: Low
- **Implementation**: 
  - Check devices without `ns1:device-on-network` or `ns1:device-on-subnet`
  - Validate device connectivity requirements
- **Test Cases**: Devices with missing network assignments

#### 1.2 Invalid Device Ranges Check (`invalid-device-ranges`)
- **Purpose**: Device IDs outside valid BACnet ranges (0-4194303)
- **Impact**: High - invalid IDs cause protocol errors
- **Complexity**: Low
- **Implementation**:
  - Validate `ns1:device-instance` values against BACnet spec
  - Check for negative values, over-range values
- **Test Cases**: Devices with IDs like -1, 4194304, non-numeric

#### 1.3 Device Address Conflicts Check (`device-address-conflicts`)
- **Purpose**: Same address assigned to multiple devices in network
- **Impact**: Critical - causes communication failures
- **Complexity**: Medium
- **Implementation**:
  - Group devices by network/subnet, check for duplicate `ns1:address` values
  - Handle different address formats (IP, BACnet network addresses)
- **Test Cases**: Multiple devices with "192.168.1.100" on same subnet

#### 1.4 Missing Vendor IDs Check (`missing-vendor-ids`)
- **Purpose**: Devices without vendor identification
- **Impact**: Medium - affects device management and troubleshooting
- **Complexity**: Low
- **Implementation**:
  - Check for missing `ns1:vendor-id` property on devices
  - Validate vendor ID format and known vendor registry
- **Test Cases**: Devices without vendor-id, invalid vendor formats

### **Phase 2: Network Topology Analysis** (3-4 weeks)
**Priority**: Medium-High Impact, Medium Complexity  
**Goal**: Ensure proper network connectivity and routing

#### 2.1 Unreachable Networks Check (`unreachable-networks`)
- **Purpose**: Networks without routing paths to other networks
- **Impact**: High - isolated network segments
- **Complexity**: Medium-High
- **Implementation**:
  - Build network topology graph from router connections
  - Use graph traversal to find isolated networks
  - Identify networks that should be connected but aren't
- **Test Cases**: Networks with no router connections, isolated segments

#### 2.2 Missing Routers Check (`missing-routers`)
- **Purpose**: Multi-network setups without proper routing infrastructure
- **Impact**: Medium - affects inter-network communication
- **Complexity**: Medium
- **Implementation**:
  - Detect when devices are on different networks but no router connects them
  - Identify networks that need routing but lack routers
- **Test Cases**: Devices on different networks with no routing path

#### 2.3 Subnet Mismatches Check (`subnet-mismatches`)
- **Purpose**: Device subnets don't match their network topology
- **Impact**: Medium - can cause routing issues
- **Complexity**: Medium
- **Implementation**:
  - Compare device subnet assignments with actual network topology
  - Validate IP addresses are within declared subnets
- **Test Cases**: Device with IP 192.168.1.100 on subnet 10.0.0.0/24

#### 2.4 Network Loops Check (`network-loops`)
- **Purpose**: Circular routing dependencies that can cause storms
- **Impact**: Critical - can bring down entire network
- **Complexity**: High
- **Implementation**:
  - Build directed graph of network routing relationships
  - Use cycle detection algorithms (DFS-based)
  - Identify potential broadcast storms
- **Test Cases**: Router A→Network X→Router B→Network Y→Router A

### **Phase 3: Performance & Scale Analysis** (2-3 weeks)
**Priority**: Medium Impact, Medium Complexity  
**Goal**: Optimize network performance and identify scalability issues

#### 3.1 Oversized Networks Check (`oversized-networks`)
- **Purpose**: Networks with too many devices (performance impact)
- **Impact**: Medium - affects network performance
- **Complexity**: Low-Medium
- **Implementation**:
  - Count devices per network/subnet
  - Apply BACnet best practice limits (typically 50-100 devices per segment)
  - Consider device types (some consume more bandwidth)
- **Test Cases**: Networks with 200+ devices, bandwidth-heavy device concentrations

#### 3.2 Broadcast Domain Analysis (`broadcast-domains`)
- **Purpose**: Inefficient broadcast domain configurations
- **Impact**: Medium - affects network efficiency
- **Complexity**: Medium
- **Implementation**:
  - Map broadcast domains across network topology
  - Identify oversized broadcast domains
  - Check for proper BBMD segmentation
- **Test Cases**: Single broadcast domain spanning many subnets

#### 3.3 Routing Inefficiencies Check (`routing-inefficiencies`)
- **Purpose**: Sub-optimal routing paths between networks
- **Impact**: Low-Medium - affects performance
- **Complexity**: High
- **Implementation**:
  - Calculate shortest paths between network segments
  - Identify unnecessarily long routing chains
  - Suggest routing optimizations
- **Test Cases**: 5-hop paths where 2-hop paths are possible

### **Phase 4: Data Quality & Completeness** (2 weeks)
**Priority**: Low-Medium Impact, Low-Medium Complexity  
**Goal**: Ensure data integrity and completeness

#### 4.1 Invalid Addresses Check (`invalid-addresses`)
- **Purpose**: Malformed or impossible network addresses
- **Impact**: Medium - causes connection failures
- **Complexity**: Medium
- **Implementation**:
  - Validate IP address formats, BACnet address formats
  - Check for impossible addresses (0.0.0.0, 255.255.255.255 in wrong contexts)
  - Validate port ranges and network ID formats
- **Test Cases**: "999.999.999.999", "not-an-address", invalid BACnet formats

#### 4.2 Incomplete Metadata Check (`incomplete-metadata`)
- **Purpose**: Missing required properties for proper network operation
- **Impact**: Medium - affects management and troubleshooting
- **Complexity**: Low-Medium
- **Implementation**:
  - Define required properties for each device type
  - Check for missing labels, descriptions, location info
  - Validate property completeness by device role
- **Test Cases**: Routers without subnet info, devices without labels

#### 4.3 Malformed URIs Check (`malformed-uris`)
- **Purpose**: Invalid BACnet URI formats
- **Impact**: Low-Medium - affects data consistency
- **Complexity**: Low
- **Implementation**:
  - Validate BACnet URI schemes and formats
  - Check for proper encoding and structure
  - Ensure URI consistency across references
- **Test Cases**: Invalid schemes, malformed device URIs

#### 4.4 Inconsistent Naming Check (`inconsistent-naming`)
- **Purpose**: Non-standard device/network naming conventions
- **Impact**: Low - affects management
- **Complexity**: Low-Medium
- **Implementation**:
  - Define naming conventions for networks, devices, subnets
  - Check for naming pattern compliance
  - Identify naming conflicts or ambiguities
- **Test Cases**: Mixed naming schemes, duplicate names

### **Phase 5: Advanced & Multi-Graph Analysis** (3-4 weeks)
**Priority**: Medium Impact, High Complexity  
**Goal**: Advanced analysis across multiple graphs and time

#### 5.1 Cross-Graph Conflicts Check (`cross-graph-conflicts`)
- **Purpose**: Issues spanning multiple TTL files
- **Impact**: Medium-High - affects multi-site deployments
- **Complexity**: High
- **Implementation**:
  - Load and correlate multiple TTL files
  - Detect device ID conflicts across sites
  - Identify network number overlaps between sites
- **Test Cases**: Same device ID in multiple buildings, network conflicts

#### 5.2 Temporal Drift Check (`temporal-drift`)
- **Purpose**: Configuration changes over time
- **Impact**: Medium - helps track network evolution
- **Complexity**: High
- **Implementation**:
  - Compare graphs with timestamps
  - Identify added/removed devices and networks
  - Track configuration parameter changes
- **Test Cases**: Device moves between networks, configuration rollbacks

#### 5.3 Consistency Violations Check (`consistency-violations`)
- **Purpose**: Same device represented differently across graphs
- **Impact**: Medium - data integrity
- **Complexity**: High
- **Implementation**:
  - Correlate devices across multiple graphs by ID
  - Check for conflicting properties (different vendor, address)
  - Validate referential integrity across files
- **Test Cases**: Device with different properties in different files

## 🏗️ **Implementation Strategy**

### **Development Workflow**
1. **Test-First Development**: Write test cases and test data before implementation
2. **Modular Architecture**: Each check gets its own module in `graph_checks/`
3. **Consistent Interface**: All checks return `(issues_list, affected_nodes)`
4. **CLI Integration**: Add new issue types to `--issue` choice list
5. **Documentation**: Update help text and examples

### **File Structure Pattern**
```
src/graph_hopper/graph_checks/
├── __init__.py                    # Export all checks
├── utils.py                       # Common utilities
├── orphaned_devices.py            # Phase 1.1
├── invalid_device_ranges.py       # Phase 1.2
├── device_address_conflicts.py    # Phase 1.3
├── missing_vendor_ids.py          # Phase 1.4
├── unreachable_networks.py        # Phase 2.1
├── missing_routers.py             # Phase 2.2
├── subnet_mismatches.py           # Phase 2.3
├── network_loops.py               # Phase 2.4
├── oversized_networks.py          # Phase 3.1
├── broadcast_domains.py           # Phase 3.2
├── routing_inefficiencies.py      # Phase 3.3
├── invalid_addresses.py           # Phase 4.1
├── incomplete_metadata.py         # Phase 4.2
├── malformed_uris.py             # Phase 4.3
├── inconsistent_naming.py         # Phase 4.4
├── cross_graph_conflicts.py       # Phase 5.1
├── temporal_drift.py              # Phase 5.2
└── consistency_violations.py      # Phase 5.3
```

### **Testing Strategy**
- **Test Data**: Create TTL files for each issue type in `tests/data/`
- **Unit Tests**: Each check module gets dedicated test class
- **Integration Tests**: CLI end-to-end testing for each issue type
- **Regression Tests**: Ensure new checks don't break existing functionality

### **CLI Evolution**
```bash
# Current
uv run graph-hopper check-graph file.ttl --issue all

# After Phase 1 (9 total issue types)
uv run graph-hopper check-graph file.ttl --issue orphaned-devices
uv run graph-hopper check-graph file.ttl --issue invalid-device-ranges

# After Phase 5 (22 total issue types)
uv run graph-hopper check-graph file.ttl --issue all
uv run graph-hopper check-graph file.ttl --issue network-topology  # Group checks
uv run graph-hopper check-graph file.ttl --issue data-quality      # Group checks
```

## 📊 **Success Metrics**
- **Issue Types**: 5 → 22 (340% increase)
- **Test Coverage**: Maintain >95% coverage across all modules
- **Performance**: <5 seconds analysis time for typical network graphs
- **Usability**: Clear, actionable error messages for network administrators

## 🔄 **Iterative Development**
Each phase should be:
1. **Planned** - Define requirements and test cases
2. **Implemented** - Code the check functions
3. **Tested** - Verify with comprehensive test suite  
4. **Integrated** - Add to CLI and update documentation
5. **Validated** - Test with real-world BACnet data

## 📚 **Development Guidelines**

### **Code Standards**
- **Linting**: Use `ruff` for code formatting and linting
- **Type Checking**: Use `pyrefly` for static type analysis
- **Testing**: Maintain >95% test coverage with `pytest`
- **Documentation**: Include docstrings for all public functions

### **BACnet Standards Compliance**
- Follow ASHRAE Standard 135 for BACnet protocol compliance
- Use standard namespace: `http://data.ashrae.org/bacnet/2020#`
- Validate against known BACnet device ranges and limits
- Reference official BACnet vendor registry for vendor IDs

### **Change Tracking**
- Update `agentic-sessions.md` after each feature completion
- Document breaking changes and migration paths
- Version bump according to semantic versioning
- Maintain backwards compatibility where possible

---

*This architecture document serves as the authoritative reference for Graph Hopper's structure, development roadmap, and implementation guidelines. Update as the project evolves.*
