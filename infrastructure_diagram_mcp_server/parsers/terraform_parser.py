"""Terraform configuration parser and diagram generator.

This module provides functionality to parse Terraform HCL configurations and
generate Python diagrams DSL code that can be used to create architecture diagrams.
"""

import io
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import hcl2

from infrastructure_diagram_mcp_server.parsers.icon_resolver import get_icon_resolver


class TerraformProvider(str, Enum):
    """Supported Terraform providers."""

    AWS = 'aws'
    GCP = 'gcp'
    AZURE = 'azure'
    KUBERNETES = 'kubernetes'
    HELM = 'helm'
    DIGITALOCEAN = 'digitalocean'
    ALICLOUD = 'alibabacloud'
    OCI = 'oci'
    IBM = 'ibm'
    OPENSTACK = 'openstack'
    GENERIC = 'generic'


# Mapping from Terraform resource type prefix to diagrams provider
PROVIDER_PREFIX_MAP = {
    'aws_': TerraformProvider.AWS,
    'google_': TerraformProvider.GCP,
    'azurerm_': TerraformProvider.AZURE,
    'azuread_': TerraformProvider.AZURE,
    'kubernetes_': TerraformProvider.KUBERNETES,
    'helm_': TerraformProvider.HELM,
    'digitalocean_': TerraformProvider.DIGITALOCEAN,
    'alicloud_': TerraformProvider.ALICLOUD,
    'oci_': TerraformProvider.OCI,
    'ibm_': TerraformProvider.IBM,
    'openstack_': TerraformProvider.OPENSTACK,
}


@dataclass
class TerraformResource:
    """Represents a Terraform resource."""

    resource_type: str  # e.g., "aws_instance", "google_compute_instance"
    name: str  # resource name in Terraform
    provider: TerraformProvider
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Dependency tracking
    depends_on: List[str] = field(default_factory=list)  # Explicit depends_on
    references: List[str] = field(default_factory=list)  # Implicit refs

    # Module context
    module_path: Optional[str] = None  # e.g., "module.vpc"

    @property
    def qualified_name(self) -> str:
        """Full resource address."""
        if self.module_path:
            return f'{self.module_path}.{self.resource_type}.{self.name}'
        return f'{self.resource_type}.{self.name}'

    @property
    def short_name(self) -> str:
        """Short resource address without module path."""
        return f'{self.resource_type}.{self.name}'


@dataclass
class TerraformModule:
    """Represents a Terraform module call."""

    name: str
    source: str
    version: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TerraformVariable:
    """Represents a Terraform variable."""

    name: str
    var_type: Optional[str] = None
    default: Any = None
    description: Optional[str] = None


