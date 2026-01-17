"""Helm chart parser and diagram generator.

This module provides functionality to parse Helm charts by rendering them
with `helm template` (if available) or by parsing raw templates as a fallback.
The resulting Kubernetes manifests are then parsed using the K8sParser.
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from infrastructure_diagram_mcp_server.parsers.k8s_parser import K8sParseResult, K8sParser


@dataclass
class HelmChartInfo:
    """Metadata about a Helm chart."""

    name: str
    version: str
    app_version: Optional[str] = None
    description: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class HelmParseResult:
    """Result of parsing a Helm chart."""

    chart_info: Optional[HelmChartInfo]
    k8s_result: K8sParseResult
    rendered_with_helm: bool  # True if helm template was used
    values_used: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class HelmParser:
    """Parser for Helm charts - renders to K8s manifests then parses."""

    def __init__(self):
        """Initialize the Helm parser."""
        self.helm_available = self._check_helm_cli()
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def _check_helm_cli(self) -> bool:
        """Check if helm CLI is available."""
        try:
            result = subprocess.run(
                ['helm', 'version', '--short'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def parse(
        self,
        input_source: Union[str, Path],
        values_file: Optional[Union[str, Path]] = None,
        values_inline: Optional[Dict[str, Any]] = None,
        release_name: str = 'release',
        namespace: str = 'default',
    ) -> HelmParseResult:
        """Parse a Helm chart and extract K8s resources.

        Args:
            input_source: Can be:
                - Directory path to a Helm chart (containing Chart.yaml)
                - Path to a .tgz packaged chart
            values_file: Optional path to values.yaml override
            values_inline: Optional inline values dict
            release_name: Helm release name (used in templating)
            namespace: Target namespace for templating

        Returns:
            HelmParseResult with chart info and parsed K8s resources
        """
        # Reset state
        self.errors = []
        self.warnings = []

        chart_path = self._resolve_chart_path(input_source)

        if chart_path is None:
            return HelmParseResult(
                chart_info=None,
                k8s_result=K8sParseResult(
                    resources=[],
                    relationships=[],
                    namespaces=set(),
                    errors=self.errors,
                    warnings=self.warnings,
                ),
                rendered_with_helm=False,
                values_used={},
                errors=self.errors,
                warnings=self.warnings,
            )

        # Read chart metadata
        chart_info = self._read_chart_info(chart_path)

        # Merge values
        values = self._merge_values(chart_path, values_file, values_inline)

        # Try helm template first, fall back to raw parsing
        rendered_yaml = None
        rendered_with_helm = False

        if self.helm_available:
            rendered_yaml = self._helm_template(
                chart_path, release_name, namespace, values_file, values_inline
            )
            if rendered_yaml:
                rendered_with_helm = True

        if rendered_yaml is None:
            self.warnings.append(
                'Helm CLI not available or failed; falling back to raw template parsing'
            )
            rendered_yaml = self._parse_raw_templates(chart_path, values)

        # Parse the rendered YAML as K8s manifests
        k8s_parser = K8sParser()
        k8s_result = k8s_parser.parse(rendered_yaml)

        return HelmParseResult(
            chart_info=chart_info,
            k8s_result=k8s_result,
            rendered_with_helm=rendered_with_helm,
            values_used=values,
            errors=self.errors + k8s_result.errors,
            warnings=self.warnings + k8s_result.warnings,
        )

    def _resolve_chart_path(self, input_source: Union[str, Path]) -> Optional[Path]:
        """Resolve input to a chart directory path."""
        if isinstance(input_source, str):
            path = Path(input_source)
        else:
            path = input_source

        if not path.exists():
            self.errors.append(f'Chart path does not exist: {path}')
            return None

        # If it's a .tgz, extract it
        if path.suffix == '.tgz' or str(path).endswith('.tar.gz'):
            return self._extract_tgz(path)

        # Validate it's a chart directory
        if not (path / 'Chart.yaml').exists():
            self.errors.append(f'Not a valid Helm chart (missing Chart.yaml): {path}')
            return None

        return path

    def _extract_tgz(self, tgz_path: Path) -> Optional[Path]:
        """Extract a .tgz chart to a temp directory."""
        try:
            import tarfile

            temp_dir = Path(tempfile.mkdtemp())
            with tarfile.open(tgz_path, 'r:gz') as tar:
                tar.extractall(temp_dir)

            # Find the chart directory (usually the first subdirectory)
            for item in temp_dir.iterdir():
                if item.is_dir() and (item / 'Chart.yaml').exists():
                    return item

            self.errors.append(f'No valid chart found in {tgz_path}')
            return None
        except Exception as e:
            self.errors.append(f'Error extracting {tgz_path}: {e}')
            return None

    def _read_chart_info(self, chart_path: Path) -> Optional[HelmChartInfo]:
        """Read Chart.yaml metadata."""
        chart_yaml = chart_path / 'Chart.yaml'
        try:
            with open(chart_yaml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                self.warnings.append('Chart.yaml is not a valid YAML dictionary')
                return None

            dependencies = []
            deps = data.get('dependencies', [])
            if isinstance(deps, list):
                for dep in deps:
                    if isinstance(dep, dict):
                        dependencies.append(dep.get('name', 'unknown'))

            return HelmChartInfo(
                name=data.get('name', 'unknown'),
                version=data.get('version', '0.0.0'),
                app_version=data.get('appVersion'),
                description=data.get('description'),
                dependencies=dependencies,
            )
        except Exception as e:
            self.warnings.append(f'Error reading Chart.yaml: {e}')
            return None

    def _merge_values(
        self,
        chart_path: Path,
        values_file: Optional[Union[str, Path]],
        values_inline: Optional[Dict],
    ) -> Dict[str, Any]:
        """Merge default values with overrides."""
        values: Dict[str, Any] = {}

        # Read default values.yaml
        default_values = chart_path / 'values.yaml'
        if default_values.exists():
            try:
                with open(default_values, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        values = loaded
            except Exception as e:
                self.warnings.append(f'Error reading values.yaml: {e}')

        # Override with values file
        if values_file:
            try:
                values_path = Path(values_file)
                with open(values_path, 'r', encoding='utf-8') as f:
                    override = yaml.safe_load(f)
                    if isinstance(override, dict):
                        values = self._deep_merge(values, override)
            except Exception as e:
                self.warnings.append(f'Error reading values file: {e}')

        # Override with inline values
        if values_inline and isinstance(values_inline, dict):
            values = self._deep_merge(values, values_inline)

        return values

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _helm_template(
        self,
        chart_path: Path,
        release_name: str,
        namespace: str,
        values_file: Optional[Union[str, Path]],
        values_inline: Optional[Dict],
    ) -> Optional[str]:
        """Render chart using helm template command."""
        cmd = [
            'helm',
            'template',
            release_name,
            str(chart_path),
            '--namespace',
            namespace,
        ]

        if values_file:
            cmd.extend(['--values', str(values_file)])

        # Write inline values to temp file if provided
        temp_values_file = None
        if values_inline:
            try:
                temp_values_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.yaml', delete=False, encoding='utf-8'
                )
                yaml.dump(values_inline, temp_values_file)
                temp_values_file.close()
                cmd.extend(['--values', temp_values_file.name])
            except Exception as e:
                self.warnings.append(f'Error writing temp values file: {e}')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                self.warnings.append(f'helm template failed: {result.stderr}')
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            self.warnings.append('helm template timed out')
            return None
        except Exception as e:
            self.warnings.append(f'helm template error: {e}')
            return None
        finally:
            if temp_values_file and os.path.exists(temp_values_file.name):
                try:
                    os.unlink(temp_values_file.name)
                except OSError:
                    pass

    def _parse_raw_templates(self, chart_path: Path, values: Dict) -> str:
        """Parse raw Go templates and extract resource structure.

        This is a best-effort approach when helm CLI is unavailable.
        It attempts to remove template directives and replace simple
        value references with placeholders.

        Templates that don't produce valid YAML are skipped with a warning.
        For best results, install the Helm CLI.
        """
        templates_dir = chart_path / 'templates'
        if not templates_dir.exists():
            self.errors.append('No templates directory found')
            return ''

        rendered_docs = []
        skipped_templates = []

        # Find all YAML files in templates
        template_files = list(templates_dir.glob('*.yaml')) + list(templates_dir.glob('*.yml'))

        for template_file in sorted(template_files):
            # Skip helpers, notes, and test files
            if template_file.name.startswith('_') or 'NOTES' in template_file.name:
                continue
            if 'test' in template_file.name.lower():
                continue

            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple template processing
                processed = self._process_template(content, values)

                if processed.strip():
                    # Validate the processed YAML before including it
                    if self._validate_yaml(processed):
                        rendered_docs.append(processed)
                    else:
                        skipped_templates.append(template_file.name)

            except Exception as e:
                self.warnings.append(f'Error parsing {template_file}: {e}')

        if skipped_templates:
            self.warnings.append(
                f'Skipped {len(skipped_templates)} templates with invalid YAML '
                f'(install helm CLI for accurate parsing): {", ".join(skipped_templates[:5])}'
                + ('...' if len(skipped_templates) > 5 else '')
            )

        return '\n---\n'.join(rendered_docs)

    def _validate_yaml(self, content: str) -> bool:
        """Check if the processed content is valid YAML."""
        try:
            # Try to parse each document in the content
            for doc in yaml.safe_load_all(content):
                if doc is not None:
                    # Basic validation - should have apiVersion and kind for K8s resources
                    if isinstance(doc, dict):
                        if 'apiVersion' not in doc and 'kind' not in doc:
                            continue  # Not a K8s resource, but still valid YAML
            return True
        except yaml.YAMLError:
            return False

    def _process_template(self, content: str, values: Dict) -> str:
        """Process a Go template file, removing directives and substituting values.

        This is a simplified processor that handles common patterns:
        - Removes control flow directives (if, else, end, range, with, define, template, block)
        - Replaces .Values.x references with actual values or placeholders
        - Replaces .Release.Name, .Release.Namespace with defaults
        - Removes remaining template expressions
        """
        # Remove template comments
        content = re.sub(r'\{\{-?\s*/\*.*?\*/\s*-?\}\}', '', content, flags=re.DOTALL)

        # Handle common naming templates before removing them
        # {{ template "chart.fullname" . }} or {{ include "chart.fullname" . }}
        # Replace with "release-chart" pattern
        content = re.sub(
            r'\{\{-?\s*(?:template|include)\s+"[^"]*\.fullname[^"]*"\s*\.?\s*-?\}\}',
            'release-chart',
            content,
        )
        # {{ template "chart.name" . }} -> chart name
        content = re.sub(
            r'\{\{-?\s*(?:template|include)\s+"[^"]*\.name[^"]*"\s*\.?\s*-?\}\}',
            'chart',
            content,
        )
        # {{ template "chart.xxx.fullname" . }} for subcomponents
        content = re.sub(
            r'\{\{-?\s*(?:template|include)\s+"[^"]*\.([a-zA-Z0-9_-]+)\.fullname[^"]*"\s*\.?\s*-?\}\}',
            r'release-\1',
            content,
        )

        # Remove control flow directives
        control_patterns = [
            r'\{\{-?\s*if\s.*?-?\}\}',
            r'\{\{-?\s*else\s*-?\}\}',
            r'\{\{-?\s*else\s+if\s.*?-?\}\}',
            r'\{\{-?\s*end\s*-?\}\}',
            r'\{\{-?\s*range\s.*?-?\}\}',
            r'\{\{-?\s*with\s.*?-?\}\}',
            r'\{\{-?\s*define\s.*?-?\}\}',
            r'\{\{-?\s*template\s.*?-?\}\}',
            r'\{\{-?\s*block\s.*?-?\}\}',
            r'\{\{-?\s*include\s.*?-?\}\}',
        ]
        for pattern in control_patterns:
            content = re.sub(pattern, '', content)

        # Replace .Release.Name
        content = re.sub(r'\{\{\s*\.Release\.Name\s*\}\}', 'release', content)
        content = re.sub(r'\{\{-?\s*\.Release\.Name\s*-?\}\}', 'release', content)

        # Replace .Release.Namespace
        content = re.sub(r'\{\{\s*\.Release\.Namespace\s*\}\}', 'default', content)
        content = re.sub(r'\{\{-?\s*\.Release\.Namespace\s*-?\}\}', 'default', content)

        # Replace .Chart.Name
        content = re.sub(r'\{\{\s*\.Chart\.Name\s*\}\}', 'chart', content)
        content = re.sub(r'\{\{-?\s*\.Chart\.Name\s*-?\}\}', 'chart', content)

        # Replace simple .Values references with actual values or placeholders
        # Pattern: {{ .Values.key.subkey }}
        # Note: We don't add quotes here - let YAML handle quoting naturally
        # This avoids issues like image: "repo":"tag" which is invalid YAML
        def replace_values(match):
            path = match.group(1)
            parts = path.split('.')
            value = values
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return 'placeholder'
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, bool):
                    return str(value).lower()
                # For strings, only quote if they contain special YAML chars
                if isinstance(value, str):
                    if any(c in value for c in ':{}[]&*#?|-><!%@`'):
                        return f'"{value}"'
                    return value
                return str(value)
            return 'placeholder'

        content = re.sub(
            r'\{\{-?\s*\.Values\.([a-zA-Z0-9_.]+)\s*-?\}\}', replace_values, content
        )

        # Replace quote and other functions with placeholders
        # quote function explicitly adds quotes, so we keep them
        content = re.sub(r'\{\{\s*quote\s+[^}]+\}\}', '"placeholder"', content)
        # default function - don't quote to avoid YAML issues
        content = re.sub(r'\{\{\s*default\s+[^}]+\}\}', 'placeholder', content)

        # For toYaml - remove the entire line as {} on its own causes YAML issues
        # Pattern: whitespace + toYaml + optional pipe + nindent/indent
        content = re.sub(r'^[ \t]*\{\{-?\s*toYaml\s+[^}]+\}\}.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\{\{\s*toYaml\s+[^}]+\}\}', '{}', content)
        content = re.sub(r'\{\{\s*nindent\s+[^}]+\}\}', '', content)
        content = re.sub(r'\{\{\s*indent\s+[^}]+\}\}', '', content)

        # Remove remaining template expressions
        content = re.sub(r'\{\{[^}]+\}\}', '', content)

        # Clean up resulting YAML issues
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and standalone empty structures
            if not stripped or stripped in ('{}', '[]', '-'):
                continue
            # Skip lines that are just a key with no value (trailing colon only)
            # But keep lines like "key: value" or "key:"  followed by nested content
            if stripped.endswith(':') and len(stripped) > 1:
                # This is a key - keep it only if it has content or is followed by content
                cleaned_lines.append(line)
            elif stripped:
                cleaned_lines.append(line)

        # Second pass: remove orphaned keys (keys with no following content at deeper indent)
        final_lines = []
        for i, line in enumerate(cleaned_lines):
            stripped = line.strip()
            if stripped.endswith(':') and not ':' in stripped[:-1]:
                # This is a simple key - check if next line is at same or lower indent
                current_indent = len(line) - len(line.lstrip())
                if i + 1 < len(cleaned_lines):
                    next_line = cleaned_lines[i + 1]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= current_indent:
                        # Next line is same or lower indent - skip this orphaned key
                        continue
                else:
                    # Last line and it's just a key - skip
                    continue
            final_lines.append(line)

        return '\n'.join(final_lines)
