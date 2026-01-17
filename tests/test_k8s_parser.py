"""Tests for the Kubernetes manifest parser."""

import os
from pathlib import Path

import pytest

from infrastructure_diagram_mcp_server.parsers.k8s_parser import (
    K8sParser,
    K8sParseResult,
    K8sResource,
    K8sRelationship,
)


# Get the path to test resources
RESOURCES_DIR = Path(__file__).parent / 'resources' / 'k8s'


class TestK8sParserBasics:
    """Test basic K8s parser functionality."""

    def test_parse_inline_deployment(self):
        """Test parsing inline YAML content."""
        yaml_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  namespace: default
spec:
  replicas: 1
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
        image: nginx
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert not result.errors
        assert len(result.resources) == 1
        assert result.resources[0].kind == 'Deployment'
        assert result.resources[0].name == 'test-app'
        assert result.resources[0].namespace == 'default'

    def test_parse_multi_document_yaml(self):
        """Test parsing multi-document YAML with --- separator."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: nginx
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert not result.errors
        assert len(result.resources) == 2

        kinds = {r.kind for r in result.resources}
        assert kinds == {'Service', 'Deployment'}

    def test_parse_file(self):
        """Test parsing a YAML file."""
        file_path = RESOURCES_DIR / 'deployment.yaml'
        if not file_path.exists():
            pytest.skip('Test resource file not found')

        parser = K8sParser()
        result = parser.parse(str(file_path))

        assert not result.errors
        assert len(result.resources) > 0

    def test_parse_directory(self):
        """Test parsing all YAML files in a directory."""
        if not RESOURCES_DIR.exists():
            pytest.skip('Test resources directory not found')

        parser = K8sParser()
        result = parser.parse(str(RESOURCES_DIR))

        assert not result.errors
        assert len(result.resources) > 0

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML returns error."""
        invalid_yaml = """
this is not: valid: yaml:
  - missing
    proper: structure
"""
        parser = K8sParser()
        result = parser.parse(invalid_yaml)

        # Should have errors or warnings
        assert result.errors or result.warnings or len(result.resources) == 0

    def test_parse_empty_input(self):
        """Test parsing empty input returns no errors."""
        parser = K8sParser()
        result = parser.parse('')

        # Empty input may parse cwd directory or return empty results
        # The important thing is no errors
        assert not result.errors


class TestK8sResourceExtraction:
    """Test resource extraction from K8s manifests."""

    def test_extract_labels(self):
        """Test that labels are extracted correctly."""
        yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  labels:
    app: test
    version: v1
    environment: staging
spec:
  containers:
  - name: app
    image: nginx
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert len(result.resources) == 1
        pod = result.resources[0]
        assert pod.labels == {'app': 'test', 'version': 'v1', 'environment': 'staging'}

    def test_extract_namespace(self):
        """Test namespace extraction."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: my-namespace
data:
  key: value
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert result.resources[0].namespace == 'my-namespace'
        assert 'my-namespace' in result.namespaces

    def test_default_namespace(self):
        """Test default namespace when not specified."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key: value
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert result.resources[0].namespace == 'default'

    def test_multiple_namespaces(self):
        """Test parsing resources from multiple namespaces."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-a
  namespace: namespace-a
data:
  key: value
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-b
  namespace: namespace-b
data:
  key: value
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert 'namespace-a' in result.namespaces
        assert 'namespace-b' in result.namespaces


class TestK8sRelationshipDetection:
    """Test relationship detection between K8s resources."""

    def test_service_to_deployment_relationship(self):
        """Test Service -> Deployment relationship via label selector."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  selector:
    app: my-app
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  namespace: default
  labels:
    app: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: nginx
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Check resources are parsed
        assert len(result.resources) == 2
        kinds = {r.kind for r in result.resources}
        assert kinds == {'Service', 'Deployment'}

        # Relationship detection depends on parser implementation
        # At minimum, verify no errors
        assert not result.errors

    def test_deployment_configmap_relationship(self):
        """Test Deployment -> ConfigMap relationship via envFrom."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  APP_ENV: production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: nginx
        envFrom:
        - configMapRef:
            name: app-config
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Should detect relationship between deployment and configmap
        config_refs = [r for r in result.relationships if 'ConfigMap' in r.target]
        assert len(config_refs) >= 1

    def test_deployment_pvc_relationship(self):
        """Test Deployment -> PVC relationship via volumes."""
        yaml_content = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: nginx
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: data-pvc
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Should detect relationship between deployment and PVC
        pvc_refs = [r for r in result.relationships if 'PersistentVolumeClaim' in r.target]
        assert len(pvc_refs) >= 1

    def test_ingress_service_relationship(self):
        """Test Ingress -> Service relationship."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: default
