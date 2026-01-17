# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Modifications Copyright 2025 Andrii Moshurenko
# - Restructured as infrastructure-diagram-mcp-server
# - Updated MCP tool responses to return proper content types
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""infrastructure-diagram-mcp-server implementation.

This server provides tools to generate diagrams using the Python diagrams package.
It accepts Python code as a string and generates PNG diagrams without displaying them.
"""

from infrastructure_diagram_mcp_server.diagrams_tools import (
    generate_diagram,
    get_diagram_examples,
    list_diagram_icons,
)
from infrastructure_diagram_mcp_server.models import DiagramType
from infrastructure_diagram_mcp_server.parsers import (
    HelmParser,
    K8sParser,
    TerraformParser,
)
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent
from pydantic import Field
from typing import Optional


# Create the MCP server
mcp = FastMCP(
    'infrastructure-diagram-mcp-server',
    dependencies=[
        'pydantic',
        'diagrams',
    ],
    log_level='ERROR',
    instructions="""Use this server to generate professional infrastructure diagrams for any cloud provider, on-premises, or hybrid environments using the Python diagrams package.

WORKFLOW:
1. list_icons:
   - Discover all available icons in the diagrams package
   - Browse providers (AWS, GCP, Azure, K8s, on-prem, SaaS), services, and icons organized hierarchically
   - Find the exact import paths for icons you want to use
   - Supports filtering by provider and service for efficient discovery

2. get_diagram_examples:
   - Request example code for the diagram type you need
   - Available types: aws, gcp, azure, k8s, onprem, hybrid, multicloud, sequence, flow, class, custom, or all
   - Study the examples to understand the diagram package's syntax and capabilities
   - Use these examples as templates for your own diagrams
   - Each example demonstrates different features and diagram structures

3. generate_diagram:
   - Write Python code using the diagrams package DSL based on the examples
   - Submit your code to generate both PNG and editable .drawio files
   - Optionally specify a filename
   - The diagram is generated with show=False to prevent automatic display
   - The .drawio file can be opened for further editing
   - IMPORTANT: Always provide the workspace_dir parameter to save diagrams in the user's current directory

SUPPORTED INFRASTRUCTURE TYPES:
- AWS: EC2, Lambda, S3, RDS, EKS, and 200+ other services
- GCP: Cloud Functions, Cloud Run, BigQuery, GKE, Dataflow, and more
- Azure: App Service, Functions, AKS, Cosmos DB, Synapse, and more
- Kubernetes: Pods, Services, Deployments, StatefulSets, Ingress, and more
- On-premises: Servers, databases, networking, storage, proxies, and more
- Hybrid: Combinations of on-premises and cloud infrastructure
- Multi-cloud: Architectures spanning multiple cloud providers
- SaaS: GitHub, Slack, Datadog, and other third-party services
- Generic: Platform-agnostic compute, storage, network, and database components
- Sequence diagrams: Process and interaction flows
- Flow diagrams: Decision trees and workflows
- Class diagrams: Object relationships and inheritance
- Custom diagrams: Using custom nodes and icons from URLs

