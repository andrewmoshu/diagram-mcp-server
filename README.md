# Infrastructure Diagram MCP Server

[![PyPI version](https://badge.fury.io/py/infrastructure-diagram-mcp-server.svg)](https://pypi.org/project/infrastructure-diagram-mcp-server/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Model Context Protocol (MCP) server for Multi-Cloud Infrastructure Diagrams

This MCP server seamlessly creates [diagrams](https://diagrams.mingrammer.com/) using the Python diagrams package DSL. Generate professional infrastructure diagrams for **any cloud provider** (AWS, GCP, Azure), Kubernetes, on-premises, hybrid, and multi-cloud architectures using natural language with Claude Desktop or other MCP clients.

> **Note**: This is a derivative work based on [awslabs/aws-diagram-mcp-server](https://github.com/awslabs/mcp/tree/main/src/aws-diagram-mcp-server), extended with multi-cloud provider support and enhanced features.

## Prerequisites

1. Install [GraphViz](https://www.graphviz.org/) **with development headers** - Required for diagram generation and .drawio export
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or use `pip`
3. *(Optional)* Install [Helm](https://helm.sh/) - Required for full Helm chart parsing with `parse_helm_chart`

### Installing GraphViz

**macOS (Homebrew):**
```bash
brew install graphviz
```

**Ubuntu/Debian:**
```bash
sudo apt-get install graphviz graphviz-dev
```

**Windows (Chocolatey):**
```powershell
choco install graphviz
```
Or download from [graphviz.org](https://graphviz.org/download/)

### Installing Helm (Optional)

Helm is required for full template rendering with the `parse_helm_chart` tool. Without Helm, the parser will use a fallback mode with limited template support.

**macOS (Homebrew):**
```bash
brew install helm
```

**Ubuntu/Debian:**
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

**Windows (Chocolatey):**
```powershell
choco install kubernetes-helm
```

Or download from [helm.sh/docs/intro/install](https://helm.sh/docs/intro/install/)

## MCP Client Configuration

Configure the MCP server in your MCP client. The `CFLAGS` and `LDFLAGS` (or `INCLUDE` and `LIB` on Windows) environment variables are needed for the initial build of `pygraphviz`.

**Claude Desktop / Cursor on macOS** (`~/Library/Application Support/Claude/claude_desktop_config.json` or `~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "infrastructure-diagrams": {
      "command": "uvx",
      "args": ["infrastructure-diagram-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "CFLAGS": "-I/opt/homebrew/include",
        "LDFLAGS": "-L/opt/homebrew/lib"
      }
    }
  }
}
```

> **Note**: `/opt/homebrew` is the default Homebrew prefix on Apple Silicon Macs. For Intel Macs, use `/usr/local` instead.

**Linux** (e.g., `~/.config/claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "infrastructure-diagrams": {
      "command": "uvx",
      "args": ["infrastructure-diagram-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

> **Note**: On Linux, install `graphviz-dev` first (`sudo apt-get install graphviz graphviz-dev`), then no extra env vars are needed.

**Windows** (e.g., `%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "infrastructure-diagrams": {
      "command": "uvx",
      "args": ["infrastructure-diagram-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "INCLUDE": "C:\\Program Files\\Graphviz\\include",
        "LIB": "C:\\Program Files\\Graphviz\\lib"
      }
    }
  }
}
```

> **Note**: Adjust the Graphviz path if you installed it in a different location.

**Other MCP Clients** (e.g., Kiro - `~/.kiro/settings/mcp.json`):
```json
{
  "mcpServers": {
    "infrastructure-diagrams": {
      "command": "uvx",
      "args": ["infrastructure-diagram-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "CFLAGS": "-I/opt/homebrew/include",
        "LDFLAGS": "-L/opt/homebrew/lib"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

### Docker Installation

Build and run with Docker:

```bash
docker build -t infrastructure-diagram-mcp-server .
```

Then configure your MCP client:

```json
{
  "mcpServers": {
    "infrastructure-diagrams": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "infrastructure-diagram-mcp-server:latest"
      ]
    }
  }
}
```

## Features

The Infrastructure Diagram MCP Server provides the following capabilities:

1. **Multi-Provider Support**: Create diagrams for AWS, GCP, Azure, Kubernetes, on-premises, and hybrid/multi-cloud architectures
2. **2000+ Icons**: Access to icons across all major cloud providers and services
3. **Multiple Diagram Types**: Infrastructure architecture, sequence diagrams, flow charts, class diagrams, and more
4. **Rich Examples**: 27+ pre-built templates for AWS, GCP, Azure, K8s, hybrid, and multi-cloud patterns
5. **Customization**: Customize diagram appearance, layout, styling, colors, and connections
6. **Security**: Built-in code scanning to ensure secure diagram generation
7. **Seamless Display**: Diagrams appear inline in Claude Desktop with automatic rendering
8. **Flexible Output**: Save diagrams to PNG format in your workspace directory
9. **Editable Export**: Automatically generates .drawio files for editing in diagrams.net/draw.io
10. **IaC Parsing**: Parse Kubernetes manifests, Helm charts, and Terraform configurations to extract infrastructure information for diagram generation

## How to Use

Once configured in your MCP client (e.g., Claude Desktop), you can generate diagrams using natural language:

### Example Prompts:

**Discover Available Icons:**
```
List all available GCP infrastructure diagram icons
```

**Get Example Code:**
```
Show me examples of Azure microservices diagrams
```

**Generate Diagrams:**
```
Create a GCP data pipeline diagram showing Pub/Sub, Dataflow, and BigQuery
```

```
Generate an AWS serverless architecture with API Gateway, Lambda, and DynamoDB
```

```
Design a multi-cloud architecture spanning AWS, GCP, and Azure
```

**Parse Infrastructure-as-Code:**
```
Parse the Kubernetes manifests in ./k8s/ and show me the resources and relationships
```

```
Parse the Helm chart at ./charts/my-app/ and generate a diagram of the infrastructure
```

```
Parse the Terraform configuration in ./infrastructure/ and visualize the AWS resources
```

The server will automatically:
1. Find the appropriate icons from the 2000+ available
2. Generate Python code using the diagrams package
3. Create and display the PNG diagram inline
4. Save the diagram to your workspace directory
5. Generate an editable .drawio file for further customization

### Editable Diagrams with draw.io

Every diagram is automatically exported in two formats:
- **PNG**: For immediate viewing and sharing (displayed inline in Claude Desktop)
- **.drawio**: For editing in [diagrams.net](https://app.diagrams.net) or draw.io

The .drawio files allow you to:
- Modify individual components, colors, and styles
- Add additional notes, annotations, or documentation
- Reorganize layout and positioning
- Export to other formats (SVG, PDF, JPEG, etc.)
- Collaborate with team members using a familiar tool

Simply open the generated .drawio file in your browser at [diagrams.net](https://app.diagrams.net) - no installation required!

## What's New

This fork extends the original AWS Diagram MCP Server with:

- ✅ **Full Multi-Cloud Support**: GCP, Azure, Kubernetes, hybrid, and multi-cloud architectures
- ✅ **27+ Comprehensive Examples**: Ready-to-use templates across all providers
- ✅ **Complete Icon Coverage**: All 2000+ icons properly imported and available
- ✅ **Enhanced Display**: MCP ImageContent format for seamless inline rendering
- ✅ **Editable Export**: Automatic .drawio file generation for editing in diagrams.net/draw.io
- ✅ **IaC Parsing**: Parse Kubernetes manifests, Helm charts, and Terraform HCL to extract infrastructure
- ✅ **Bug Fixes**: Resolved double `.png` extension and read-only filesystem issues
- ✅ **Icon Corrections**: Fixed 28+ incorrect class names in examples

## Code Examples

Below are Python code examples showing the diagrams package syntax. When using with Claude Desktop, you can simply describe what you want in natural language!

### AWS Serverless Application
```python
from diagrams import Diagram
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import APIGateway

with Diagram("Serverless Application", show=False):
    api = APIGateway("API Gateway")
    function = Lambda("Function")
    database = Dynamodb("DynamoDB")

    api >> function >> database
```

### GCP Microservices
```python
from diagrams import Diagram, Cluster
from diagrams.gcp.compute import CloudRun
from diagrams.gcp.network import LoadBalancing
from diagrams.gcp.database import SQL

with Diagram("GCP Microservices", show=False):
    lb = LoadBalancing("load balancer")
    with Cluster("Services"):
        services = [CloudRun("api"), CloudRun("worker")]
    db = SQL("database")

    lb >> services >> db
```

### Azure Web App
```python
from diagrams import Diagram
from diagrams.azure.web import AppService
from diagrams.azure.database import SQLServer
from diagrams.azure.storage import BlobStorage

with Diagram("Azure Web App", show=False):
    AppService("web") >> SQLServer("db") >> BlobStorage("storage")
```

### Multi-Cloud Architecture
```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.gcp.compute import CloudRun
from diagrams.azure.web import AppService

with Diagram("Multi-Cloud Setup", show=False):
    with Cluster("AWS"):
        aws = EC2("primary")
    with Cluster("GCP"):
        gcp = CloudRun("backup")
    with Cluster("Azure"):
        azure = AppService("cdn")

    aws >> [gcp, azure]
```

## Example Diagrams Gallery

Below are complete architecture diagram examples generated using this MCP server. These demonstrate real-world patterns across different cloud providers and deployment scenarios.

### AWS Serverless Architecture

A production-ready serverless architecture using AWS services.

<p align="center">
  <img src="examples/aws-serverless-architecture.png" alt="AWS Serverless Architecture" width="600">
</p>

**Architecture Components:**
- Users connecting via HTTPS
- API Gateway as the entry point
- Multiple Lambda functions for compute
- DynamoDB for NoSQL database storage

---

### GCP Serverless Architecture

A serverless architecture on Google Cloud Platform with managed services.

<p align="center">
  <img src="examples/gcp-serverless-architecture.png" alt="GCP Serverless Architecture" width="600">
</p>

**Architecture Components:**
- Users connecting via HTTPS
- Load Balancer for traffic distribution
- Cloud Functions for serverless compute
- Firestore for document database

---

### Azure Serverless Architecture

A serverless architecture on Microsoft Azure featuring fully managed services.

<p align="center">
  <img src="examples/azure-serverless-architecture.png" alt="Azure Serverless Architecture" width="600">
</p>

**Architecture Components:**
- Users connecting via HTTPS
- Application Gateway for routing and load balancing
- Function Apps for serverless execution
- Cosmos DB for globally distributed database

---

### Kubernetes Architecture

A containerized application deployment on Kubernetes with full storage support.

<p align="center">
  <img src="examples/kubernetes-architecture.png" alt="Kubernetes Architecture" width="700">
</p>

**Architecture Components:**
- Ingress for external access and routing
- Service for internal load balancing
- Multiple Pods running containerized applications
- Persistent Volumes and Claims for stateful storage

---

### Multi-Cloud Architecture

A distributed architecture spanning AWS, GCP, and Azure with global DNS routing for high availability.

<p align="center">
  <img src="examples/multi-cloud-architecture.png" alt="Multi-Cloud Architecture" width="500">
</p>

**Architecture Components:**
- Global DNS (Route53) for intelligent traffic routing
- **AWS Region**: ELB → Lambda → DynamoDB
- **GCP Region**: Load Balancer → Cloud Functions → Firestore
- **Azure Region**: Load Balancer → Function Apps → Cosmos DB

---

### Hybrid Cloud Architecture

An enterprise hybrid cloud setup connecting on-premises infrastructure to AWS cloud.

<p align="center">
  <img src="examples/hybrid-cloud-architecture.png" alt="Hybrid Cloud Architecture" width="700">
</p>

**Architecture Components:**
- On-premises application server and PostgreSQL database
- VPN Gateway for secure encrypted connectivity
- AWS VPC with EC2 instances
- RDS for database replication and disaster recovery
- S3 for backup and archival storage

---

### GCP Foundation Organization Layer (from Terraform)

A comprehensive GCP organization-level infrastructure parsed from the [terraform-example-foundation](https://github.com/terraform-google-modules/terraform-example-foundation) using the `parse_terraform` tool.

<p align="center">
  <img src="examples/gcp_foundation_organization_layer.png" alt="GCP Foundation Organization Layer" width="800">
</p>

**Architecture Components:**
- Organization-level resources (VPC Service Controls, Resource Tags, Org Policies)
- Logging infrastructure (Cloud Logging, Pub/Sub, Storage, BigQuery sinks)
- Security services (Cloud KMS, Secret Manager, Security Command Center)
- CI/CD pipeline (Cloud Build, Source Repos, Artifact Registry)
- Network hub (Hub VPC, Cloud NAT, Cloud Router, Interconnects)
- Environment-specific shared VPCs (Dev, NonProd, Prod)

---

### Milvus Vector Database Architecture (from Helm Chart)

A production-ready Milvus deployment parsed from the official [milvus-helm](https://github.com/milvus-io/milvus-helm) chart using the `parse_helm_chart` tool.

<p align="center">
  <img src="examples/milvus-helm-architecture.png" alt="Milvus Helm Architecture" width="500">
</p>

**Architecture Components:**
- Client access through Milvus SDK
- Access Layer (Service, Deployment for milvus-proxy)
- Coordinator Layer (rootcoord, querycoord, indexcoord, datacoord)
- Worker Layer (querynode, indexnode, datanode)
- Dependencies (etcd for metadata, MinIO for object storage, Pulsar for message queue)

---

## IaC Parsing Tools

The server includes three tools for parsing Infrastructure-as-Code files:

### parse_k8s_manifest

Parse Kubernetes YAML manifests to extract resources and relationships.

```
Parse the K8s manifests in ./manifests/ and show me what's deployed
```

**Detects:**
- All K8s resource types (Deployments, Services, ConfigMaps, Secrets, PVCs, Ingress, etc.)
- Relationships: Service→Deployment, Deployment→ConfigMap/Secret/PVC, Ingress→Service
- Namespace grouping

### parse_helm_chart

Parse Helm charts with full `helm template` rendering or fallback mode when Helm CLI is unavailable.

> **Note**: For best results, [install Helm](#installing-helm-optional). Without Helm, the parser uses a fallback mode with limited Go template support.

```
Parse the Helm chart at ./charts/my-app/ with values from values-prod.yaml
```

**Features:**
- Full Helm template rendering (requires Helm CLI)
- Fallback mode for basic parsing without Helm
- Custom values file and inline values support
- Release name and namespace configuration

### parse_terraform

Parse Terraform HCL configurations to extract resources, data sources, modules, and relationships.

```
Parse the Terraform configuration in ./terraform/ and visualize the infrastructure
```

**Detects:**
- Resources from AWS, GCP, Azure, and Kubernetes providers
- Data sources and module references
- Explicit `depends_on` relationships
- Implicit references between resources

---

## Development

### Testing

The project includes a comprehensive test suite to ensure the functionality of the MCP server. The tests are organized by module and cover all aspects of the server's functionality.

To run the tests, use the provided script:

```bash
./run_tests.sh
```

This script will automatically install pytest and its dependencies if they're not already installed.

Or run pytest directly (if you have pytest installed):

```bash
pytest -xvs tests/
```

To run with coverage:

```bash
pytest --cov=infrastructure_diagram_mcp_server --cov-report=term-missing tests/
```

### Development Dependencies

To set up the development environment, install the development dependencies:

```bash
uv pip install -e ".[dev]"
```

This will install the required dependencies for development, including pytest, pytest-asyncio, and pytest-cov.

## Troubleshooting

### `pygraphviz` build error: `graphviz/cgraph.h not found`

This error occurs when the GraphViz development headers are not found during installation.

**macOS:**
```bash
# Make sure graphviz is installed
brew install graphviz

# Set compiler flags
export CFLAGS="-I$(brew --prefix graphviz)/include"
export LDFLAGS="-L$(brew --prefix graphviz)/lib"

# Then install
uvx infrastructure-diagram-mcp-server
```

**Linux:**
```bash
# Install development headers
sudo apt-get install graphviz graphviz-dev  # Ubuntu/Debian
sudo dnf install graphviz-devel              # Fedora/RHEL
```

**Windows:**
```powershell
# Install Graphviz with Chocolatey
choco install graphviz

# Set environment variables
$env:INCLUDE = "C:\Program Files\Graphviz\include"
$env:LIB = "C:\Program Files\Graphviz\lib"
```

### MCP server fails to start in Claude Desktop / Cursor

1. Make sure the `CFLAGS`/`LDFLAGS` (macOS) or `INCLUDE`/`LIB` (Windows) environment variables are set in your MCP config
2. Try clearing the uv cache: `rm -rf ~/.cache/uv`
3. Restart your MCP client

### Diagrams not displaying inline

Make sure you're using a recent version of Claude Desktop or Cursor that supports MCP ImageContent.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the [GitHub repository](https://github.com/andrewmoshu/diagram-mcp-server).

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

This is a derivative work based on [awslabs/aws-diagram-mcp-server](https://github.com/awslabs/mcp/tree/main/src/aws-diagram-mcp-server).
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

See [NOTICE](NOTICE) file for additional attribution information.

## Links

- **PyPI**: https://pypi.org/project/infrastructure-diagram-mcp-server/
- **GitHub**: https://github.com/andrewmoshu/diagram-mcp-server
- **Original Project**: https://github.com/awslabs/mcp/tree/main/src/aws-diagram-mcp-server
- **Diagrams Library**: https://diagrams.mingrammer.com/
