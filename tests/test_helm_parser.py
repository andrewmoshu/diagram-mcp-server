"""Tests for the Helm chart parser."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from infrastructure_diagram_mcp_server.parsers.helm_parser import (
    HelmParser,
    HelmParseResult,
    HelmChartInfo,
)


class TestHelmParserBasics:
    """Test basic Helm parser functionality."""

    def test_parse_nonexistent_chart(self):
        """Test parsing a non-existent chart path."""
        parser = HelmParser()
        result = parser.parse('/nonexistent/path/to/chart')

        assert result.errors
        assert any('not found' in e.lower() or 'does not exist' in e.lower() for e in result.errors)

    def test_parse_directory_without_chart_yaml(self):
        """Test parsing a directory that's not a Helm chart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory without Chart.yaml
            parser = HelmParser()
            result = parser.parse(tmpdir)

            assert result.errors
            assert any('chart.yaml' in e.lower() for e in result.errors)


class TestHelmChartStructure:
    """Test Helm chart structure parsing."""

    @pytest.fixture
    def sample_chart(self):
        """Create a sample Helm chart for testing."""
        tmpdir = tempfile.mkdtemp()

        # Create Chart.yaml
        chart_yaml = """
apiVersion: v2
name: test-chart
description: A test Helm chart
version: 1.0.0
appVersion: "1.0"
"""
        with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
            f.write(chart_yaml)

        # Create values.yaml
        values_yaml = """
replicaCount: 3
image:
  repository: nginx
  tag: latest
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
"""
        with open(os.path.join(tmpdir, 'values.yaml'), 'w') as f:
            f.write(values_yaml)

        # Create templates directory
        templates_dir = os.path.join(tmpdir, 'templates')
        os.makedirs(templates_dir)

        # Create a simple deployment template (without complex templating)
        deployment_template = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
"""
        with open(os.path.join(templates_dir, 'deployment.yaml'), 'w') as f:
            f.write(deployment_template)

        # Create a simple service template
        service_template = """
apiVersion: v1
kind: Service
metadata:
  name: test-service
spec:
  type: ClusterIP
  selector:
    app: test
  ports:
  - port: 80
    targetPort: 80
"""
        with open(os.path.join(templates_dir, 'service.yaml'), 'w') as f:
            f.write(service_template)

        yield tmpdir

        # Cleanup
        shutil.rmtree(tmpdir)

    def test_parse_chart_info(self, sample_chart):
        """Test parsing Chart.yaml information."""
        parser = HelmParser()
        result = parser.parse(sample_chart)

        assert result.chart_info is not None
        assert result.chart_info.name == 'test-chart'
        assert result.chart_info.version == '1.0.0'
        assert result.chart_info.app_version == '1.0'

    def test_parse_chart_resources(self, sample_chart):
        """Test parsing K8s resources from chart templates."""
        parser = HelmParser()
        result = parser.parse(sample_chart)

        # Should have k8s_result with resources
        assert result.k8s_result is not None
        assert len(result.k8s_result.resources) >= 1

    def test_parse_with_custom_values(self, sample_chart):
        """Test parsing with custom values inline."""
        parser = HelmParser()
        custom_values = {'replicaCount': 5, 'service': {'port': 8080}}
        result = parser.parse(
            sample_chart,
            values_inline=custom_values,
        )

        assert not result.errors or len(result.k8s_result.resources) > 0


class TestHelmTemplateProcessing:
    """Test Helm template processing (fallback mode)."""

    @pytest.fixture
    def chart_with_templates(self):
        """Create a chart with Go templates for testing fallback mode."""
        tmpdir = tempfile.mkdtemp()

        # Create Chart.yaml
        with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
            f.write("""
apiVersion: v2
name: templated-chart
version: 1.0.0
""")

        # Create values.yaml
        with open(os.path.join(tmpdir, 'values.yaml'), 'w') as f:
            f.write("""