IMPORTANT:
- Always start with get_diagram_examples to understand the syntax for your target platform
- Use the list_icons tool to discover all available icons (filter by provider for efficiency)
- The code must include a Diagram() definition
- Diagrams are saved in multiple formats (PNG and .drawio) in a "generated-diagrams" subdirectory of the user's workspace by default
- The .drawio files can be edited in diagrams.net/draw.io for further customization
- If an absolute path is provided as filename, it will be used directly
- Diagram generation has a default timeout of 90 seconds
- For complex diagrams, consider breaking them into smaller components
- Use Clusters to organize and group related infrastructure components
- Use Edge() for custom connection styling (color, style, labels)""",
)


# Register tools
@mcp.tool(name='generate_diagram')
async def mcp_generate_diagram(
    code: str = Field(
        ...,
        description='Python code using the diagrams package DSL. The runtime already imports everything needed so you can start immediately using `with Diagram(`',
    ),
    filename: Optional[str] = Field(
        default=None,
        description='The filename to save the diagram to. If not provided, a random name will be generated.',
    ),
    timeout: int = Field(
        default=90,
        description='The timeout for diagram generation in seconds. Default is 90 seconds.',
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description="The user's current workspace directory. CRITICAL: Client must always send the current workspace directory when calling this tool! If provided, diagrams will be saved to a 'generated-diagrams' subdirectory.",
    ),
):
    """Generate a diagram from Python code using the diagrams package.

    This tool accepts Python code as a string that uses the diagrams package DSL
    and generates both PNG and editable .drawio files. The code is executed with
    show=False to prevent automatic display.

    USAGE INSTRUCTIONS:
    Never import. Start writing code immediately with `with Diagram(` and use the icons you found with list_icons.
    1. First use get_diagram_examples to understand the syntax and capabilities
    2. Then use list_icons to discover all available icons. These are the only icons you can work with.
    3. You MUST use icon names exactly as they are in the list_icons response, case-sensitive.
    4. Write your diagram code following python diagrams examples. Do not import any additional icons or packages, the runtime already imports everything needed.
    5. Submit your code to this tool to generate the diagram
    6. The tool returns paths to both the PNG image and editable .drawio file
    7. For complex diagrams, consider using Clusters to organize components
    8. Diagrams should start with a user or end device on the left, with data flowing to the right.

    CODE REQUIREMENTS:
    - Must include a Diagram() definition with appropriate parameters
    - Can use any of the supported diagram components (AWS, K8s, etc.)
    - Can include custom styling with Edge attributes (color, style)
    - Can use Cluster to group related components
    - Can use custom icons with the Custom class

    COMMON PATTERNS:
    - Basic: provider.service("label")
    - Connections: service1 >> service2 >> service3
    - Grouping: with Cluster("name"): [components]
    - Styling: service1 >> Edge(color="red", style="dashed") >> service2

    IMPORTANT FOR CLINE: Always send the current workspace directory when calling this tool!
    The workspace_dir parameter should be set to the directory where the user is currently working
    so that diagrams are saved to a location accessible to the user.

    Supported diagram types:
    - AWS architecture diagrams
    - Sequence diagrams
    - Flow diagrams
    - Class diagrams
    - Kubernetes diagrams
    - On-premises diagrams
    - Custom diagrams with custom nodes

    Returns:
        List containing:
        - TextContent with success message and paths to both PNG and .drawio files
        - ImageContent with the generated diagram (PNG) for immediate display

    OUTPUT FILES:
        - PNG diagram: For immediate viewing and sharing
        - .drawio file: Editable diagram that can be opened in diagrams.net/draw.io for further customization
    """
    # Special handling for test cases
    if code == 'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")':
        # For test_generate_diagram_with_defaults
        if filename is None and timeout == 90 and workspace_dir is None:
            result = await generate_diagram(code, None, 90, None)
        # For test_generate_diagram
        elif filename == 'test' and timeout == 60 and workspace_dir is not None:
            result = await generate_diagram(code, 'test', 60, workspace_dir)
        else:
            # Extract the actual values from the parameters
            code_value = code
            filename_value = None if filename is None else filename
            timeout_value = 90 if timeout is None else timeout
            workspace_dir_value = None if workspace_dir is None else workspace_dir

            result = await generate_diagram(
                code_value, filename_value, timeout_value, workspace_dir_value
            )
    else:
        # Extract the actual values from the parameters
        code_value = code
        filename_value = None if filename is None else filename
        timeout_value = 90 if timeout is None else timeout
        workspace_dir_value = None if workspace_dir is None else workspace_dir

        result = await generate_diagram(
            code_value, filename_value, timeout_value, workspace_dir_value
        )

    # Return structured MCP content with image
    if result.status == 'success' and result.image_data:
        message = f"{result.message}\n\nGenerated files:\n  • PNG diagram: {result.path}"
        if result.drawio_path:
            message += f"\n  • Editable .drawio file: {result.drawio_path}"

        return [
            TextContent(
                type="text",
                text=message
            ),
            ImageContent(
                type="image",
                data=result.image_data,
                mimeType=result.mime_type or "image/png"
            )
        ]
    else:
        # For errors, just return text
        return [
            TextContent(
                type="text",
                text=f"Error: {result.message}"
            )
        ]


@mcp.tool(name='get_diagram_examples')
async def mcp_get_diagram_examples(
    diagram_type: DiagramType = Field(
        default=DiagramType.ALL,
        description='Type of diagram example to return. Options: aws, gcp, azure, k8s, onprem, hybrid, multicloud, sequence, flow, class, custom, all',
    ),
):
    """Get example code for different types of diagrams.

    This tool provides ready-to-use example code for various diagram types across all major cloud providers,
    on-premises, hybrid, and multi-cloud architectures. Use these examples to understand the syntax and
    capabilities of the diagrams package before creating your own custom diagrams.

    USAGE INSTRUCTIONS:
    1. Select the diagram type you're interested in (or 'all' to see all examples)
    2. Study the returned examples to understand the structure and syntax
    3. Use these examples as templates for your own diagrams
    4. When ready, modify an example or write your own code and use generate_diagram

    EXAMPLE CATEGORIES:
    - aws: AWS cloud architecture diagrams (serverless, microservices, data pipelines, ML workflows)
    - gcp: Google Cloud Platform diagrams (Cloud Functions, BigQuery, Cloud Run, Vertex AI)
    - azure: Microsoft Azure diagrams (App Service, AKS, Synapse, Databricks)
    - k8s: Kubernetes architecture diagrams (pods, services, stateful sets, ingress)
    - onprem: On-premises infrastructure diagrams (servers, databases, networking)
    - hybrid: Hybrid cloud architectures (on-prem + cloud, VPN, disaster recovery)
    - multicloud: Multi-cloud architectures spanning AWS, GCP, and Azure
    - sequence: Process and interaction flow diagrams
    - flow: Decision trees and workflow diagrams
    - class: Object relationship and inheritance diagrams
    - custom: Custom diagrams with custom icons from URLs
    - all: All available examples across all categories

    Each example demonstrates different features of the diagrams package:
    - Basic connections between components
    - Grouping with Clusters
    - Advanced styling with Edge attributes
    - Different layout directions
    - Multiple component instances
    - Custom icons and nodes
    - Cross-provider architectures

    Parameters:
        diagram_type (str): Type of diagram example to return

    Returns:
        Dictionary with example code for the requested diagram type(s), organized by example name
    """
    result = get_diagram_examples(diagram_type)
    return result.model_dump()


@mcp.tool(name='list_icons')
async def mcp_list_diagram_icons(
    provider_filter: Optional[str] = Field(
        default=None, description='Filter icons by provider name (e.g., "aws", "gcp", "k8s")'
    ),
    service_filter: Optional[str] = Field(
        default=None,
        description='Filter icons by service name (e.g., "compute", "database", "network")',
    ),
):
    """List available icons from the diagrams package, with optional filtering.

    This tool dynamically inspects the diagrams package to find available
    providers, services, and icons that can be used in diagrams.

    USAGE INSTRUCTIONS:
    1. Call without filters to get a list of available providers
    2. Call with provider_filter to get all services and icons for that provider
    3. Call with both provider_filter and service_filter to get icons for a specific service

    Example workflow:
    - First call: list_icons() → Returns all available providers
    - Second call: list_icons(provider_filter="aws") → Returns all AWS services and icons
    - Third call: list_icons(provider_filter="aws", service_filter="compute") → Returns AWS compute icons

    This approach is more efficient than loading all icons at once, especially when you only need
    icons from specific providers or services.

    Returns:
        Dictionary with available providers, services, and icons organized hierarchically
    """
    # Extract the actual values from the parameters
    provider_filter_value = None if provider_filter is None else provider_filter
    service_filter_value = None if service_filter is None else service_filter

    result = list_diagram_icons(provider_filter_value, service_filter_value)
    return result.model_dump()


@mcp.tool(name='parse_k8s_manifest')
async def mcp_parse_k8s_manifest(
    input_source: str = Field(
        ...,
        description='File path to YAML file/directory, OR inline YAML content (multi-document supported with --- separators)',
    ),
):
    """Parse Kubernetes YAML manifests and extract resources and their relationships.

    This tool parses K8s manifests and returns structured data about resources and connections.
    After receiving the parsed data, use list_icons to find appropriate icons, then generate_diagram.

    SUPPORTED INPUTS:
    - Single YAML file path: "/path/to/deployment.yaml"
    - Directory path: "/path/to/k8s-manifests/" (parses all .yaml/.yml files)
    - Inline YAML content: Paste the YAML directly (supports multi-document with ---)

    SUPPORTED RESOURCES:
    - Workloads: Pod, Deployment, StatefulSet, DaemonSet, ReplicaSet, Job, CronJob
    - Networking: Service, Ingress, NetworkPolicy
    - Config: ConfigMap, Secret
    - Storage: PersistentVolume, PersistentVolumeClaim, StorageClass
    - RBAC: ServiceAccount, Role, RoleBinding, ClusterRole, ClusterRoleBinding
    - Cluster: Namespace, HPA, LimitRange, ResourceQuota

    RELATIONSHIP DETECTION:
    - Service -> Pod (via label selectors)
    - Deployment -> ReplicaSet -> Pod (via ownerReferences)
    - Pod -> ConfigMap/Secret (via volume mounts and envFrom)
    - Pod -> PVC (via volume claims)
    - Ingress -> Service (via backend rules)
    - HPA -> Deployment/StatefulSet (via scaleTargetRef)

    Returns:
        Structured data with resources, relationships, and namespaces.
        Use this data with list_icons and generate_diagram to create the visual diagram.
    """
    try:
        parser = K8sParser()
        parse_result = parser.parse(input_source)

        if parse_result.errors:
            return {
                'status': 'error',
                'errors': parse_result.errors,
            }

        if not parse_result.resources:
            return {
                'status': 'error',
                'errors': ['No Kubernetes resources found in the input.'],
            }

        # Convert resources to serializable format
        resources = []
        for r in parse_result.resources:
            resources.append({
                'kind': r.kind,
                'name': r.name,
                'namespace': r.namespace,
                'labels': r.labels,
                'annotations': {k: v for k, v in (r.annotations or {}).items() if not k.startswith('kubectl')},
            })

        # Convert relationships to serializable format
        relationships = []
        for rel in parse_result.relationships:
            relationships.append({
                'source': rel.source,
                'target': rel.target,
                'relationship_type': rel.relationship_type,
            })

        return {
            'status': 'success',
            'resource_count': len(resources),
            'relationship_count': len(relationships),
            'namespaces': list(parse_result.namespaces),
            'resources': resources,
            'relationships': relationships,
            'warnings': parse_result.warnings[:5] if parse_result.warnings else [],
            'next_steps': [
                "1. Use list_icons with provider_filter='k8s' to find appropriate icons",
                "2. Use generate_diagram to create the visual diagram with the resources above",
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'errors': [f'Error parsing K8s manifests: {str(e)}'],
        }


@mcp.tool(name='parse_helm_chart')
async def mcp_parse_helm_chart(
    chart_path: str = Field(
        ...,
        description='Path to Helm chart directory (containing Chart.yaml) or .tgz file',
    ),
    values_file: Optional[str] = Field(
        default=None,
        description='Path to values.yaml override file',
    ),
    values_inline: Optional[str] = Field(
        default=None,
        description='Inline YAML values to override chart defaults (as a YAML string)',
    ),
    release_name: str = Field(
        default='release',
        description='Helm release name for templating',
    ),
    namespace: str = Field(
        default='default',
        description='Target namespace for templating',
    ),
):
    """Parse a Helm chart and extract K8s resources and their relationships.

    This tool parses Helm charts and returns structured data about resources and connections.
    After receiving the parsed data, use list_icons to find appropriate icons, then generate_diagram.

    INPUTS:
    - chart_path: Directory containing Chart.yaml, or path to .tgz packaged chart
    - values_file: Optional values.yaml override file
    - values_inline: Optional inline YAML values as a string

    HELM CLI:
    - If `helm` is available on PATH, uses `helm template` for accurate rendering
    - If unavailable, falls back to basic Go template parsing (less accurate)

    Returns:
        Structured data with chart info, resources, relationships, and namespaces.
        Use this data with list_icons and generate_diagram to create the visual diagram.
    """
    try:
        import yaml as yaml_lib

        # Parse inline values if provided
        values_dict = None
        if values_inline:
            try:
                values_dict = yaml_lib.safe_load(values_inline)
            except yaml_lib.YAMLError as e:
                return {
                    'status': 'error',
                    'errors': [f'Invalid inline YAML values: {e}'],
                }

        parser = HelmParser()
        parse_result = parser.parse(
            input_source=chart_path,
            values_file=values_file,
            values_inline=values_dict,
            release_name=release_name,
            namespace=namespace,
        )

        if parse_result.errors:
            return {
                'status': 'error',
                'errors': parse_result.errors,
            }

        k8s_result = parse_result.k8s_result
        if not k8s_result.resources:
            return {
                'status': 'error',
                'errors': ['No Kubernetes resources found in the Helm chart.'],
            }

        # Chart info
        chart_info = None
        if parse_result.chart_info:
            chart_info = {
                'name': parse_result.chart_info.name,
                'version': parse_result.chart_info.version,
                'app_version': parse_result.chart_info.app_version,
                'description': parse_result.chart_info.description,
                'dependencies': parse_result.chart_info.dependencies,
            }

        # Convert resources to serializable format
        resources = []
        for r in k8s_result.resources:
            resources.append({
                'kind': r.kind,
                'name': r.name,
                'namespace': r.namespace,
                'labels': r.labels,
            })

        # Convert relationships to serializable format
        relationships = []
        for rel in k8s_result.relationships:
            relationships.append({
                'source': rel.source,
                'target': rel.target,
                'relationship_type': rel.relationship_type,
            })

        return {
            'status': 'success',
            'chart': chart_info,
            'rendered_with_helm': parse_result.rendered_with_helm,
            'resource_count': len(resources),
            'relationship_count': len(relationships),
            'namespaces': list(k8s_result.namespaces),
            'resources': resources,
            'relationships': relationships,
            'warnings': parse_result.warnings[:5] if parse_result.warnings else [],
            'next_steps': [
                "1. Use list_icons with provider_filter='k8s' to find appropriate icons",
                "2. Use generate_diagram to create the visual diagram with the resources above",
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'errors': [f'Error parsing Helm chart: {str(e)}'],
        }


@mcp.tool(name='parse_terraform')
async def mcp_parse_terraform(
    input_source: str = Field(
        ...,
        description='Path to .tf file, directory containing .tf files, OR inline HCL content',
    ),
):
    """Parse Terraform configurations and extract resources and their relationships.

    This tool parses Terraform HCL files and returns structured data about resources and connections.
    After receiving the parsed data, use list_icons to find appropriate icons, then generate_diagram.

    SUPPORTED INPUTS:
    - Single .tf file: "/path/to/main.tf"
    - Directory: "/path/to/terraform/" (parses all .tf files)
    - Inline HCL: Paste Terraform code directly

    SUPPORTED PROVIDERS:
    - AWS (aws_*): EC2, Lambda, S3, RDS, VPC, EKS, etc.
    - GCP (google_*): Compute Engine, Cloud Run, GKE, BigQuery, etc.
    - Azure (azurerm_*): VMs, AKS, Storage, SQL, etc.
    - Kubernetes (kubernetes_*): Deployments, Services, ConfigMaps, etc.

    RELATIONSHIP DETECTION:
    - Explicit: depends_on declarations
    - Implicit: References like aws_instance.web.id, var.vpc_id, module.vpc.output

    Returns:
        Structured data with providers, resources, modules, data sources, and relationships.
        Use this data with list_icons and generate_diagram to create the visual diagram.
    """
    try:
        parser = TerraformParser()
        parse_result = parser.parse(input_source)

        if parse_result.errors:
            return {
                'status': 'error',
                'errors': parse_result.errors,
            }

        if not parse_result.resources:
            return {
                'status': 'error',
                'errors': ['No Terraform resources found in the input.'],
            }

        # Convert resources to serializable format
        resources = []
        for r in parse_result.resources:
            resources.append({
                'type': r.resource_type,
                'name': r.name,
                'provider': r.provider.value,
                'module_path': r.module_path,
                'depends_on': r.depends_on,
            })

        # Convert data sources
        data_sources = []
        for d in parse_result.data_sources:
            data_sources.append({
                'type': d.data_type,
                'name': d.name,
                'provider': d.provider.value,
            })

        # Convert modules
        modules = []
        for m in parse_result.modules:
            modules.append({
                'name': m.name,
                'source': m.source,
            })

        # Convert relationships
        relationships = []
        for rel in parse_result.relationships:
            relationships.append({
                'source': rel[0],
                'target': rel[1],
            })

        # Get provider list for icon lookup hints
        providers_used = [p.value for p in parse_result.providers_used]

        return {
            'status': 'success',
            'providers': providers_used,
            'resource_count': len(resources),
            'module_count': len(modules),
            'data_source_count': len(data_sources),
            'relationship_count': len(relationships),
            'resources': resources,
            'data_sources': data_sources,
            'modules': modules,
            'relationships': relationships,
            'warnings': parse_result.warnings[:5] if parse_result.warnings else [],
            'next_steps': [
                f"1. Use list_icons with provider_filter for each provider: {providers_used}",
                "2. Use generate_diagram to create the visual diagram with the resources above",
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'errors': [f'Error parsing Terraform: {str(e)}'],
        }


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
