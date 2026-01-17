"""Dynamic icon resolution using the diagrams package introspection.

This module provides the IconResolver class that dynamically discovers and resolves
icons from the diagrams package. Instead of maintaining static mapping files, it
uses the existing list_diagram_icons() function to discover all available icons
at runtime.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from infrastructure_diagram_mcp_server.diagrams_tools import list_diagram_icons


# Provider mappings for Terraform resource type prefixes
TERRAFORM_PROVIDER_MAPPING = {
    'aws_': 'aws',
    'google_': 'gcp',
    'azurerm_': 'azure',
    'kubernetes_': 'k8s',
    'helm_': 'k8s',
    'digitalocean_': 'digitalocean',
    'alicloud_': 'alibabacloud',
    'oci_': 'oci',
    'ibm_': 'ibm',
    'openstack_': 'openstack',
}

# Generic fallback icons per provider
GENERIC_FALLBACK_ICONS = {
    'aws': ('aws.general', 'General'),
    'gcp': ('gcp.compute', 'ComputeEngine'),
    'azure': ('azure.compute', 'VM'),
    'k8s': ('k8s.compute', 'Pod'),
    'digitalocean': ('digitalocean.compute', 'Droplet'),
    'alibabacloud': ('alibabacloud.compute', 'ECS'),
    'oci': ('oci.compute', 'VM'),
    'ibm': ('ibm.compute', 'VirtualServer'),
    'openstack': ('openstack.compute', 'Nova'),
    'generic': ('generic.compute', 'Rack'),
    'onprem': ('onprem.compute', 'Server'),
}

# Common abbreviations and aliases for better matching
ICON_ALIASES = {
    # K8s abbreviations
    'horizontalpodautoscaler': ['hpa'],
    'persistentvolume': ['pv'],
    'persistentvolumeclaim': ['pvc'],
    'storageclass': ['sc'],
    'configmap': ['cm'],
    'replicaset': ['rs'],
    'statefulset': ['sts'],
    'daemonset': ['ds'],
    'deployment': ['deploy'],
    'service': ['svc'],
    'ingress': ['ing'],
    'namespace': ['ns'],
    'serviceaccount': ['sa'],
    'cronjob': ['cj'],
    # AWS common terms
    'lambda': ['lambdafunction', 'function'],
    'ec2': ['instance', 'computeinstance'],
    's3': ['bucket', 'storage', 'simplestorage'],
    'rds': ['database', 'db', 'relationaldb'],
    'elb': ['loadbalancer', 'lb', 'alb', 'nlb'],
    'vpc': ['virtualnetwork', 'network'],
    'iam': ['identity', 'accessmanagement'],
    'sqs': ['queue', 'simplequeue'],
    'sns': ['notification', 'simplenotification'],
    'dynamodb': ['dynamo', 'nosql'],
    'elasticache': ['cache', 'redis', 'memcached'],
    'cloudwatch': ['monitoring', 'logs'],
    'apigateway': ['api', 'gateway'],
    # GCP common terms
    'computeengine': ['gce', 'compute', 'vm'],
    'cloudstorage': ['gcs', 'storage', 'bucket'],
    'cloudsql': ['sql', 'database'],
    'bigquery': ['bq', 'datawarehouse'],
    'pubsub': ['messaging', 'queue'],
    'gke': ['kubernetes', 'k8s'],
    # Azure common terms
    'virtualmachine': ['vm', 'compute'],
    'storageaccount': ['storage', 'blob'],
    'sqldatabase': ['sql', 'database'],
    'cosmosdb': ['cosmos', 'nosql'],
    'aks': ['kubernetes', 'k8s'],
}


class IconResolver:
    """Dynamic icon resolver that discovers icons from the diagrams package.

    This class uses list_diagram_icons() to dynamically discover all available
    icons and provides intelligent matching including exact, case-insensitive,
    partial, and fuzzy matching.

    Usage:
        resolver = IconResolver()
        module, icon = resolver.resolve_k8s("Deployment")  # ("k8s.compute", "Deployment")
        module, icon = resolver.resolve_terraform("aws_lambda_function")  # ("aws.compute", "Lambda")
    """

    def __init__(self):
        """Initialize the icon resolver with lazy-loaded icon cache."""
        self._icon_cache: Optional[Dict[str, Dict[str, List[str]]]] = None
        self._flat_index: Optional[Dict[str, List[Tuple[str, str, str]]]] = None

    def _ensure_loaded(self) -> None:
        """Ensure the icon cache is loaded."""
        if self._icon_cache is None:
            self._load_all_icons()

    def _load_all_icons(self) -> None:
        """Load all icons from the diagrams package using list_diagram_icons()."""
        self._icon_cache = {}
        self._flat_index = {}

        # First, get all available providers
        providers_response = list_diagram_icons()
        providers = list(providers_response.providers.keys())

        # Then load icons for each provider
        for provider in providers:
            provider_response = list_diagram_icons(provider_filter=provider)
            if provider_response.providers and provider in provider_response.providers:
                self._icon_cache[provider] = provider_response.providers[provider]

                # Build flat index for searching
                for service, icons in provider_response.providers[provider].items():
                    for icon in icons:
                        icon_lower = icon.lower()
                        if icon_lower not in self._flat_index:
                            self._flat_index[icon_lower] = []
                        self._flat_index[icon_lower].append((provider, service, icon))

    def resolve_k8s(self, kind: str) -> Tuple[str, str]:
        """Resolve a Kubernetes resource kind to a diagrams icon.

        Args:
            kind: The Kubernetes resource kind (e.g., "Deployment", "Service")

        Returns:
            Tuple of (module_path, icon_class) e.g., ("k8s.compute", "Deployment")
        """
        self._ensure_loaded()

        # Try to find in k8s provider first
        result = self._search_provider('k8s', kind)
        if result:
            return result

        # Try generic/onprem as fallback
        result = self._search_provider('generic', kind)
        if result:
            return result

        # Return default k8s icon
        return GENERIC_FALLBACK_ICONS.get('k8s', ('k8s.compute', 'Pod'))

    def resolve_terraform(self, resource_type: str) -> Tuple[str, str]:
        """Resolve a Terraform resource type to a diagrams icon.

        Args:
            resource_type: The Terraform resource type (e.g., "aws_lambda_function")

        Returns:
            Tuple of (module_path, icon_class) e.g., ("aws.compute", "Lambda")
        """
        self._ensure_loaded()

        # Detect provider from resource type prefix
        provider = self._detect_terraform_provider(resource_type)

        # Extract the resource name without provider prefix
        resource_name = self._extract_resource_name(resource_type)

        # Search within the detected provider
        result = self._search_provider(provider, resource_name)
        if result:
            return result

        # Try searching in related providers (e.g., onprem for generic resources)
        for fallback_provider in ['generic', 'onprem']:
            if fallback_provider != provider:
                result = self._search_provider(fallback_provider, resource_name)
                if result:
                    return result

        # Return provider-specific generic icon
        return GENERIC_FALLBACK_ICONS.get(provider, GENERIC_FALLBACK_ICONS['generic'])

    def resolve_any(self, resource_type: str, hint_provider: Optional[str] = None) -> Tuple[str, str]:
        """Resolve any resource type to a diagrams icon.

        Args:
            resource_type: The resource type name
            hint_provider: Optional provider hint to prioritize

        Returns:
            Tuple of (module_path, icon_class)
        """
        self._ensure_loaded()

        # If provider hint is given, search there first
        if hint_provider:
            result = self._search_provider(hint_provider, resource_type)
            if result:
                return result

        # Search all providers
        result = self._search_all_providers(resource_type)
        if result:
            return result

        # Return generic fallback
        provider = hint_provider or 'generic'
        return GENERIC_FALLBACK_ICONS.get(provider, GENERIC_FALLBACK_ICONS['generic'])

    def _detect_terraform_provider(self, resource_type: str) -> str:
        """Detect the diagrams provider from Terraform resource type prefix."""
        for prefix, provider in TERRAFORM_PROVIDER_MAPPING.items():
            if resource_type.startswith(prefix):
                return provider
        return 'generic'

    def _extract_resource_name(self, resource_type: str) -> str:
        """Extract the resource name from a Terraform resource type.

        Examples:
            aws_lambda_function -> lambda_function -> lambda function
            google_compute_instance -> compute_instance -> compute instance
            azurerm_kubernetes_cluster -> kubernetes_cluster -> kubernetes cluster
        """
        # Remove provider prefix
        for prefix in TERRAFORM_PROVIDER_MAPPING.keys():
            if resource_type.startswith(prefix):
                resource_type = resource_type[len(prefix):]
                break

        # Convert underscores to spaces for better matching
        return resource_type.replace('_', ' ')

    def _search_provider(self, provider: str, search_term: str) -> Optional[Tuple[str, str]]:
        """Search for an icon within a specific provider.

        Uses multiple matching strategies:
        1. Exact match
        2. Case-insensitive match
        3. Alias match
        4. Partial match
        5. Fuzzy match
        """
        if provider not in self._icon_cache:
            return None

        search_lower = search_term.lower().replace(' ', '').replace('_', '')

        # Strategy 1: Exact match
        for service, icons in self._icon_cache[provider].items():
            for icon in icons:
                if icon == search_term:
                    return (f'{provider}.{service}', icon)

        # Strategy 2: Case-insensitive exact match
        for service, icons in self._icon_cache[provider].items():
            for icon in icons:
                if icon.lower() == search_lower:
                    return (f'{provider}.{service}', icon)

        # Strategy 3: Alias match
        for canonical, aliases in ICON_ALIASES.items():
            if search_lower in aliases or search_lower == canonical:
                # Found an alias, search for the canonical name
                for service, icons in self._icon_cache[provider].items():
                    for icon in icons:
                        if icon.lower() == canonical:
                            return (f'{provider}.{service}', icon)

        # Strategy 4: Partial match (search term is contained in icon name or vice versa)
        best_partial = None
        best_partial_score = 0

        for service, icons in self._icon_cache[provider].items():
            for icon in icons:
                icon_lower = icon.lower()

                # Check if search term is in icon name
                if search_lower in icon_lower:
                    score = len(search_lower) / len(icon_lower)
                    if score > best_partial_score:
                        best_partial_score = score
                        best_partial = (f'{provider}.{service}', icon)

                # Check if any word from search matches
                search_words = re.split(r'[\s_-]+', search_term.lower())
                for word in search_words:
                    if len(word) >= 3 and word in icon_lower:
                        score = len(word) / len(icon_lower) * 0.8  # Slightly lower score for word match
                        if score > best_partial_score:
                            best_partial_score = score
                            best_partial = (f'{provider}.{service}', icon)

        if best_partial and best_partial_score > 0.3:
            return best_partial

        # Strategy 5: Fuzzy match using sequence matcher
        best_fuzzy = None
        best_fuzzy_score = 0

        for service, icons in self._icon_cache[provider].items():
            for icon in icons:
                score = SequenceMatcher(None, search_lower, icon.lower()).ratio()
                if score > best_fuzzy_score and score > 0.5:  # Threshold of 0.5
                    best_fuzzy_score = score
                    best_fuzzy = (f'{provider}.{service}', icon)

        if best_fuzzy:
            return best_fuzzy

        return None

    def _search_all_providers(self, search_term: str) -> Optional[Tuple[str, str]]:
        """Search for an icon across all providers."""
        search_lower = search_term.lower().replace(' ', '').replace('_', '')

        # First check flat index for exact/case-insensitive match
        if search_lower in self._flat_index:
            # Return first match (arbitrary but consistent)
            provider, service, icon = self._flat_index[search_lower][0]
            return (f'{provider}.{service}', icon)

        # Search each provider
        for provider in self._icon_cache.keys():
            result = self._search_provider(provider, search_term)
            if result:
                return result

        return None

    def get_all_icons_for_provider(self, provider: str) -> Dict[str, List[str]]:
        """Get all icons for a specific provider.

        Args:
            provider: The provider name (e.g., "aws", "k8s")

        Returns:
            Dictionary mapping service names to lists of icon names
        """
        self._ensure_loaded()
        return self._icon_cache.get(provider, {})

    def get_available_providers(self) -> List[str]:
        """Get list of all available providers.

        Returns:
            List of provider names
        """
        self._ensure_loaded()
        return list(self._icon_cache.keys())


# Module-level singleton for convenience
_resolver_instance: Optional[IconResolver] = None


def get_icon_resolver() -> IconResolver:
    """Get the singleton IconResolver instance.

    Returns:
        The shared IconResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = IconResolver()
    return _resolver_instance
