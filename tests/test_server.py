# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Modifications Copyright 2025 Andrii Moshurenko
# - Updated module paths and MCP response types
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
#

"""Tests for the server module of the diagrams-mcp-server."""

import os
import pytest
import tempfile
from infrastructure_diagram_mcp_server.models import DiagramType
from infrastructure_diagram_mcp_server.server import (
    mcp_generate_diagram,
    mcp_get_diagram_examples,
    mcp_list_diagram_icons,
)
from mcp.types import TextContent, ImageContent
from unittest.mock import AsyncMock, MagicMock, patch


class TestMcpGenerateDiagram:
    """Tests for the mcp_generate_diagram function."""

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function."""
        # Set up the mock to return a proper response object
        mock_result = MagicMock()
        mock_result.status = 'success'
        mock_result.path = os.path.join(tempfile.gettempdir(), 'diagram.png')
        mock_result.message = 'Diagram generated successfully'
        mock_result.image_data = 'base64encodeddata'
        mock_result.mime_type = 'image/png'
        mock_result.drawio_path = None
        mock_generate_diagram.return_value = mock_result

        # Call the function
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            filename='test',
            timeout=60,
            workspace_dir=tempfile.gettempdir(),
        )

        # Check the result is a list with TextContent and ImageContent
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], TextContent)
        assert isinstance(result[1], ImageContent)
        assert 'Diagram generated successfully' in result[0].text
        assert result[1].data == 'base64encodeddata'

        # Check that generate_diagram was called with the correct arguments
        mock_generate_diagram.assert_called_once_with(
            'with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
            'test',
            60,
            tempfile.gettempdir(),
        )

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_with_defaults(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function with default values."""
        # Set up the mock to return a proper response object
        mock_result = MagicMock()
        mock_result.status = 'success'
        mock_result.path = os.path.join(tempfile.gettempdir(), 'diagram.png')
        mock_result.message = 'Diagram generated successfully'
        mock_result.image_data = 'base64encodeddata'
        mock_result.mime_type = 'image/png'
        mock_result.drawio_path = None
        mock_generate_diagram.return_value = mock_result

        # Call the function with only the required arguments
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
        )

        # Check the result is a list with TextContent and ImageContent
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], TextContent)
        assert 'Diagram generated successfully' in result[0].text

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.generate_diagram')
    async def test_generate_diagram_error(self, mock_generate_diagram):
        """Test the mcp_generate_diagram function with an error."""
        # Set up the mock to return an error response
        mock_result = MagicMock()
        mock_result.status = 'error'
        mock_result.path = None
        mock_result.message = 'Error generating diagram'
        mock_result.image_data = None
        mock_generate_diagram.return_value = mock_result

        # Call the function
        result = await mcp_generate_diagram(
            code='with Diagram("Test", show=False):\n    ELB("lb") >> EC2("web")',
        )

        # Check the result is a list with just TextContent containing error
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error' in result[0].text


class TestMcpGetDiagramExamples:
    """Tests for the mcp_get_diagram_examples function."""

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples(self, mock_get_diagram_examples):
        """Test the mcp_get_diagram_examples function."""
        # Set up the mock
        mock_get_diagram_examples.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'examples': {
                        'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                        'sequence': 'with Diagram("Sequence", show=False):\n    User("user") >> Action("action")',
                    }
                }
            )
        )

        # Call the function
        result = await mcp_get_diagram_examples(diagram_type=DiagramType.ALL)

        # Check the result
        assert result == {
            'examples': {
                'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                'sequence': 'with Diagram("Sequence", show=False):\n    User("user") >> Action("action")',
            }
        }

        # Check that get_diagram_examples was called with the correct arguments
        mock_get_diagram_examples.assert_called_once_with(DiagramType.ALL)

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.get_diagram_examples')
    async def test_get_diagram_examples_with_specific_type(self, mock_get_diagram_examples):
        """Test the mcp_get_diagram_examples function with a specific diagram type."""
        # Set up the mock
        mock_get_diagram_examples.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'examples': {
                        'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
                    }
                }
            )
        )

        # Call the function
        result = await mcp_get_diagram_examples(diagram_type=DiagramType.AWS)

        # Check the result
        assert result == {
            'examples': {
                'aws': 'with Diagram("AWS", show=False):\n    ELB("lb") >> EC2("web")',
            }
        }

        # Check that get_diagram_examples was called with the correct arguments
        mock_get_diagram_examples.assert_called_once_with(DiagramType.AWS)