@dataclass
class TerraformDataSource:
    """Represents a Terraform data source."""

    data_type: str
    name: str
    provider: TerraformProvider
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Full data source address."""
        return f'data.{self.data_type}.{self.name}'


@dataclass
class TerraformParseResult:
    """Result of parsing Terraform configurations."""

    resources: List[TerraformResource] = field(default_factory=list)
    modules: List[TerraformModule] = field(default_factory=list)
    data_sources: List[TerraformDataSource] = field(default_factory=list)
    variables: List[TerraformVariable] = field(default_factory=list)
    providers_used: Set[TerraformProvider] = field(default_factory=set)
    relationships: List[Tuple[str, str, str]] = field(default_factory=list)  # (source, target, type)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TerraformParser:
    """Parser for Terraform HCL configurations."""

    def __init__(self):
        """Initialize the Terraform parser."""
        self.resources: List[TerraformResource] = []
        self.modules: List[TerraformModule] = []
        self.data_sources: List[TerraformDataSource] = []
        self.variables: List[TerraformVariable] = []
        self.providers_used: Set[TerraformProvider] = set()
        self.relationships: List[Tuple[str, str, str]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Index for reference resolution
        self._resource_index: Dict[str, TerraformResource] = {}

    def parse(self, input_source: Union[str, Path]) -> TerraformParseResult:
        """Parse Terraform configurations.

        Args:
            input_source: Can be:
                - File path to a .tf file
                - Directory path containing .tf files
                - Inline HCL content string

        Returns:
            TerraformParseResult with resources, modules, and relationships
        """
        # Reset state
        self.resources = []
        self.modules = []
        self.data_sources = []
        self.variables = []
        self.providers_used = set()
        self.relationships = []
        self.errors = []
        self.warnings = []
        self._resource_index = {}

        if self._is_file_path(input_source):
            path = Path(input_source)
            if path.is_dir():
                self._parse_directory(path)
            elif path.exists():
                self._parse_file(path)
            else:
                self.errors.append(f'File not found: {path}')
        else:
            self._parse_hcl_content(str(input_source))

        # Build indexes and detect relationships
        self._build_index()
        self._detect_relationships()

        return TerraformParseResult(
            resources=self.resources,
            modules=self.modules,
            data_sources=self.data_sources,
            variables=self.variables,
            providers_used=self.providers_used,
            relationships=self.relationships,
            errors=self.errors,
            warnings=self.warnings,
        )

    def _is_file_path(self, source: Union[str, Path]) -> bool:
        """Determine if source is a file path or inline content."""
        if isinstance(source, Path):
            return True

        source_str = str(source)

        # If it contains newlines and typical HCL markers, it's likely content
        if '\n' in source_str and ('resource' in source_str or 'module' in source_str or 'variable' in source_str):
            return False

        path = Path(source_str)
        return path.exists() or source_str.endswith('.tf')

    def _parse_directory(self, directory: Path) -> None:
        """Parse all .tf files in a directory (recursively)."""
        # Search recursively for .tf files
        tf_files = list(directory.glob('**/*.tf'))

        if not tf_files:
            self.warnings.append(f'No .tf files found in {directory} (searched recursively)')
            return

        for tf_file in sorted(tf_files):
            self._parse_file(tf_file)

    def _parse_file(self, file_path: Path) -> None:
        """Parse a single .tf file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._parse_hcl_content(content, source=str(file_path))
        except Exception as e:
            self.errors.append(f'Error reading {file_path}: {e}')

    def _parse_hcl_content(self, content: str, source: str = 'inline') -> None:
        """Parse HCL content string."""
        try:
            data = hcl2.load(io.StringIO(content))
            self._process_terraform_dict(data, source)
        except Exception as e:
            self.errors.append(f'HCL parse error in {source}: {e}')

    def _process_terraform_dict(self, data: Dict, source: str) -> None:
        """Process parsed Terraform configuration dictionary."""
        if not isinstance(data, dict):
            return

        # Process resources
        resources = data.get('resource', [])
        if isinstance(resources, list):
            for resource_block in resources:
                if isinstance(resource_block, dict):
                    for resource_type, resources_of_type in resource_block.items():
                        if isinstance(resources_of_type, dict):
                            for resource_name, config in resources_of_type.items():
                                self._process_resource(resource_type, resource_name, config)

        # Process data sources
        data_sources = data.get('data', [])
        if isinstance(data_sources, list):
            for data_block in data_sources:
                if isinstance(data_block, dict):
                    for data_type, data_items in data_block.items():
                        if isinstance(data_items, dict):
                            for data_name, config in data_items.items():
                                self._process_data_source(data_type, data_name, config)

        # Process modules
        modules = data.get('module', [])
        if isinstance(modules, list):
            for module_block in modules:
                if isinstance(module_block, dict):
                    for module_name, config in module_block.items():
                        self._process_module(module_name, config)

        # Process variables
        variables = data.get('variable', [])
        if isinstance(variables, list):
            for var_block in variables:
                if isinstance(var_block, dict):
                    for var_name, config in var_block.items():
                        self._process_variable(var_name, config)

    def _process_resource(self, resource_type: str, name: str, config: Any) -> None:
        """Process a single resource block."""
        if not isinstance(config, dict):
            config = {}

        provider = self._detect_provider(resource_type)
        self.providers_used.add(provider)

        # Extract dependencies
        depends_on = []
        raw_depends = config.pop('depends_on', [])
        if isinstance(raw_depends, list):
            for dep in raw_depends:
                if isinstance(dep, str):
                    depends_on.append(dep)

        # Find references in attribute values
        references = self._extract_references(config)

        resource = TerraformResource(
            resource_type=resource_type,
            name=name,
            provider=provider,
            attributes=config,
            depends_on=depends_on,
            references=references,
        )

        self.resources.append(resource)

    def _process_data_source(self, data_type: str, name: str, config: Any) -> None:
        """Process a data source block."""
        if not isinstance(config, dict):
            config = {}

        provider = self._detect_provider(data_type)
        self.providers_used.add(provider)

        data_source = TerraformDataSource(
            data_type=data_type,
            name=name,
            provider=provider,
            attributes=config,
        )

        self.data_sources.append(data_source)

    def _process_module(self, name: str, config: Any) -> None:
        """Process a module block."""
        if not isinstance(config, dict):
            config = {}

        module = TerraformModule(
            name=name,
            source=config.get('source', ''),
            version=config.get('version'),
            variables={k: v for k, v in config.items() if k not in ('source', 'version', 'providers')},
        )

        self.modules.append(module)

    def _process_variable(self, name: str, config: Any) -> None:
        """Process a variable block."""
        if not isinstance(config, dict):
            config = {}

        var = TerraformVariable(
            name=name,
            var_type=str(config.get('type')) if config.get('type') else None,
            default=config.get('default'),
            description=config.get('description'),
        )

        self.variables.append(var)

    def _detect_provider(self, resource_type: str) -> TerraformProvider:
        """Detect provider from resource type prefix."""
        for prefix, provider in PROVIDER_PREFIX_MAP.items():
            if resource_type.startswith(prefix):
                return provider
        return TerraformProvider.GENERIC

    def _extract_references(self, config: Any, refs: Optional[List[str]] = None) -> List[str]:
        """Extract resource references from configuration values."""
        if refs is None:
            refs = []

        if isinstance(config, str):
            # Match patterns like: aws_instance.web, module.vpc.vpc_id, data.aws_ami.ubuntu
            patterns = [
                r'\b([a-z_]+\.[a-z0-9_-]+)(?:\.[a-z0-9_-]+)*',  # resource.name or resource.name.attr
                r'\b(module\.[a-z0-9_-]+)(?:\.[a-z0-9_-]+)*',  # module.name.output
                r'\b(data\.[a-z_]+\.[a-z0-9_-]+)(?:\.[a-z0-9_-]+)*',  # data.type.name.attr
            ]
            for pattern in patterns:
                matches = re.findall(pattern, config)
                for match in matches:
                    # Filter out false positives (like "http.port" or "default.name")
                    if '.' in match:
                        first_part = match.split('.')[0]
                        # Check if it looks like a resource type
                        if '_' in first_part or first_part in ('module', 'data', 'var', 'local'):
                            refs.append(match)

        elif isinstance(config, dict):
            for value in config.values():
                self._extract_references(value, refs)

        elif isinstance(config, list):
            for item in config:
                self._extract_references(item, refs)

        return list(set(refs))

    def _build_index(self) -> None:
        """Build index of resources for reference resolution."""
        for resource in self.resources:
            self._resource_index[resource.qualified_name] = resource
            self._resource_index[resource.short_name] = resource

    def _detect_relationships(self) -> None:
        """Detect relationships between resources."""
        for resource in self.resources:
            # Explicit depends_on
            for dep in resource.depends_on:
                if dep in self._resource_index:
                    self.relationships.append((resource.qualified_name, dep, 'depends_on'))

            # Implicit references
            for ref in resource.references:
                # Check if reference matches a known resource
                if ref in self._resource_index:
                    self.relationships.append((resource.qualified_name, ref, 'references'))
                else:
                    # Try to find partial match
                    for res_name in self._resource_index:
                        if ref in res_name or res_name.endswith(ref):
                            self.relationships.append((resource.qualified_name, res_name, 'references'))
                            break


