"""Kubernetes manifest parser and diagram generator.

This module provides functionality to parse Kubernetes YAML manifests and
generate Python diagrams DSL code that can be used to create architecture diagrams.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml

from infrastructure_diagram_mcp_server.parsers.icon_resolver import get_icon_resolver


@dataclass
class K8sResource:
    """Represents a parsed Kubernetes resource."""

    kind: str
    name: str
    namespace: str = 'default'
    api_version: str = 'v1'
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    spec: Dict[str, Any] = field(default_factory=dict)

    # Relationship tracking
    selector: Optional[Dict[str, str]] = None  # For Services, Deployments
    owner_refs: List[str] = field(default_factory=list)  # ownerReferences
    config_refs: List[str] = field(default_factory=list)  # ConfigMap/Secret refs
    pvc_refs: List[str] = field(default_factory=list)  # PVC references
    service_account: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        """Return namespace/kind/name identifier."""
        return f'{self.namespace}/{self.kind}/{self.name}'

    @property
    def simple_key(self) -> str:
        """Return namespace/name identifier for relationship matching."""
        return f'{self.namespace}/{self.name}'


@dataclass
class K8sRelationship:
    """Represents a relationship between K8s resources."""

    source: str  # qualified_name of source resource
    target: str  # qualified_name of target resource
    relationship_type: str  # "selects", "mounts", "owns", "exposes", etc.
    label: Optional[str] = None


@dataclass
class K8sParseResult:
    """Result of parsing K8s manifests."""

    resources: List[K8sResource] = field(default_factory=list)
    relationships: List[K8sRelationship] = field(default_factory=list)
    namespaces: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class K8sParser:
    """Parser for Kubernetes YAML manifests."""

    def __init__(self):
        """Initialize the K8s parser."""
        self.resources: List[K8sResource] = []
        self.relationships: List[K8sRelationship] = []
        self.namespaces: Set[str] = set()
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Index for relationship detection
        self._resources_by_qualified_name: Dict[str, K8sResource] = {}
        self._resources_by_kind_name: Dict[str, K8sResource] = {}
        self._resources_by_labels: Dict[str, List[K8sResource]] = {}

    def parse(self, input_source: Union[str, Path]) -> K8sParseResult:
        """Parse K8s manifests from file path, directory, or inline YAML content.

        Args:
            input_source: Can be:
                - File path (str or Path) to a .yaml/.yml file
                - Directory path containing YAML files
                - Inline YAML content string (multi-document supported)

        Returns:
            K8sParseResult with resources, relationships, and any errors
        """
        # Reset state
        self.resources = []
        self.relationships = []
        self.namespaces = set()
        self.errors = []
        self.warnings = []
        self._resources_by_qualified_name = {}
        self._resources_by_kind_name = {}
        self._resources_by_labels = {}

        # Detect input type
        if self._is_file_path(input_source):
            path = Path(input_source)
            if path.is_dir():
                self._parse_directory(path)
            elif path.exists():
                self._parse_file(path)
            else:
                self.errors.append(f'File not found: {path}')
        else:
            # Treat as inline YAML content
            self._parse_yaml_content(str(input_source))

        # Build relationships after all resources are parsed
        self._detect_relationships()

        return K8sParseResult(
            resources=self.resources,
            relationships=self.relationships,
            namespaces=self.namespaces,
            errors=self.errors,
            warnings=self.warnings,
        )

    def _is_file_path(self, source: Union[str, Path]) -> bool:
        """Determine if source is a file path or inline content."""
        if isinstance(source, Path):
            return True

        source_str = str(source)

        # If it contains newlines and typical YAML markers, it's likely content
        if '\n' in source_str and ('apiVersion:' in source_str or 'kind:' in source_str):
            return False

        # Check if it looks like a path
        path = Path(source_str)
        return path.exists() or source_str.endswith(('.yaml', '.yml'))

    def _parse_directory(self, directory: Path) -> None:
        """Parse all YAML files in a directory (recursive)."""
        yaml_files = list(directory.rglob('*.yaml')) + list(directory.rglob('*.yml'))

        if not yaml_files:
            self.warnings.append(f'No YAML files found in {directory}')
            return

        for yaml_file in sorted(yaml_files):
            self._parse_file(yaml_file)

    def _parse_file(self, file_path: Path) -> None:
        """Parse a single YAML file (supports multi-document)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._parse_yaml_content(content, source=str(file_path))
        except Exception as e:
            self.errors.append(f'Error reading {file_path}: {e}')

    def _parse_yaml_content(self, content: str, source: str = 'inline') -> None:
        """Parse YAML content, handling multi-document YAML."""
        try:
            # yaml.safe_load_all handles multi-document YAML (separated by ---)
            for doc in yaml.safe_load_all(content):
                if doc is None:
                    continue
                self._parse_document(doc, source)
        except yaml.YAMLError as e:
            self.errors.append(f'YAML parse error in {source}: {e}')

    def _parse_document(self, doc: Dict[str, Any], source: str) -> None:
        """Parse a single YAML document into a K8sResource."""
        if not isinstance(doc, dict):
            return

        # Handle List kind (e.g., from kubectl get -o yaml)
        if doc.get('kind') == 'List':
            for item in doc.get('items', []):
                self._parse_document(item, source)
            return

        # Validate required fields
        kind = doc.get('kind')
        api_version = doc.get('apiVersion')
        metadata = doc.get('metadata', {})

        if not kind or not api_version:
            self.warnings.append(f'Document in {source} missing kind or apiVersion, skipping')
            return

        if not isinstance(metadata, dict):
            metadata = {}

        name = metadata.get('name', 'unnamed')
        namespace = metadata.get('namespace', 'default')

        # Track namespace
        self.namespaces.add(namespace)

        # Extract spec and relationships
        spec = doc.get('spec', {})
        if not isinstance(spec, dict):
            spec = {}

        resource = K8sResource(
            kind=kind,
            name=name,
            namespace=namespace,
            api_version=api_version,
            labels=metadata.get('labels', {}) or {},
            annotations=metadata.get('annotations', {}) or {},
            spec=spec,
            selector=self._extract_selector(kind, spec),
            owner_refs=self._extract_owner_refs(metadata),
            config_refs=self._extract_config_refs(kind, spec),
            pvc_refs=self._extract_pvc_refs(kind, spec),
            service_account=self._extract_service_account(kind, spec),
        )

        self.resources.append(resource)
        self._index_resource(resource)

    def _extract_selector(self, kind: str, spec: Dict) -> Optional[Dict[str, str]]:
        """Extract selector from Service, Deployment, etc."""
        if kind == 'Service':
            selector = spec.get('selector', {})
            return selector if isinstance(selector, dict) else None

        if kind in ('Deployment', 'StatefulSet', 'DaemonSet', 'ReplicaSet', 'Job'):
            selector = spec.get('selector', {})
            if isinstance(selector, dict):
                match_labels = selector.get('matchLabels', {})
                return match_labels if isinstance(match_labels, dict) else None

        return None

    def _extract_owner_refs(self, metadata: Dict) -> List[str]:
        """Extract ownerReferences."""
        refs = []
        owner_refs = metadata.get('ownerReferences', [])
        if isinstance(owner_refs, list):
            for ref in owner_refs:
                if isinstance(ref, dict):
                    ref_kind = ref.get('kind', '')
                    ref_name = ref.get('name', '')
                    if ref_kind and ref_name:
                        refs.append(f'{ref_kind}/{ref_name}')
        return refs

    def _extract_config_refs(self, kind: str, spec: Dict) -> List[str]:
        """Extract ConfigMap and Secret references from volumes and envFrom."""
        refs = []

        # Get pod spec (either directly or from template)
        pod_spec = self._get_pod_spec(kind, spec)
        if not pod_spec:
            return refs

        # Volume references
        volumes = pod_spec.get('volumes', [])
        if isinstance(volumes, list):
            for volume in volumes:
                if not isinstance(volume, dict):
                    continue
                if 'configMap' in volume:
                    cm = volume['configMap']
                    if isinstance(cm, dict) and cm.get('name'):
                        refs.append(f"ConfigMap/{cm['name']}")
                if 'secret' in volume:
                    secret = volume['secret']
                    if isinstance(secret, dict) and secret.get('secretName'):
                        refs.append(f"Secret/{secret['secretName']}")

        # Container env references
        containers = pod_spec.get('containers', [])
        if isinstance(containers, list):
            for container in containers:
                if not isinstance(container, dict):
                    continue
                # envFrom references
                env_from = container.get('envFrom', [])
                if isinstance(env_from, list):
                    for ef in env_from:
                        if not isinstance(ef, dict):
                            continue
                        if 'configMapRef' in ef:
                            cmref = ef['configMapRef']
                            if isinstance(cmref, dict) and cmref.get('name'):
                                refs.append(f"ConfigMap/{cmref['name']}")
                        if 'secretRef' in ef:
                            sref = ef['secretRef']
                            if isinstance(sref, dict) and sref.get('name'):
                                refs.append(f"Secret/{sref['name']}")

                # env valueFrom references
                env = container.get('env', [])
                if isinstance(env, list):
                    for e in env:
                        if not isinstance(e, dict):
                            continue
                        value_from = e.get('valueFrom', {})
                        if isinstance(value_from, dict):
                            if 'configMapKeyRef' in value_from:
                                cmkr = value_from['configMapKeyRef']
                                if isinstance(cmkr, dict) and cmkr.get('name'):
                                    refs.append(f"ConfigMap/{cmkr['name']}")
                            if 'secretKeyRef' in value_from:
                                skr = value_from['secretKeyRef']
                                if isinstance(skr, dict) and skr.get('name'):
                                    refs.append(f"Secret/{skr['name']}")

        return list(set(refs))  # Remove duplicates

    def _extract_pvc_refs(self, kind: str, spec: Dict) -> List[str]:
        """Extract PVC references from volumes."""
        refs = []

        # Get pod spec
        pod_spec = self._get_pod_spec(kind, spec)
        if pod_spec:
            volumes = pod_spec.get('volumes', [])
            if isinstance(volumes, list):
                for volume in volumes:
                    if isinstance(volume, dict) and 'persistentVolumeClaim' in volume:
                        pvc = volume['persistentVolumeClaim']
                        if isinstance(pvc, dict) and pvc.get('claimName'):
                            refs.append(pvc['claimName'])

        # StatefulSet volumeClaimTemplates
        if kind == 'StatefulSet':
            vcts = spec.get('volumeClaimTemplates', [])
            if isinstance(vcts, list):
                for vct in vcts:
                    if isinstance(vct, dict):
                        vct_meta = vct.get('metadata', {})
                        if isinstance(vct_meta, dict) and vct_meta.get('name'):
                            refs.append(vct_meta['name'])

        return refs

    def _extract_service_account(self, kind: str, spec: Dict) -> Optional[str]:
        """Extract serviceAccountName."""
        pod_spec = self._get_pod_spec(kind, spec)
        if pod_spec:
            return pod_spec.get('serviceAccountName') or pod_spec.get('serviceAccount')
        return None

    def _get_pod_spec(self, kind: str, spec: Dict) -> Optional[Dict]:
        """Get the pod spec from a resource spec.

        For Pods, returns spec directly.
        For Deployments/etc, returns spec.template.spec.
        """
        if kind == 'Pod':
            return spec

        if kind in (
            'Deployment',
            'StatefulSet',
            'DaemonSet',
            'ReplicaSet',
            'Job',
        ):
            template = spec.get('template', {})
            if isinstance(template, dict):
                return template.get('spec', {})

        if kind == 'CronJob':
            job_template = spec.get('jobTemplate', {})
            if isinstance(job_template, dict):
                job_spec = job_template.get('spec', {})
                if isinstance(job_spec, dict):
                    template = job_spec.get('template', {})
                    if isinstance(template, dict):
                        return template.get('spec', {})

        return None

    def _index_resource(self, resource: K8sResource) -> None:
        """Index resource for relationship detection."""
        self._resources_by_qualified_name[resource.qualified_name] = resource

        # Index by kind/name within namespace
        kind_name_key = f'{resource.namespace}/{resource.kind}/{resource.name}'
        self._resources_by_kind_name[kind_name_key] = resource

        # Index by labels for selector matching
        for key, value in resource.labels.items():
            label_key = f'{resource.namespace}:{key}={value}'
            if label_key not in self._resources_by_labels:
                self._resources_by_labels[label_key] = []
            self._resources_by_labels[label_key].append(resource)

    def _detect_relationships(self) -> None:
        """Detect relationships between resources."""
        for resource in self.resources:
            # Service -> Pod (via selector)
            if resource.kind == 'Service' and resource.selector:
                self._match_selector_relationship(resource, 'exposes')

            # Deployment/StatefulSet -> Pod (via selector) - represents management
            if resource.kind in ('Deployment', 'StatefulSet', 'DaemonSet', 'ReplicaSet'):
                if resource.selector:
                    self._match_selector_relationship(resource, 'manages')

            # Ingress -> Service
            if resource.kind == 'Ingress':
                self._detect_ingress_relationships(resource)

            # ConfigMap/Secret references
            for ref in resource.config_refs:
                parts = ref.split('/')
                if len(parts) == 2:
                    ref_kind, ref_name = parts
                    target_key = f'{resource.namespace}/{ref_kind}/{ref_name}'
                    if target_key in self._resources_by_kind_name:
                        target = self._resources_by_kind_name[target_key]
                        self.relationships.append(
                            K8sRelationship(
                                source=resource.qualified_name,
                                target=target.qualified_name,
                                relationship_type='mounts',
                                label=ref_kind.lower(),
                            )
                        )

            # PVC references
            for pvc_name in resource.pvc_refs:
                target_key = f'{resource.namespace}/PersistentVolumeClaim/{pvc_name}'
                if target_key in self._resources_by_kind_name:
                    target = self._resources_by_kind_name[target_key]
                    self.relationships.append(
                        K8sRelationship(
                            source=resource.qualified_name,
                            target=target.qualified_name,
                            relationship_type='uses',
                        )
                    )

            # ServiceAccount references
            if resource.service_account:
                target_key = f'{resource.namespace}/ServiceAccount/{resource.service_account}'
                if target_key in self._resources_by_kind_name:
                    target = self._resources_by_kind_name[target_key]
                    self.relationships.append(
                        K8sRelationship(
                            source=resource.qualified_name,
                            target=target.qualified_name,
                            relationship_type='uses',
                            label='sa',
                        )
                    )

            # HPA -> Deployment/StatefulSet
            if resource.kind == 'HorizontalPodAutoscaler':
                self._detect_hpa_relationships(resource)

    def _match_selector_relationship(self, resource: K8sResource, rel_type: str) -> None:
        """Match resources by label selector."""
        if not resource.selector:
            return

        # Find resources that match ALL selector labels
        matching_resources: Set[str] = None

        for label_key, label_value in resource.selector.items():
            lookup_key = f'{resource.namespace}:{label_key}={label_value}'
            matching = self._resources_by_labels.get(lookup_key, [])
            matching_names = {r.qualified_name for r in matching}

            if matching_resources is None:
                matching_resources = matching_names
            else:
                matching_resources = matching_resources.intersection(matching_names)

        if not matching_resources:
            return

        for target_name in matching_resources:
            target = self._resources_by_qualified_name.get(target_name)
            if target and target.qualified_name != resource.qualified_name:
                # Don't create self-relationships
                # Don't connect Service to Deployment directly - Service selects Pods
                if resource.kind == 'Service' and target.kind not in ('Pod', 'Deployment', 'StatefulSet', 'DaemonSet'):
                    continue
                if resource.kind in ('Deployment', 'StatefulSet', 'DaemonSet', 'ReplicaSet'):
                    # These manage Pods, but we may not have Pod resources
                    pass

                self.relationships.append(
                    K8sRelationship(
                        source=resource.qualified_name,
                        target=target.qualified_name,
                        relationship_type=rel_type,
                    )
                )

    def _detect_ingress_relationships(self, ingress: K8sResource) -> None:
        """Detect Ingress -> Service relationships."""
        rules = ingress.spec.get('rules', [])
        if not isinstance(rules, list):
            return

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            http = rule.get('http', {})
            if not isinstance(http, dict):
                continue
            paths = http.get('paths', [])
            if not isinstance(paths, list):
                continue

            for path_item in paths:
                if not isinstance(path_item, dict):
                    continue
                backend = path_item.get('backend', {})
                if not isinstance(backend, dict):
                    continue

                # Handle both old and new Ingress API
                service_name = None
                service = backend.get('service', {})
                if isinstance(service, dict):
                    service_name = service.get('name')
                if not service_name:
                    service_name = backend.get('serviceName')

                if service_name:
                    target_key = f'{ingress.namespace}/Service/{service_name}'
                    if target_key in self._resources_by_kind_name:
                        target = self._resources_by_kind_name[target_key]
                        self.relationships.append(
                            K8sRelationship(
                                source=ingress.qualified_name,
                                target=target.qualified_name,
                                relationship_type='routes',
                            )
                        )

        # Also check default backend
        default_backend = ingress.spec.get('defaultBackend', {})
        if isinstance(default_backend, dict):
            service = default_backend.get('service', {})
            service_name = None
            if isinstance(service, dict):
                service_name = service.get('name')
            if not service_name:
                service_name = default_backend.get('serviceName')

            if service_name:
                target_key = f'{ingress.namespace}/Service/{service_name}'
                if target_key in self._resources_by_kind_name:
                    target = self._resources_by_kind_name[target_key]
                    self.relationships.append(
                        K8sRelationship(
                            source=ingress.qualified_name,
                            target=target.qualified_name,
                            relationship_type='routes',
                            label='default',
                        )
                    )

    def _detect_hpa_relationships(self, hpa: K8sResource) -> None:
        """Detect HPA -> ScaleTarget relationships."""
        scale_target = hpa.spec.get('scaleTargetRef', {})
        if not isinstance(scale_target, dict):
            return

        target_kind = scale_target.get('kind')
        target_name = scale_target.get('name')

        if target_kind and target_name:
            target_key = f'{hpa.namespace}/{target_kind}/{target_name}'
            if target_key in self._resources_by_kind_name:
                target = self._resources_by_kind_name[target_key]
                self.relationships.append(
                    K8sRelationship(
                        source=hpa.qualified_name,
                        target=target.qualified_name,
                        relationship_type='scales',
                    )
                )