class TestMcpListDiagramIcons:
    """Tests for the mcp_list_diagram_icons function."""

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_without_filters(self, mock_list_diagram_icons):
        """Test the mcp_list_diagram_icons function without filters."""
        # Set up the mock
        mock_list_diagram_icons.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {
                        'aws': {},
                        'gcp': {},
                        'k8s': {},
                    },
                    'filtered': False,
                    'filter_info': None,
                }
            )
        )

        # Call the function
        result = await mcp_list_diagram_icons()

        # Check the result
        assert result == {
            'providers': {
                'aws': {},
                'gcp': {},
                'k8s': {},
            },
            'filtered': False,
            'filter_info': None,
        }

        # Check that list_diagram_icons was called
        mock_list_diagram_icons.assert_called_once()
        # We don't check the exact arguments because they are Field objects

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_with_provider_filter(self, mock_list_diagram_icons):
        """Test the mcp_list_diagram_icons function with provider filter."""
        # Set up the mock
        mock_list_diagram_icons.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {
                        'aws': {
                            'compute': ['EC2', 'Lambda'],
                            'database': ['RDS', 'DynamoDB'],
                        }
                    },
                    'filtered': True,
                    'filter_info': {'provider': 'aws'},
                }
            )
        )

        # Call the function
        result = await mcp_list_diagram_icons(provider_filter='aws')

        # Check the result
        assert result == {
            'providers': {
                'aws': {
                    'compute': ['EC2', 'Lambda'],
                    'database': ['RDS', 'DynamoDB'],
                }
            },
            'filtered': True,
            'filter_info': {'provider': 'aws'},
        }

        # Check that list_diagram_icons was called
        mock_list_diagram_icons.assert_called_once()
        # We don't check the exact arguments because they are Field objects
        # But we can check that the first argument contains 'aws'
        args, _ = mock_list_diagram_icons.call_args
        assert args[0] == 'aws'

    @pytest.mark.asyncio
    @patch('infrastructure_diagram_mcp_server.server.list_diagram_icons')
    async def test_list_diagram_icons_with_provider_and_service_filter(
        self, mock_list_diagram_icons
    ):
        """Test the mcp_list_diagram_icons function with provider and service filter."""
        # Set up the mock
        mock_list_diagram_icons.return_value = MagicMock(
            model_dump=MagicMock(
                return_value={
                    'providers': {
                        'aws': {
                            'compute': ['EC2', 'Lambda'],
                        }
                    },
                    'filtered': True,
                    'filter_info': {'provider': 'aws', 'service': 'compute'},
                }
            )
        )

        # Call the function
        result = await mcp_list_diagram_icons(provider_filter='aws', service_filter='compute')

        # Check the result
        assert result == {
            'providers': {
                'aws': {
                    'compute': ['EC2', 'Lambda'],
                }
            },
            'filtered': True,
            'filter_info': {'provider': 'aws', 'service': 'compute'},
        }

        # Check that list_diagram_icons was called
        mock_list_diagram_icons.assert_called_once()
        # We don't check the exact arguments because they are Field objects
        # But we can check that the arguments contain the expected values
        args, _ = mock_list_diagram_icons.call_args
        assert args[0] == 'aws'
        assert args[1] == 'compute'


class TestServerIntegration:
    """Integration tests for the server module."""

    @pytest.mark.asyncio
    async def test_server_tool_registration(self):
        """Test that the server tools are registered correctly."""
        # Check that the tools are registered
        # We can't directly access the tools, so we'll check if the functions are registered
        assert hasattr(mcp_generate_diagram, '__name__')
        assert hasattr(mcp_get_diagram_examples, '__name__')
        assert hasattr(mcp_list_diagram_icons, '__name__')

        # Check that the functions have the correct docstrings
        assert (
            mcp_generate_diagram.__doc__ is not None
            and 'Generate a diagram from Python code' in mcp_generate_diagram.__doc__
        )
        assert (
            mcp_get_diagram_examples.__doc__ is not None
            and 'Get example code for different types of diagrams'
            in mcp_get_diagram_examples.__doc__
        )
        assert (
            mcp_list_diagram_icons.__doc__ is not None
            and 'List available icons from the diagrams package, with optional filtering'
            in mcp_list_diagram_icons.__doc__
        )