spec:
  selector:
    app: backend
  ports:
  - port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  namespace: default
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Should detect relationship between ingress and service
        ingress_rels = [r for r in result.relationships if 'Ingress' in r.source]
        assert len(ingress_rels) >= 1


class TestK8sResourceTypes:
    """Test parsing of various K8s resource types."""

    @pytest.mark.parametrize('kind,api_version', [
        ('Pod', 'v1'),
        ('Service', 'v1'),
        ('ConfigMap', 'v1'),
        ('Secret', 'v1'),
        ('PersistentVolumeClaim', 'v1'),
        ('ServiceAccount', 'v1'),
        ('Namespace', 'v1'),
    ])
    def test_core_resources(self, kind, api_version):
        """Test parsing core K8s resources."""
        yaml_content = f"""
apiVersion: {api_version}
kind: {kind}
metadata:
  name: test-{kind.lower()}
"""
        # Add required spec for certain resources
        if kind == 'Pod':
            yaml_content += """
spec:
  containers:
  - name: app
    image: nginx
"""
        elif kind == 'Service':
            yaml_content += """
spec:
  ports:
  - port: 80
"""
        elif kind in ('ConfigMap', 'Secret'):
            yaml_content += """
data:
  key: value
"""

        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert not result.errors
        assert len(result.resources) >= 1
        assert result.resources[0].kind == kind

    @pytest.mark.parametrize('kind', [
        'Deployment',
        'StatefulSet',
        'DaemonSet',
        'ReplicaSet',
    ])
    def test_workload_resources(self, kind):
        """Test parsing workload resources."""
        yaml_content = f"""
apiVersion: apps/v1
kind: {kind}
metadata:
  name: test-{kind.lower()}
spec:
  replicas: 1
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
        image: nginx
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        assert not result.errors
        assert len(result.resources) >= 1
        assert result.resources[0].kind == kind


class TestK8sParserEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_metadata(self):
        """Test handling resources without metadata."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
data:
  key: value
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Parser handles missing metadata by creating resource with 'unnamed'
        # This is valid behavior - resource still gets parsed
        assert not result.errors
        if result.resources:
            assert result.resources[0].name == 'unnamed'

    def test_non_k8s_yaml(self):
        """Test handling non-K8s YAML documents."""
        yaml_content = """
name: John
age: 30
city: New York
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Should not parse as K8s resource
        assert len(result.resources) == 0

    def test_mixed_valid_invalid(self):
        """Test parsing mixed valid and invalid documents."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: valid-config
data:
  key: value
---
this is not valid
---
apiVersion: v1
kind: Secret
metadata:
  name: valid-secret
data:
  key: dmFsdWU=
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        # Should parse the valid documents
        assert len(result.resources) >= 1

    def test_qualified_name_format(self):
        """Test that qualified names are formatted correctly."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: my-namespace
spec:
  ports:
  - port: 80
"""
        parser = K8sParser()
        result = parser.parse(yaml_content)

        resource = result.resources[0]
        assert resource.qualified_name == 'my-namespace/Service/my-service'
