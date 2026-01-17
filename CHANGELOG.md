# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4] - 2026-01-17

### Added

- **Infrastructure-as-Code (IaC) Parsing Tools**: Three new MCP tools to parse IaC files and extract infrastructure information
  - `parse_k8s_manifest`: Parse Kubernetes YAML manifests to extract resources and relationships
  - `parse_helm_chart`: Parse Helm charts with full `helm template` rendering or fallback mode
  - `parse_terraform`: Parse Terraform HCL configurations to extract resources, data sources, and modules
- **Comprehensive Relationship Detection**:
  - K8s: Service→Deployment, Deployment→ConfigMap/Secret/PVC, Ingress→Service relationships
  - Terraform: Explicit `depends_on` and implicit reference relationships between resources
- **Multi-Provider Support for Terraform**: Automatic provider detection from resource type prefixes (aws_, google_, azurerm_, kubernetes_)
- **New Dependencies**: Added PyYAML for K8s/Helm parsing and python-hcl2 for Terraform HCL parsing
- **Comprehensive Test Suite**: 85+ new tests for all parsers covering basic parsing, relationship detection, edge cases

### Changed

- Parsers return structured data (resources, relationships, modules) rather than auto-generating diagrams
- This allows users to inspect the parsed infrastructure before diagram generation

### Documentation

- Added IaC Parsing section to README with usage examples
- Added example diagrams generated from real IaC files:
  - GCP Foundation Organization Layer (from Terraform)
  - Milvus Vector Database Architecture (from Helm chart)

## [0.0.3] - 2026-01-15

### Added

- **Editable Export**: Automatic .drawio file generation for every diagram
  - Diagrams are now exported in both PNG and DOT formats
  - DOT files are automatically converted to .drawio format using graphviz2drawio
  - Users can edit diagrams in diagrams.net/draw.io - no installation required
  - Full component-level editing: modify colors, styles, layouts, and add annotations
  - Export to additional formats (SVG, PDF, JPEG) from draw.io
- **graphviz2drawio Integration**: Added graphviz2drawio dependency for seamless DOT to .drawio conversion

### Changed

- Updated response messages to include both PNG and .drawio file paths with equal prominence
- Diagram generation now creates three files: .png, .dot, and .drawio

### Documentation

- Added "Editable Diagrams with draw.io" section to README
- Updated Features list to highlight .drawio export capability
- Added documentation on how to use .drawio files in diagrams.net
- Enhanced tool description to document .drawio file generation in workflow and return values

## [0.0.1] - 2026-01-15

### Added

- **Multi-Provider Support**: Full support for AWS, GCP, Azure, Kubernetes, on-premises, hybrid, and multi-cloud architectures
  - Added GCP, AZURE, HYBRID, and MULTICLOUD to DiagramType enum
- **27 Comprehensive Examples** across all providers:
  - 6 GCP examples (basic, data_pipeline, microservices, ml_pipeline, event_driven, iot_streaming)
  - 7 Azure examples (basic, serverless, microservices, data_platform, event_driven, ntier, iot_edge)
  - 3 Hybrid examples (aws_onprem, k8s_cloud, disaster_recovery)
  - 3 Multi-cloud examples (global_app, data_mesh, cicd)
- **Complete Module Import Coverage**: Added all GCP and Azure module imports to enable proper icon usage
  - 12 GCP modules (compute, network, database, analytics, ml, devtools, operations, iot, api, security, migration, storage)
  - 15 Azure modules (web, database, storage, compute, analytics, integration, devops, ml, iot, network, general, mobile, security, identity, migration)
- **MCP ImageContent Response Format**: Diagrams now return proper MCP ImageContent objects for seamless display
  - Returns structured ImageContent with type="image", data=base64, and mimeType="image/png"
  - Claude Desktop displays diagrams immediately without manual decoding
  - Also includes TextContent with file path and success message
- **2000+ Icons**: Access to icons across all major cloud providers and services
- **Security**: Built-in code scanning with Bandit to ensure secure diagram generation

### Fixed

- **Icon Name Corrections**: Fixed 28+ incorrect class names in examples to match actual diagrams package classes
  - GCP: CloudFunctions→Functions, CloudStorage→Storage, CloudRun→Run, GCPLoadBalancing→LoadBalancing, and more
  - Azure: AppService→AppServices, Functions→FunctionApps, EventHub→EventHubs, RedisCaches→CacheForRedis, and more
- **Double .png Extension Bug**: Fixed filename handling to prevent `.png.png` extensions
  - Strip `.png` extension before passing to diagrams library (which adds it automatically)
- **Read-Only File System Error**: Fixed OSError when diagrams library tries to create temp directories
  - Changes working directory to output_dir before executing diagram code
  - Ensures diagrams library can write temporary files during generation
- **Workspace Directory Handling**: Improved directory path validation and fallback logic for cross-platform compatibility

### Documentation

- Created comprehensive README with multi-cloud examples
- Added quick start examples for AWS, GCP, Azure, and multi-cloud architectures