class K8sDiagramGenerator:
    """Generate diagrams DSL code from K8s parse results."""

    def __init__(self, parse_result: K8sParseResult, diagram_name: str = 'Kubernetes Architecture'):
        """Initialize the diagram generator.

        Args:
            parse_result: The parsed K8s resources and relationships
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
        lines.append(f'with Diagram("{self.diagram_name}", show=False, direction="TB"):')

        # Group resources by namespace (use Clusters)
        namespaces = sorted(self.result.namespaces)

        if len(namespaces) == 1 and 'default' in namespaces:
            # Single default namespace - no cluster needed
            lines.extend(self._generate_resources_code(self.result.resources, indent=4))
        else:
            # Multiple namespaces - use Clusters
            for ns in namespaces:
                ns_resources = [r for r in self.result.resources if r.namespace == ns]
                if not ns_resources:
                    continue

                lines.append(f'    with Cluster("{ns}"):')
                lines.extend(self._generate_resources_code(ns_resources, indent=8))

        # Generate relationships
        rel_lines = self._generate_relationships_code(indent=4)
        if rel_lines:
            lines.append('')  # Add blank line before relationships
            lines.extend(rel_lines)

        return '\n'.join(lines)

    def _generate_resources_code(self, resources: List[K8sResource], indent: int) -> List[str]:
        """Generate code for resource declarations."""
        lines = []
        prefix = ' ' * indent

        # Group by kind for cleaner code
        by_kind: Dict[str, List[K8sResource]] = {}
        for r in resources:
            if r.kind not in by_kind:
                by_kind[r.kind] = []
            by_kind[r.kind].append(r)

        # Sort kinds for consistent output
        for kind in sorted(by_kind.keys()):
            kind_resources = by_kind[kind]

            for resource in kind_resources:
                var_name = self._make_var_name(resource)
                self._resource_vars[resource.qualified_name] = var_name

                # Get icon using resolver
                module, icon_class = self._resolver.resolve_k8s(kind)

                # Create the resource line
                lines.append(f'{prefix}{var_name} = {icon_class}("{resource.name}")')

        return lines

    def _generate_relationships_code(self, indent: int) -> List[str]:
        """Generate code for relationships between resources."""
        lines = []
        prefix = ' ' * indent

        # Deduplicate relationships
        seen_relationships: Set[tuple] = set()

        for rel in self.result.relationships:
            source_var = self._resource_vars.get(rel.source)
            target_var = self._resource_vars.get(rel.target)

            if not source_var or not target_var:
                continue

            rel_key = (source_var, target_var)
            if rel_key in seen_relationships:
                continue
            seen_relationships.add(rel_key)

            if rel.label:
                lines.append(f'{prefix}{source_var} >> Edge(label="{rel.label}") >> {target_var}')
            else:
                lines.append(f'{prefix}{source_var} >> {target_var}')

        return lines

    def _make_var_name(self, resource: K8sResource) -> str:
        """Create a valid Python variable name for a resource."""
        # Start with kind abbreviation + name
        kind_abbrev = self._get_kind_abbreviation(resource.kind)
        base = f'{kind_abbrev}_{resource.name}'

        # Sanitize: replace invalid chars with underscores
        base = re.sub(r'[^a-zA-Z0-9_]', '_', base)

        # Ensure it starts with a letter
        if base[0].isdigit():
            base = f'r_{base}'

        # Handle duplicates
        var_name = base
        counter = 1
        while var_name in self._used_var_names:
            var_name = f'{base}_{counter}'
            counter += 1

        self._used_var_names.add(var_name)
        return var_name

    def _get_kind_abbreviation(self, kind: str) -> str:
        """Get a short abbreviation for a K8s kind."""
        abbreviations = {
            'Deployment': 'deploy',
            'StatefulSet': 'sts',
            'DaemonSet': 'ds',
            'ReplicaSet': 'rs',
            'Service': 'svc',
            'Ingress': 'ing',
            'ConfigMap': 'cm',
            'Secret': 'secret',
            'PersistentVolumeClaim': 'pvc',
            'PersistentVolume': 'pv',
            'StorageClass': 'sc',
            'ServiceAccount': 'sa',
            'Role': 'role',
            'RoleBinding': 'rb',
            'ClusterRole': 'cr',
            'ClusterRoleBinding': 'crb',
            'HorizontalPodAutoscaler': 'hpa',
            'NetworkPolicy': 'netpol',
            'Namespace': 'ns',
            'Pod': 'pod',
            'Job': 'job',
            'CronJob': 'cj',
            'Node': 'node',
        }
        return abbreviations.get(kind, kind.lower()[:6])