class TerraformDiagramGenerator:
    """Generate diagrams DSL code from Terraform parse results."""

    def __init__(self, parse_result: TerraformParseResult, diagram_name: str = 'Terraform Infrastructure'):
        """Initialize the diagram generator.

        Args:
            parse_result: The parsed Terraform resources and relationships
            diagram_name: Name for the generated diagram
        """
        self.result = parse_result
        self.diagram_name = diagram_name
        self._resource_vars: Dict[str, str] = {}  # qualified_name -> variable name
        self._used_var_names: Set[str] = set()
        self._resolver = get_icon_resolver()

    def generate(self) -> str:
        """Generate Python diagrams DSL code.

        Returns:
            Python code string that can be executed to generate a diagram
        """
        lines = []

        # Diagram header
        lines.append(f'with Diagram("{self.diagram_name}", show=False, direction="LR"):')

        # Choose grouping strategy
        if self.result.modules:
            # Use modules as clusters
            lines.extend(self._generate_with_modules(indent=4))
        elif len(self.result.providers_used) > 1:
            # Multi-provider: group by provider
            lines.extend(self._generate_by_provider(indent=4))
        else:
            # Single provider: flat structure
            lines.extend(self._generate_flat(indent=4))

        # Generate relationships
        rel_lines = self._generate_relationships(indent=4)
        if rel_lines:
            lines.append('')  # Add blank line before relationships
            lines.extend(rel_lines)

        return '\n'.join(lines)

    def _generate_with_modules(self, indent: int) -> List[str]:
        """Generate code with module-based clusters."""
        lines = []
        prefix = ' ' * indent

        # Resources not in modules (root level)
        root_resources = [r for r in self.result.resources if not r.module_path]
        if root_resources:
            lines.append(f'{prefix}with Cluster("Root"):')
            lines.extend(self._generate_resources(root_resources, indent + 4))

        # Module clusters
        for module in self.result.modules:
            lines.append(f'{prefix}with Cluster("module.{module.name}"):')
            module_resources = [
                r for r in self.result.resources if r.module_path == f'module.{module.name}'
            ]
            if module_resources:
                lines.extend(self._generate_resources(module_resources, indent + 4))
            else:
                # Placeholder comment for module with no resources parsed
                lines.append(f'{" " * (indent + 4)}# Module: {module.source}')
                lines.append(f'{" " * (indent + 4)}pass')

        return lines

    def _generate_by_provider(self, indent: int) -> List[str]:
        """Generate code grouped by provider."""
        lines = []
        prefix = ' ' * indent

        # Sort providers for consistent output
        for provider in sorted(self.result.providers_used, key=lambda p: p.value):
            provider_resources = [r for r in self.result.resources if r.provider == provider]
            if provider_resources:
                cluster_name = self._get_provider_display_name(provider)
                lines.append(f'{prefix}with Cluster("{cluster_name}"):')
                lines.extend(self._generate_resources(provider_resources, indent + 4))

        return lines

    def _generate_flat(self, indent: int) -> List[str]:
        """Generate flat structure without clusters."""
        return self._generate_resources(self.result.resources, indent)

    def _generate_resources(self, resources: List[TerraformResource], indent: int) -> List[str]:
        """Generate resource declarations."""
        lines = []
        prefix = ' ' * indent

        for resource in resources:
            var_name = self._make_var_name(resource)
            self._resource_vars[resource.qualified_name] = var_name
            self._resource_vars[resource.short_name] = var_name

            # Get icon using resolver
            module, icon_class = self._resolver.resolve_terraform(resource.resource_type)

            # Create label (shortened resource type + name)
            label = f'{resource.resource_type}.{resource.name}'
            if len(label) > 40:
                # Truncate for readability
                label = f'...{label[-37:]}'

            lines.append(f'{prefix}{var_name} = {icon_class}("{resource.name}")')

        return lines

    def _generate_relationships(self, indent: int) -> List[str]:
        """Generate relationship code."""
        lines = []
        prefix = ' ' * indent

        # Deduplicate relationships
        seen_relationships: Set[Tuple[str, str]] = set()

        for source, target, rel_type in self.result.relationships:
            source_var = self._resource_vars.get(source)
            target_var = self._resource_vars.get(target)

            if not source_var or not target_var:
                continue

            # Normalize relationship direction
            rel_key = (source_var, target_var)
            if rel_key in seen_relationships:
                continue
            seen_relationships.add(rel_key)

            if rel_type == 'depends_on':
                # depends_on means target must exist before source
                lines.append(f'{prefix}{target_var} >> {source_var}')
            else:
                # references means source uses target
                lines.append(f'{prefix}{source_var} >> {target_var}')

        return lines

    def _make_var_name(self, resource: TerraformResource) -> str:
        """Create valid Python variable name."""
        # Use resource type and name
        base = f'{resource.resource_type}_{resource.name}'

        # Sanitize: replace invalid chars with underscores
        base = re.sub(r'[^a-zA-Z0-9_]', '_', base)

        # Ensure it starts with a letter
        if base[0].isdigit():
            base = f'r_{base}'

        # Truncate if too long
        if len(base) > 50:
            base = base[:50]

        # Handle duplicates
        var_name = base
        counter = 1
        while var_name in self._used_var_names:
            var_name = f'{base}_{counter}'
            counter += 1

        self._used_var_names.add(var_name)
        return var_name

    def _get_provider_display_name(self, provider: TerraformProvider) -> str:
        """Get display name for provider cluster."""
        display_names = {
            TerraformProvider.AWS: 'AWS',
            TerraformProvider.GCP: 'Google Cloud',
            TerraformProvider.AZURE: 'Azure',
            TerraformProvider.KUBERNETES: 'Kubernetes',
            TerraformProvider.HELM: 'Helm',
            TerraformProvider.DIGITALOCEAN: 'DigitalOcean',
            TerraformProvider.ALICLOUD: 'Alibaba Cloud',
            TerraformProvider.OCI: 'Oracle Cloud',
            TerraformProvider.IBM: 'IBM Cloud',
            TerraformProvider.OPENSTACK: 'OpenStack',
            TerraformProvider.GENERIC: 'Other',
        }
        return display_names.get(provider, provider.value)
