# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Modifications Copyright 2025 Andrii Moshurenko
# - Restructured as infrastructure-diagram-mcp-server
# - Added comprehensive diagram examples for GCP, Azure, Hybrid, and Multi-cloud
# - Added draw.io export support
# - Enhanced icon discovery and filtering
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

"""Diagram generation and example functions for the diagrams-mcp-server."""

import diagrams
import importlib
import inspect
import logging
import os
import re
import signal
import uuid
from infrastructure_diagram_mcp_server.models import (
    DiagramExampleResponse,
    DiagramGenerateResponse,
    DiagramIconsResponse,
    DiagramType,
)
from infrastructure_diagram_mcp_server.scanner import scan_python_code
from typing import Optional


logger = logging.getLogger(__name__)


async def generate_diagram(
    code: str,
    filename: Optional[str] = None,
    timeout: int = 90,
    workspace_dir: Optional[str] = None,
) -> DiagramGenerateResponse:
    """Generate a diagram from Python code using the `diagrams` package.

    You should use the `get_diagram_examples` tool first to get examples of how to use the `diagrams` package.

    This function accepts Python code as a string that uses the diagrams package DSL
    and generates a PNG diagram without displaying it. The code is executed with
    show=False to prevent automatic display.

    Supported diagram types:
    - AWS architecture diagrams
    - Sequence diagrams
    - Flow diagrams
    - Class diagrams
    - Kubernetes diagrams
    - On-premises diagrams
    - Custom diagrams with custom nodes

    Args:
        code: Python code string using the diagrams package DSL
        filename: Output filename (without extension). If not provided, a random name will be generated.
        timeout: Timeout in seconds for diagram generation
        workspace_dir: The user's current workspace directory. If provided, diagrams will be saved to a "generated-diagrams" subdirectory.

    Returns:
        DiagramGenerateResponse: Response with the path to the generated diagram and status
    """
    # Scan the code for security issues
    scan_result = await scan_python_code(code)
    if scan_result.has_errors:
        return DiagramGenerateResponse(
            status='error',
            message=f'Security issues found in the code: {scan_result.error_message}',
        )

    if filename is None:
        filename = f'diagram_{uuid.uuid4().hex[:8]}'

    # Determine the output path
    if os.path.isabs(filename):
        # If it's an absolute path, strip .png extension if present
        # (diagrams library adds .png automatically)
        output_path = filename[:-4] if filename.endswith('.png') else filename
        # Set output_dir to the directory containing the file
        output_dir = os.path.dirname(output_path) or os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
    else:
        # For non-absolute paths, use the "generated-diagrams" subdirectory

        # Strip any path components to ensure it's just a filename
        # (for relative paths with directories like "path/to/diagram.png")
        simple_filename = os.path.basename(filename)

        # Strip .png extension if present, as the diagrams library adds it automatically
        if simple_filename.endswith('.png'):
            simple_filename = simple_filename[:-4]

        # Use workspace_dir if provided and writable, otherwise fall back to temp directory
        if workspace_dir and os.path.isdir(workspace_dir) and os.access(workspace_dir, os.W_OK):
            # Create a "generated-diagrams" subdirectory in the workspace
            output_dir = os.path.join(workspace_dir, 'generated-diagrams')
        else:
            # Fall back to a secure temporary directory if workspace_dir isn't provided or isn't writable
            import tempfile

            temp_base = tempfile.gettempdir()
            output_dir = os.path.join(temp_base, 'generated-diagrams')

        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Combine directory and filename
        output_path = os.path.join(output_dir, simple_filename)

    try:
        # Create a namespace for execution
        namespace = {}

        # Import necessary modules directly in the namespace
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec(  # nosem: python.lang.security.audit.exec-detected.exec-detected
            # nosem: python.lang.security.audit.exec-detected.exec-detected
            'import os',
            namespace,
        )
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec(  # nosem: python.lang.security.audit.exec-detected.exec-detected
            'import diagrams', namespace
        )
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec(  # nosem: python.lang.security.audit.exec-detected.exec-detected
            'from diagrams import Diagram, Cluster, Edge', namespace
        )  # nosem: python.lang.security.audit.exec-detected.exec-detected
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec(  # nosem: python.lang.security.audit.exec-detected.exec-detected
            """from diagrams.saas.crm import *
from diagrams.saas.identity import *
from diagrams.saas.chat import *
from diagrams.saas.recommendation import *
from diagrams.saas.cdn import *
from diagrams.saas.communication import *
from diagrams.saas.media import *
from diagrams.saas.logging import *
from diagrams.saas.security import *
from diagrams.saas.social import *
from diagrams.saas.alerting import *
from diagrams.saas.analytics import *
from diagrams.saas.automation import *
from diagrams.saas.filesharing import *
from diagrams.onprem.vcs import *
from diagrams.onprem.database import *
from diagrams.onprem.gitops import *
from diagrams.onprem.workflow import *
from diagrams.onprem.etl import *
from diagrams.onprem.inmemory import *
from diagrams.onprem.identity import *
from diagrams.onprem.network import *
from diagrams.onprem.proxmox import *
from diagrams.onprem.cd import *
from diagrams.onprem.container import *
from diagrams.onprem.certificates import *
from diagrams.onprem.mlops import *
from diagrams.onprem.dns import *
from diagrams.onprem.compute import *
from diagrams.onprem.logging import *
from diagrams.onprem.registry import *
from diagrams.onprem.security import *
from diagrams.onprem.client import *
from diagrams.onprem.groupware import *
from diagrams.onprem.iac import *
from diagrams.onprem.analytics import *
from diagrams.onprem.messaging import *
from diagrams.onprem.tracing import *
from diagrams.onprem.ci import *
from diagrams.onprem.search import *
from diagrams.onprem.storage import *
from diagrams.onprem.auth import *
from diagrams.onprem.monitoring import *
from diagrams.onprem.aggregator import *
from diagrams.onprem.queue import *
from diagrams.gis.database import *
from diagrams.gis.cli import *
from diagrams.gis.server import *
from diagrams.gis.python import *
from diagrams.gis.organization import *
from diagrams.gis.cplusplus import *
from diagrams.gis.mobile import *
from diagrams.gis.javascript import *
from diagrams.gis.desktop import *
from diagrams.gis.ogc import *
from diagrams.gis.java import *
from diagrams.gis.routing import *
from diagrams.gis.data import *
from diagrams.gis.geocoding import *
from diagrams.gis.format import *
from diagrams.elastic.saas import *
from diagrams.elastic.observability import *
from diagrams.elastic.elasticsearch import *
from diagrams.elastic.orchestration import *
from diagrams.elastic.security import *
from diagrams.elastic.beats import *
from diagrams.elastic.enterprisesearch import *
from diagrams.elastic.agent import *
from diagrams.programming.runtime import *
from diagrams.programming.framework import *
from diagrams.programming.flowchart import *
from diagrams.programming.language import *
from diagrams.gcp.storage import *
from diagrams.gcp.compute import *
from diagrams.gcp.network import *
from diagrams.gcp.database import *
from diagrams.gcp.analytics import *
from diagrams.gcp.ml import *
from diagrams.gcp.devtools import *
from diagrams.gcp.operations import *
from diagrams.gcp.iot import *
from diagrams.gcp.api import *
from diagrams.gcp.security import *
from diagrams.gcp.migration import *
from diagrams.azure.web import *
from diagrams.azure.database import *
from diagrams.azure.storage import *
from diagrams.azure.compute import *
from diagrams.azure.analytics import *
from diagrams.azure.integration import *
from diagrams.azure.devops import *
from diagrams.azure.ml import *
from diagrams.azure.iot import *
from diagrams.azure.network import *
from diagrams.azure.general import *
from diagrams.azure.mobile import *
from diagrams.azure.security import *
from diagrams.azure.identity import *
from diagrams.azure.migration import *
from diagrams.generic.database import *
from diagrams.generic.blank import *
from diagrams.generic.network import *
from diagrams.generic.virtualization import *
from diagrams.generic.place import *
from diagrams.generic.device import *
from diagrams.generic.compute import *
from diagrams.generic.os import *
from diagrams.generic.storage import *
from diagrams.k8s.others import *
from diagrams.k8s.rbac import *
from diagrams.k8s.network import *
from diagrams.k8s.ecosystem import *
from diagrams.k8s.compute import *
from diagrams.k8s.chaos import *
from diagrams.k8s.infra import *
from diagrams.k8s.podconfig import *
from diagrams.k8s.controlplane import *
from diagrams.k8s.clusterconfig import *
from diagrams.k8s.storage import *
from diagrams.k8s.group import *
from diagrams.aws.cost import *
from diagrams.aws.ar import *
from diagrams.aws.general import *
from diagrams.aws.database import *
from diagrams.aws.management import *
from diagrams.aws.ml import *
from diagrams.aws.game import *
from diagrams.aws.enablement import *
from diagrams.aws.network import *
from diagrams.aws.quantum import *
from diagrams.aws.iot import *
from diagrams.aws.robotics import *
from diagrams.aws.migration import *
from diagrams.aws.mobile import *
from diagrams.aws.compute import *
from diagrams.aws.media import *
from diagrams.aws.engagement import *
from diagrams.aws.security import *
from diagrams.aws.devtools import *
from diagrams.aws.integration import *
from diagrams.aws.business import *
from diagrams.aws.analytics import *
from diagrams.aws.blockchain import *
from diagrams.aws.storage import *
from diagrams.aws.satellite import *
from diagrams.aws.enduser import *
""",
            namespace,
        )
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec(  # nosem: python.lang.security.audit.exec-detected.exec-detected
            'from urllib.request import urlretrieve', namespace
        )  # nosem: python.lang.security.audit.exec-detected.exec-detected

        # Process the code to ensure show=False and set the output path
        if 'with Diagram(' in code:
            # Find all instances of Diagram constructor
            diagram_pattern = r'with\s+Diagram\s*\((.*?)\)'
            matches = re.findall(diagram_pattern, code)

            for match in matches:
                # Get the original arguments
                original_args = match.strip()

                # Check if show parameter is already set
                has_show = 'show=' in original_args
                has_filename = 'filename=' in original_args
                has_outformat = 'outformat=' in original_args

                # Prepare new arguments
                new_args = original_args

                # Add or replace parameters as needed
                # If filename is already set, we need to replace it with our output_path
                if has_filename:
                    # Replace the existing filename parameter
                    filename_pattern = r'filename\s*=\s*[\'"]([^\'"]*)[\'"]'
                    new_args = re.sub(filename_pattern, f"filename='{output_path}'", new_args)
                else:
                    # Add the filename parameter
                    if new_args and not new_args.endswith(','):
                        new_args += ', '
                    new_args += f"filename='{output_path}'"

                # Add show=False if not already set
                if not has_show:
                    if new_args and not new_args.endswith(','):
                        new_args += ', '
                    new_args += 'show=False'

                # Add outformat=["png", "dot"] to generate both PNG and DOT files
                if not has_outformat:
                    if new_args and not new_args.endswith(','):
                        new_args += ', '
                    new_args += 'outformat=["png", "dot"]'

                # Replace in the code
                code = code.replace(f'with Diagram({original_args})', f'with Diagram({new_args})')

        # Set up a timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError(f'Diagram generation timed out after {timeout} seconds')

        # Register the timeout handler
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        # Change to output directory before executing code
        # This ensures the diagrams library can create temporary directories
        original_cwd = os.getcwd()
        try:
            os.chdir(output_dir)

            # Execute the code
            # nosec B102 - This exec is necessary to run user-provided diagram code in a controlled environment
            exec(code, namespace)  # nosem: python.lang.security.audit.exec-detected.exec-detected
        finally:
            # Always restore the original working directory
            os.chdir(original_cwd)

        # Cancel the alarm
        signal.alarm(0)

        # Check if the file was created
        png_path = f'{output_path}.png'
        if os.path.exists(png_path):
            # Read the image file and encode as base64
            import base64
            with open(png_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')

            # Convert DOT to .drawio format if DOT file exists
            dot_path = f'{output_path}.dot'
            drawio_path = None
            if os.path.exists(dot_path):
                try:
                    from graphviz2drawio import graphviz2drawio

                    drawio_path = f'{output_path}.drawio'
                    # Convert DOT to .drawio
                    xml = graphviz2drawio.convert(dot_path)
                    with open(drawio_path, 'w') as f:
                        f.write(xml)
                    logger.info(f'Successfully converted DOT to draw.io format: {drawio_path}')
                except Exception as e:
                    logger.warning(f'Failed to convert DOT to draw.io format: {e}')
                    # Non-fatal error - we still have the PNG

            response = DiagramGenerateResponse(
                status='success',
                path=png_path,
                message=f'Diagram generated successfully at {png_path}',
                image_data=image_data,
                mime_type='image/png',
                drawio_path=drawio_path,
            )

            return response
        else:
            return DiagramGenerateResponse(
                status='error',
                message='Diagram file was not created. Check your code for errors.',
            )
    except TimeoutError as e:
        return DiagramGenerateResponse(status='error', message=str(e))
    except Exception as e:
        # More detailed error logging
        error_type = type(e).__name__
        error_message = str(e)
        return DiagramGenerateResponse(
            status='error', message=f'Error generating diagram: {error_type}: {error_message}'
        )


def get_diagram_examples(diagram_type: DiagramType = DiagramType.ALL) -> DiagramExampleResponse:
    """Get example code for different types of diagrams.

    Args:
        diagram_type: Type of diagram example to return.

    Returns:
        DiagramExampleResponse: Dictionary with example code for the requested diagram type(s)
    """
    examples = {}

    # Basic examples
    if diagram_type in [DiagramType.AWS, DiagramType.ALL]:
        examples['aws_basic'] = """with Diagram("Web Service Architecture", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""

    if diagram_type in [DiagramType.SEQUENCE, DiagramType.ALL]:
        examples['sequence'] = """with Diagram("User Authentication Flow", show=False):
    user = User("User")
    login = InputOutput("Login Form")
    auth = Decision("Authenticated?")
    success = Action("Access Granted")
    failure = Action("Access Denied")

    user >> login >> auth
    auth >> success
    auth >> failure
"""

    if diagram_type in [DiagramType.FLOW, DiagramType.ALL]:
        examples['flow'] = """with Diagram("Order Processing Flow", show=False):
    start = Predefined("Start")
    order = InputOutput("Order Received")
    check = Decision("In Stock?")
    process = Action("Process Order")
    wait = Delay("Backorder")
    ship = Action("Ship Order")
    end = Predefined("End")

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
"""

    if diagram_type in [DiagramType.CLASS, DiagramType.ALL]:
        examples['class'] = """with Diagram("Simple Class Diagram", show=False):
    base = Python("BaseClass")
    child1 = Python("ChildClass1")
    child2 = Python("ChildClass2")

    base >> child1
    base >> child2
"""

    # Advanced examples from the documentation
    if diagram_type in [DiagramType.AWS, DiagramType.ALL]:
        examples[
            'aws_grouped_workers'
        ] = """with Diagram("Grouped Workers", show=False, direction="TB"):
    ELB("lb") >> [EC2("worker1"),
                  EC2("worker2"),
                  EC2("worker3"),
                  EC2("worker4"),
                  EC2("worker5")] >> RDS("events")
"""

        examples[
            'aws_clustered_web_services'
        ] = """with Diagram("Clustered Web Services", show=False):
    dns = Route53("dns")
    lb = ELB("lb")

    with Cluster("Services"):
        svc_group = [ECS("web1"),
                     ECS("web2"),
                     ECS("web3")]

    with Cluster("DB Cluster"):
        db_primary = RDS("userdb")
        db_primary - [RDS("userdb ro")]

    memcached = ElastiCache("memcached")

    dns >> lb >> svc_group
    svc_group >> db_primary
    svc_group >> memcached
"""

        examples['aws_event_processing'] = """with Diagram("Event Processing", show=False):
    source = EKS("k8s source")

    with Cluster("Event Flows"):
        with Cluster("Event Workers"):
            workers = [ECS("worker1"),
                       ECS("worker2"),
                       ECS("worker3")]

        queue = SQS("event queue")

        with Cluster("Processing"):
            handlers = [Lambda("proc1"),
                        Lambda("proc2"),
                        Lambda("proc3")]

    store = S3("events store")
    dw = Redshift("analytics")

    source >> workers >> queue >> handlers
    handlers >> store
    handlers >> dw
"""

        examples[
            'aws_bedrock'
        ] = """with Diagram("S3 Image Processing with Bedrock", show=False, direction="LR"):
    user = User("User")

    with Cluster("Amazon S3 Bucket"):
        input_folder = S3("Input Folder")
        output_folder = S3("Output Folder")

    lambda_function = Lambda("Image Processor Function")
    bedrock = Bedrock("Claude Sonnet 3.7")

    user >> Edge(label="Upload Image") >> input_folder
    input_folder >> Edge(label="Trigger") >> lambda_function
    lambda_function >> Edge(label="Process Image") >> bedrock
    bedrock >> Edge(label="Return Bounding Box") >> lambda_function
    lambda_function >> Edge(label="Upload Processed Image") >> output_folder
    output_folder >> Edge(label="Download Result") >> user
"""

    if diagram_type in [DiagramType.K8S, DiagramType.ALL]:
        examples['k8s_exposed_pod'] = """with Diagram("Exposed Pod with 3 Replicas", show=False):
    net = Ingress("domain.com") >> Service("svc")
    net >> [Pod("pod1"),
            Pod("pod2"),
            Pod("pod3")] << ReplicaSet("rs") << Deployment("dp") << HPA("hpa")
"""

        examples['k8s_stateful'] = """with Diagram("Stateful Architecture", show=False):
    with Cluster("Apps"):
        svc = Service("svc")
        sts = StatefulSet("sts")

        apps = []
        for _ in range(3):
            pod = Pod("pod")
            pvc = PVC("pvc")
            pod - sts - pvc
            apps.append(svc >> pod >> pvc)

    apps << PV("pv") << StorageClass("sc")
"""

    if diagram_type in [DiagramType.ONPREM, DiagramType.ALL]:
        examples[
            'onprem_web_service'
        ] = """with Diagram("Advanced Web Service with On-Premises", show=False):
    ingress = Nginx("ingress")

    metrics = Prometheus("metric")
    metrics << Grafana("monitoring")

    with Cluster("Service Cluster"):
        grpcsvc = [
            Server("grpc1"),
            Server("grpc2"),
            Server("grpc3")]

    with Cluster("Sessions HA"):
        primary = Redis("session")
        primary - Redis("replica") << metrics
        grpcsvc >> primary

    with Cluster("Database HA"):
        primary = PostgreSQL("users")
        primary - PostgreSQL("replica") << metrics
        grpcsvc >> primary

    aggregator = Fluentd("logging")
    aggregator >> Kafka("stream") >> Spark("analytics")

    ingress >> grpcsvc >> aggregator
"""

        examples[
            'onprem_web_service_colored'
        ] = """with Diagram(name="Advanced Web Service with On-Premise (colored)", show=False):
    ingress = Nginx("ingress")

    metrics = Prometheus("metric")
    metrics << Edge(color="firebrick", style="dashed") << Grafana("monitoring")

    with Cluster("Service Cluster"):
        grpcsvc = [
            Server("grpc1"),
            Server("grpc2"),
            Server("grpc3")]

    with Cluster("Sessions HA"):
        primary = Redis("session")
        primary - Edge(color="brown", style="dashed") - Redis("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="brown") >> primary

    with Cluster("Database HA"):
        primary = PostgreSQL("users")
        primary - Edge(color="brown", style="dotted") - PostgreSQL("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="black") >> primary

    aggregator = Fluentd("logging")
    aggregator >> Edge(label="parse") >> Kafka("stream") >> Edge(color="black", style="bold") >> Spark("analytics")

    ingress >> Edge(color="darkgreen") << grpcsvc >> Edge(color="darkorange") >> aggregator
"""

    if diagram_type in [DiagramType.CUSTOM, DiagramType.ALL]:
        examples['custom_rabbitmq'] = """# Download an image to be used into a Custom Node class
rabbitmq_url = "https://jpadilla.github.io/rabbitmqapp/assets/img/icon.png"
rabbitmq_icon = "rabbitmq.png"
urlretrieve(rabbitmq_url, rabbitmq_icon)

with Diagram("Broker Consumers", show=False):
    with Cluster("Consumers"):
        consumers = [
            Pod("worker"),
            Pod("worker"),
            Pod("worker")]

    queue = Custom("Message queue", rabbitmq_icon)

    queue >> consumers >> Aurora("Database")
"""

    # GCP examples
    if diagram_type in [DiagramType.GCP, DiagramType.ALL]:
        # Three-tier serverless architecture following GCP best practices
        examples['gcp_basic'] = """with Diagram("GCP Serverless Application", show=False, direction="TB"):
    with Cluster("Production Project"):
        with Cluster("API Layer"):
            endpoints = Endpoints("Cloud Endpoints")
            gateway = APIGateway("API Gateway")

        with Cluster("Application Layer"):
            with Cluster("Cloud Run Functions"):
                api_handler = Functions("api-handler")
                async_worker = Functions("async-worker")
                trigger_fn = Functions("storage-trigger")

            events = PubSub("event-bus")

        with Cluster("Data Layer"):
            firestore = Firestore("documents")
            storage = Storage("objects")
            cache = Memorystore("cache")

    endpoints >> gateway >> api_handler
    api_handler >> firestore
    api_handler >> cache >> firestore
    api_handler >> events >> async_worker
    storage >> trigger_fn >> events
"""

        examples['gcp_data_pipeline'] = """with Diagram("GCP Data Pipeline", show=False, direction="LR"):
    with Cluster("Analytics Project"):
        source = PubSub("events")

        with Cluster("VPC Network"):
            with Cluster("Processing Subnet"):
                dataflow = Dataflow("transform")
                dataproc = Dataproc("batch")

        warehouse = BigQuery("analytics")
        viz = Datalab("analysis")

    source >> [dataflow, dataproc] >> warehouse >> viz
"""

        examples['gcp_microservices'] = """with Diagram("GCP Microservices Architecture", show=False):
    lb = LoadBalancing("load balancer")

    with Cluster("Production Project"):
        with Cluster("VPC Network"):
            with Cluster("us-central1 Subnet"):
                services = [
                    Run("auth-service"),
                    Run("user-service"),
                    Run("order-service")
                ]

            with Cluster("Data Subnet"):
                sql = SQL("users")
                firestore = Firestore("orders")
                cache = Memorystore("cache")

        queue = PubSub("events")

    lb >> services
    services[0] >> sql
    services[1] >> cache >> sql
    services[2] >> firestore
    services >> queue
"""

        # MLOps architecture with Vertex AI Pipelines following Google Cloud best practices
        examples['gcp_ml_pipeline'] = """with Diagram("GCP MLOps Pipeline", show=False, direction="LR"):
    with Cluster("ML Project"):
        with Cluster("Data Sources"):
            bq_source = BigQuery("feature store")
            gcs_data = Storage("training data")

        with Cluster("Development"):
            notebooks = AIPlatform("Vertex Workbench")
            experiments = AIPlatform("Experiments")

        with Cluster("CI/CD Pipeline"):
            source = SourceRepositories("pipeline code")
            build = Build("Cloud Build")
            registry = ContainerRegistry("Artifact Registry")

        with Cluster("Vertex AI Pipelines"):
            pipeline = Dataflow("training pipeline")
            train = AIPlatform("model training")
            evaluate = AIPlatform("evaluation")
            model_registry = AIPlatform("Model Registry")

        with Cluster("Serving"):
            endpoint = AIPlatform("prediction endpoint")
            monitor = Logging("model monitoring")

    [bq_source, gcs_data] >> notebooks >> experiments
    experiments >> source >> build >> registry
    registry >> pipeline >> train >> evaluate >> model_registry
    model_registry >> endpoint >> monitor
"""

        # Event-driven architecture with Pub/Sub, Cloud Run functions, and error handling
        examples['gcp_event_driven'] = """with Diagram("GCP Event-Driven Architecture", show=False, direction="LR"):
    with Cluster("Events Project"):
        with Cluster("Event Sources"):
            user_events = PubSub("user-events")
            storage_events = Storage("file uploads")
            scheduler = Scheduler("cron triggers")

        with Cluster("Event Routing"):
            main_topic = PubSub("event-router")
            dead_letter = PubSub("dead-letter-topic")
            dlq_handler = Functions("dlq-processor")

        with Cluster("Event Handlers (Cloud Run)"):
            with Cluster("Notification Service"):
                notif = Run("notifications")
            with Cluster("Analytics Service"):
                analytics = Run("analytics-processor")
            with Cluster("Audit Service"):
                audit = Run("audit-logger")

        with Cluster("State Management"):
            state = Firestore("event-state")
            cache = Memorystore("dedup-cache")

        monitoring = Monitoring("alerts")
        logs = Logging("event-logs")

    [user_events, storage_events, scheduler] >> main_topic
    main_topic >> [notif, analytics, audit]
    main_topic >> Edge(style="dashed", label="failed") >> dead_letter >> dlq_handler
    [notif, analytics, audit] >> cache >> state
    [notif, analytics, audit] >> logs >> monitoring
"""

        # IoT streaming architecture with proper data flow and processing tiers
        examples['gcp_iot_streaming'] = """with Diagram("GCP IoT Streaming Platform", show=False, direction="LR"):
    with Cluster("IoT Project"):
        with Cluster("Device Layer"):
            devices = IotCore("IoT Core Registry")
            telemetry = PubSub("telemetry-topic")
            commands = PubSub("command-topic")

        with Cluster("Stream Processing Layer"):
            with Cluster("Dataflow Jobs"):
                hot_path = Dataflow("real-time aggregation")
                cold_path = Dataflow("batch enrichment")

            with Cluster("Alert Processing"):
                alert_fn = Functions("threshold-alerts")
                ml_inference = AIPlatform("anomaly detection")

        with Cluster("Storage Layer"):
            time_series = Bigtable("time-series-db")
            warehouse = BigQuery("analytics-warehouse")
            archive = Storage("cold-storage")

        with Cluster("Visualization"):
            dashboard = Datalab("dashboards")
            monitoring = Monitoring("alerts")

    devices >> telemetry >> hot_path
    hot_path >> time_series >> dashboard
    hot_path >> alert_fn >> monitoring
    hot_path >> ml_inference
    telemetry >> cold_path >> warehouse >> dashboard
    cold_path >> archive
    commands >> devices
"""

        # Shared VPC example showing GCP networking best practices
        examples['gcp_shared_vpc'] = """with Diagram("GCP Shared VPC Architecture", show=False, direction="TB"):
    interconnect = DedicatedInterconnect("Cloud Interconnect")

    with Cluster("Shared VPC Host Project"):
        with Cluster("Shared VPC Network"):
            with Cluster("us-central1"):
                prod_subnet = VPC("prod-subnet\\n10.0.1.0/24")
                dev_subnet = VPC("dev-subnet\\n10.0.2.0/24")

            with Cluster("us-east1"):
                dr_subnet = VPC("dr-subnet\\n10.0.3.0/24")

            nat = NAT("Cloud NAT")
            fw = FirewallRules("Firewall Rules")

    with Cluster("Production Service Project"):
        with Cluster("GKE Cluster"):
            prod_gke = GKE("prod-cluster")
            prod_nodes = [
                ComputeEngine("node-1"),
                ComputeEngine("node-2")
            ]

    with Cluster("Development Service Project"):
        dev_run = Run("dev-services")
        dev_sql = SQL("dev-db")

    interconnect >> fw >> prod_subnet
    prod_subnet >> prod_gke >> prod_nodes
    dev_subnet >> dev_run >> dev_sql
    [prod_subnet, dev_subnet] >> nat
"""

    # Azure examples
    if diagram_type in [DiagramType.AZURE, DiagramType.ALL]:
        examples['azure_basic'] = """with Diagram("Azure Web Application", show=False):
    AppServices("web app") >> SQLServers("database") >> BlobStorage("storage")
"""

        examples['azure_serverless'] = """with Diagram("Azure Serverless Architecture", show=False, direction="LR"):
    http = APIManagement("api gateway")
    func = FunctionApps("business logic")

    with Cluster("Data Layer"):
        cosmos = CosmosDb("documents")
        cache = CacheForRedis("cache")

    events = EventHubs("event stream")

    http >> func >> cosmos
    func >> cache
    func >> events
"""

        examples['azure_microservices'] = """with Diagram("Azure Microservices on AKS", show=False):
    gateway = ApplicationGateway("gateway")
    aks = KubernetesServices("AKS cluster")

    with Cluster("Services"):
        services = [
            ContainerInstances("auth"),
            ContainerInstances("orders"),
            ContainerInstances("payments")
        ]

    with Cluster("Databases"):
        sql = SQLServers("users")
        cosmos = CosmosDb("orders")

    monitor = LogAnalyticsWorkspaces("monitoring")
    registry = ContainerRegistries("images")

    gateway >> aks >> services
    services[0] >> sql
    services[1] >> cosmos
    services >> monitor
    registry >> aks
"""

        examples['azure_data_platform'] = """with Diagram("Azure Data Platform", show=False, direction="TB"):
    sources = [
        BlobStorage("raw data"),
        EventHubs("streaming")
    ]

    with Cluster("Processing"):
        databricks = Databricks("transform")
        synapse = SynapseAnalytics("warehouse")

    analysis = AnalysisServices("analytics")

    sources >> databricks >> synapse >> analysis
"""

        examples['azure_event_driven'] = """with Diagram("Azure Event-Driven Microservices", show=False, direction="LR"):
    gateway = APIManagement("api gateway")

    with Cluster("Event Bus"):
        events = EventHubs("event stream")
        grid = EventGridTopics("event routing")

    with Cluster("Microservices"):
        services = [
            FunctionApps("orders"),
            FunctionApps("inventory"),
            FunctionApps("shipping")
        ]

    with Cluster("State"):
        cosmos = CosmosDb("event store")
        queue = ServiceBus("saga coordinator")

    gateway >> services[0] >> events
    events >> grid >> services[1:]
    services >> cosmos
    services >> queue
"""

        examples['azure_ntier'] = """with Diagram("Azure N-Tier Application", show=False, direction="TB"):
    users = TrafficManagerProfiles("global traffic")

    with Cluster("Presentation Tier"):
        web = AppServices("web app")
        cdn = CDNProfiles("static content")

    with Cluster("Application Tier"):
        lb = ApplicationGateway("load balancer")
        apps = [
            VM("app server 1"),
            VM("app server 2"),
            VM("app server 3")
        ]

    with Cluster("Data Tier"):
        primary = SQLServers("primary db")
        replica = SQLServers("read replica")
        cache = CacheForRedis("cache")

    users >> [web, cdn]
    web >> lb >> apps
    apps >> cache >> primary
    primary >> Edge(style="dashed") >> replica
"""

        examples['azure_iot_edge'] = """with Diagram("Azure IoT Edge Solution", show=False, direction="LR"):
    devices = IotCentralApplications("iot devices")
    hub = IotHub("iot hub")

    with Cluster("Stream Analytics"):
        stream = StreamAnalyticsJobs("hot path")
        batch = DataLakeStorage("cold path")

    with Cluster("Processing"):
        functions = FunctionApps("event processing")
        ml = MachineLearningServiceWorkspaces("ml inference")

    with Cluster("Storage & Visualization"):
        cosmos = CosmosDb("time series")
        insights = TimeSeriesInsightsEnvironments("analytics")

    devices >> hub >> [stream, batch]
    stream >> functions >> cosmos
    stream >> ml
    cosmos >> insights
"""

    # Hybrid cloud examples
    if diagram_type in [DiagramType.HYBRID, DiagramType.ALL]:
        examples['hybrid_aws_onprem'] = """with Diagram("Hybrid Cloud Architecture", show=False, direction="LR"):
    with Cluster("On-Premises Data Center"):
        onprem_db = PostgreSQL("legacy db")
        onprem_app = Server("legacy app")

    vpn = VPN("site-to-site")

    with Cluster("AWS Cloud"):
        vpc = VPC("vpc")
        with Cluster("Application Tier"):
            alb = ELB("load balancer")
            apps = [
                EC2("app1"),
                EC2("app2")
            ]
        rds = RDS("cloud db")

    onprem_app >> vpn >> vpc >> alb >> apps
    apps >> rds
    apps >> Edge(label="sync") >> onprem_db
"""

        examples['hybrid_k8s_cloud'] = """with Diagram("Hybrid Kubernetes Setup", show=False):
    with Cluster("On-Premises"):
        onprem_k8s = Server("k8s master")
        onprem_workers = [
            Server("worker1"),
            Server("worker2")
        ]
        onprem_storage = Storage("nfs")

    with Cluster("Cloud"):
        cloud_k8s = EKS("eks cluster")
        cloud_storage = S3("object storage")

    mesh = Istio("service mesh")

    onprem_k8s >> onprem_workers >> onprem_storage
    cloud_k8s >> cloud_storage
    onprem_k8s >> Edge(label="federation") >> mesh >> cloud_k8s
"""

        examples['hybrid_disaster_recovery'] = """with Diagram("Hybrid DR Architecture", show=False, direction="TB"):
    with Cluster("Primary Site (On-Prem)"):
        primary_lb = Nginx("load balancer")
        primary_app = [Server("app1"), Server("app2")]
        primary_db = PostgreSQL("primary db")

    replication = Edge(label="continuous replication", style="dashed")

    with Cluster("DR Site (Cloud)"):
        dr_lb = ELB("standby lb")
        dr_app = [EC2("standby1"), EC2("standby2")]
        dr_db = RDS("replica db")

    dns = Route53("dns failover")

    dns >> primary_lb >> primary_app >> primary_db
    primary_db >> replication >> dr_db
    dns >> Edge(style="dotted") >> dr_lb >> dr_app >> dr_db
"""

    # Multi-cloud examples
    if diagram_type in [DiagramType.MULTICLOUD, DiagramType.ALL]:
        examples['multicloud_global_app'] = """with Diagram("Multi-Cloud Global Application", show=False, direction="LR"):
    dns = Route53("global dns")

    with Cluster("AWS Region (US)"):
        aws_lb = ELB("alb")
        aws_app = [EC2("app1"), EC2("app2")]
        aws_db = RDS("primary db")

    with Cluster("GCP Region (EU)"):
        gcp_lb = LoadBalancing("lb")
        gcp_app = [Run("app1"), Run("app2")]
        gcp_db = SQL("replica db")

    with Cluster("Azure Region (APAC)"):
        azure_lb = ApplicationGateway("gateway")
        azure_app = [AppServices("app1"), AppServices("app2")]
        azure_db = SQLServers("read replica")

    dns >> [aws_lb, gcp_lb, azure_lb]
    aws_lb >> aws_app >> aws_db
    gcp_lb >> gcp_app >> gcp_db
    azure_lb >> azure_app >> azure_db
    aws_db >> Edge(label="replication", style="dashed") >> [gcp_db, azure_db]
"""

        examples['multicloud_data_mesh'] = """with Diagram("Multi-Cloud Data Mesh", show=False, direction="TB"):
    with Cluster("Data Sources"):
        aws_source = S3("aws data lake")
        gcp_source = Storage("gcp data lake")
        azure_source = BlobStorage("azure data lake")

    with Cluster("Processing Layer"):
        aws_proc = Glue("aws etl")
        gcp_proc = Dataflow("gcp pipeline")
        azure_proc = Databricks("azure transform")

    with Cluster("Analytics"):
        aws_analytics = Athena("aws query")
        gcp_analytics = BigQuery("gcp warehouse")
        azure_analytics = SynapseAnalytics("azure analytics")

    unified = Grafana("unified dashboard")

    aws_source >> aws_proc >> aws_analytics
    gcp_source >> gcp_proc >> gcp_analytics
    azure_source >> azure_proc >> azure_analytics
    [aws_analytics, gcp_analytics, azure_analytics] >> unified
"""

        examples['multicloud_cicd'] = """with Diagram("Multi-Cloud CI/CD Pipeline", show=False, direction="LR"):
    repo = Github("source code")
    cicd = Jenkins("ci/cd")

    with Cluster("Build & Registry"):
        build = Docker("build")
        aws_registry = ECR("aws ecr")
        gcp_registry = ContainerRegistry("gcp registry")
        azure_registry = ContainerRegistries("azure acr")

    with Cluster("Deployment Targets"):
        aws_deploy = EKS("aws eks")
        gcp_deploy = GKE("gcp gke")
        azure_deploy = KubernetesServices("azure aks")

    monitor = Datadog("monitoring")

    repo >> cicd >> build
    build >> [aws_registry, gcp_registry, azure_registry]
    aws_registry >> aws_deploy
    gcp_registry >> gcp_deploy
    azure_registry >> azure_deploy
    [aws_deploy, gcp_deploy, azure_deploy] >> monitor
"""

    return DiagramExampleResponse(examples=examples)


def list_diagram_icons(
    provider_filter: Optional[str] = None, service_filter: Optional[str] = None
) -> DiagramIconsResponse:
    """List available icons from the diagrams package, with optional filtering.

    Args:
        provider_filter: Optional filter by provider name (e.g., "aws", "gcp")
        service_filter: Optional filter by service name (e.g., "compute", "database")

    Returns:
        DiagramIconsResponse: Dictionary with available providers, services, and icons
    """
    logger.debug('Starting list_diagram_icons function')
    logger.debug(f'Filters - provider: {provider_filter}, service: {service_filter}')

    try:
        # If no filters provided, just return the list of available providers
        if not provider_filter and not service_filter:
            # Get the base path of the diagrams package
            diagrams_path = os.path.dirname(diagrams.__file__)
            providers = {}

            # List of provider directories to exclude
            exclude_dirs = ['__pycache__', '_template']

            # Just list the available providers without their services/icons
            for provider_name in os.listdir(os.path.join(diagrams_path)):
                provider_path = os.path.join(diagrams_path, provider_name)

                # Skip non-directories and excluded directories
                if (
                    not os.path.isdir(provider_path)
                    or provider_name.startswith('_')
                    or provider_name in exclude_dirs
                ):
                    continue

                # Add provider to the dictionary with empty services
                providers[provider_name] = {}

            return DiagramIconsResponse(providers=providers, filtered=False, filter_info=None)

        # Dictionary to store filtered providers and their services/icons
        providers = {}

        # Get the base path of the diagrams package
        diagrams_path = os.path.dirname(diagrams.__file__)

        # List of provider directories to exclude
        exclude_dirs = ['__pycache__', '_template']

        # If only provider filter is specified
        if provider_filter and not service_filter:
            provider_path = os.path.join(diagrams_path, provider_filter)

            # Check if the provider exists
            if not os.path.isdir(provider_path) or provider_filter in exclude_dirs:
                return DiagramIconsResponse(
                    providers={},
                    filtered=True,
                    filter_info={'provider': provider_filter, 'error': 'Provider not found'},
                )

            # Add provider to the dictionary
            providers[provider_filter] = {}

            # Iterate through all service modules in the provider
            for service_file in os.listdir(provider_path):
                # Skip non-Python files and special files
                if not service_file.endswith('.py') or service_file.startswith('_'):
                    continue

                service_name = service_file[:-3]  # Remove .py extension

                # Import the service module
                module_path = f'diagrams.{provider_filter}.{service_name}'
                try:
                    service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                        module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                    )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

                    # Find all classes in the module that are Node subclasses
                    icons = []
                    for name, obj in inspect.getmembers(service_module):
                        # Skip private members and imported modules
                        if name.startswith('_') or inspect.ismodule(obj):
                            continue

                        # Check if it's a class and likely a Node subclass
                        if inspect.isclass(obj) and hasattr(obj, '_icon'):
                            icons.append(name)

                    # Add service and its icons to the provider
                    if icons:
                        providers[provider_filter][service_name] = sorted(icons)

                except (ImportError, AttributeError, Exception) as e:
                    logger.error(f'Error processing {module_path}: {str(e)}')
                    continue

            return DiagramIconsResponse(
                providers=providers, filtered=True, filter_info={'provider': provider_filter}
            )

        # If both provider and service filters are specified
        elif provider_filter and service_filter:
            provider_path = os.path.join(diagrams_path, provider_filter)

            # Check if the provider exists
            if not os.path.isdir(provider_path) or provider_filter in exclude_dirs:
                return DiagramIconsResponse(
                    providers={},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': 'Provider not found',
                    },
                )

            # Add provider to the dictionary
            providers[provider_filter] = {}

            # Check if the service exists
            service_file = f'{service_filter}.py'
            service_path = os.path.join(provider_path, service_file)

            if not os.path.isfile(service_path):
                return DiagramIconsResponse(
                    providers={provider_filter: {}},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': 'Service not found',
                    },
                )

            # Import the service module
            module_path = f'diagrams.{provider_filter}.{service_filter}'
            try:
                service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                    module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

                # Find all classes in the module that are Node subclasses
                icons = []
                for name, obj in inspect.getmembers(service_module):
                    # Skip private members and imported modules
                    if name.startswith('_') or inspect.ismodule(obj):
                        continue

                    # Check if it's a class and likely a Node subclass
                    if inspect.isclass(obj) and hasattr(obj, '_icon'):
                        icons.append(name)

                # Add service and its icons to the provider
                if icons:
                    providers[provider_filter][service_filter] = sorted(icons)

            except (ImportError, AttributeError, Exception) as e:
                logger.error(f'Error processing {module_path}: {str(e)}')
                return DiagramIconsResponse(
                    providers={provider_filter: {}},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': f'Error loading service: {str(e)}',
                    },
                )

            return DiagramIconsResponse(
                providers=providers,
                filtered=True,
                filter_info={'provider': provider_filter, 'service': service_filter},
            )

        # If only service filter is specified (not supported)
        elif service_filter:
            return DiagramIconsResponse(
                providers={},
                filtered=True,
                filter_info={
                    'service': service_filter,
                    'error': 'Service filter requires provider filter',
                },
            )

        # Original implementation for backward compatibility
        else:
            # Dictionary to store all providers and their services/icons
            providers = {}

            # Get the base path of the diagrams package
            diagrams_path = os.path.dirname(diagrams.__file__)
            logger.debug(f'Diagrams package path: {diagrams_path}')

            # Iterate through all provider directories
            for provider_name in os.listdir(os.path.join(diagrams_path)):
                provider_path = os.path.join(diagrams_path, provider_name)

                # Skip non-directories and excluded directories
                if (
                    not os.path.isdir(provider_path)
                    or provider_name.startswith('_')
                    or provider_name in exclude_dirs
                ):
                    logger.debug(f'Skipping {provider_name}: not a directory or in exclude list')
                    continue

                # Add provider to the dictionary
                providers[provider_name] = {}
                logger.debug(f'Processing provider: {provider_name}')

                # Iterate through all service modules in the provider
                for service_file in os.listdir(provider_path):
                    # Skip non-Python files and special files
                    if not service_file.endswith('.py') or service_file.startswith('_'):
                        logger.debug(
                            f'Skipping file {service_file}: not a Python file or starts with _'
                        )
                        continue

                    service_name = service_file[:-3]  # Remove .py extension
                    logger.debug(f'Processing service: {provider_name}.{service_name}')

                    # Import the service module
                    module_path = f'diagrams.{provider_name}.{service_name}'
                    try:
                        logger.debug(f'Attempting to import module: {module_path}')
                        service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                            module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                        )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

                        # Find all classes in the module that are Node subclasses
                        icons = []
                        for name, obj in inspect.getmembers(service_module):
                            # Skip private members and imported modules
                            if name.startswith('_') or inspect.ismodule(obj):
                                continue

                            # Check if it's a class and likely a Node subclass
                            if inspect.isclass(obj) and hasattr(obj, '_icon'):
                                icons.append(name)
                                logger.debug(f'Found icon: {name}')

                        # Add service and its icons to the provider
                        if icons:
                            providers[provider_name][service_name] = sorted(icons)
                            logger.debug(
                                f'Added {len(icons)} icons for {provider_name}.{service_name}'
                            )
                        else:
                            logger.warning(f'No icons found for {provider_name}.{service_name}')

                    except ImportError as ie:
                        logger.error(f'ImportError for {module_path}: {str(ie)}')
                        continue
                    except AttributeError as ae:
                        logger.error(f'AttributeError for {module_path}: {str(ae)}')
                        continue
                    except Exception as e:
                        logger.error(f'Unexpected error processing {module_path}: {str(e)}')
                        continue

            logger.debug(f'Completed processing. Found {len(providers)} providers')
            return DiagramIconsResponse(providers=providers, filtered=False, filter_info=None)

    except Exception as e:
        logger.exception(f'Error in list_diagram_icons: {str(e)}')
        # Return empty response on error
        return DiagramIconsResponse(providers={}, filtered=False, filter_info={'error': str(e)})