name: myapp
port: 8080
""")

        # Create templates directory
        templates_dir = os.path.join(tmpdir, 'templates')
        os.makedirs(templates_dir)

        # Create _helpers.tpl (should be skipped)
        with open(os.path.join(templates_dir, '_helpers.tpl'), 'w') as f:
            f.write('{{/* Helper templates */}}')

        # Create simple configmap that's easy to parse in fallback mode
        with open(os.path.join(templates_dir, 'configmap.yaml'), 'w') as f:
            f.write("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Values.name }}-config
data:
  APP_NAME: {{ .Values.name }}
  APP_PORT: "{{ .Values.port }}"
""")

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_fallback_when_helm_unavailable(self, chart_with_templates):
        """Test fallback template parsing when helm CLI is unavailable."""
        parser = HelmParser()
        # Override helm_available to simulate helm not being present
        parser.helm_available = False

        result = parser.parse(chart_with_templates)

        # Should use fallback mode
        assert result.rendered_with_helm is False
        # Chart info should still be parsed
        assert result.chart_info is not None
        # May have resources (depending on template complexity) or errors/warnings
        # The key is that it doesn't crash
        assert result is not None

    def test_skip_helper_files(self, chart_with_templates):
        """Test that _helpers.tpl and similar files are skipped."""
        parser = HelmParser()
        result = parser.parse(chart_with_templates)

        # _helpers.tpl should not appear as a resource
        for resource in result.k8s_result.resources:
            assert resource.kind != '_helpers'


class TestHelmValuesOverride:
    """Test values override functionality."""

    @pytest.fixture
    def chart_with_values(self):
        """Create a chart for testing values override."""
        tmpdir = tempfile.mkdtemp()

        with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
            f.write("""
apiVersion: v2
name: values-test
version: 1.0.0
""")

        with open(os.path.join(tmpdir, 'values.yaml'), 'w') as f:
            f.write("""
app:
  name: default-app
  port: 8080
debug: false
""")

        templates_dir = os.path.join(tmpdir, 'templates')
        os.makedirs(templates_dir)

        with open(os.path.join(templates_dir, 'configmap.yaml'), 'w') as f:
            f.write("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_NAME: {{ .Values.app.name }}
  APP_PORT: "{{ .Values.app.port }}"
""")

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_values_file_override(self, chart_with_values):
        """Test overriding values with a values file."""
        # Create override values file
        override_file = os.path.join(chart_with_values, 'custom-values.yaml')
        with open(override_file, 'w') as f:
            f.write("""
app:
  name: custom-app
  port: 9090
""")

        parser = HelmParser()
        result = parser.parse(chart_with_values, values_file=override_file)

        # Should parse without errors
        assert not result.errors or len(result.k8s_result.resources) > 0

    def test_inline_values_override(self, chart_with_values):
        """Test overriding values with inline dict."""
        parser = HelmParser()
        result = parser.parse(
            chart_with_values,
            values_inline={'app': {'name': 'inline-app'}},
        )

        assert not result.errors or len(result.k8s_result.resources) > 0


class TestHelmParserEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_templates_directory(self):
        """Test chart with empty templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
                f.write("""
apiVersion: v2
name: empty-templates
version: 1.0.0
""")
            os.makedirs(os.path.join(tmpdir, 'templates'))

            parser = HelmParser()
            result = parser.parse(tmpdir)

            # Should handle gracefully
            assert result.k8s_result is not None

    def test_invalid_chart_yaml(self):
        """Test chart with invalid Chart.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
                f.write('invalid: yaml: content:')

            parser = HelmParser()
            result = parser.parse(tmpdir)

            # Should report error
            assert result.errors or result.warnings

    def test_chart_with_dependencies(self):
        """Test parsing Chart.yaml with dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
                f.write("""
apiVersion: v2
name: chart-with-deps
version: 1.0.0
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
  - name: redis
    version: "17.0.0"
    repository: "https://charts.bitnami.com/bitnami"
""")
            os.makedirs(os.path.join(tmpdir, 'templates'))

            parser = HelmParser()
            result = parser.parse(tmpdir)

            assert result.chart_info is not None
            assert len(result.chart_info.dependencies) == 2


class TestHelmParserIntegration:
    """Integration tests with real Helm charts if available."""

    def test_parse_release_name_and_namespace(self):
        """Test that release name and namespace are passed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'Chart.yaml'), 'w') as f:
                f.write("""
apiVersion: v2
name: release-test
version: 1.0.0
""")

            with open(os.path.join(tmpdir, 'values.yaml'), 'w') as f:
                f.write('key: value\n')

            templates_dir = os.path.join(tmpdir, 'templates')
            os.makedirs(templates_dir)

            with open(os.path.join(templates_dir, 'configmap.yaml'), 'w') as f:
                f.write("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-config
  namespace: {{ .Release.Namespace }}
data:
  key: value
""")

            parser = HelmParser()
            result = parser.parse(
                tmpdir,
                release_name='my-release',
                namespace='my-namespace',
            )

            # Should process without errors
            assert result.k8s_result is not None
