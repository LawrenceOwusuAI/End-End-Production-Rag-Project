# monitoring/mcp_tools.py
from __future__ import annotations
import os
from langchain.mcp import MCPAdapter

# MCP ENDPOINTS
PROMETHEUS_MCP_URL = os.getenv("PROMETHEUS_MCP_URL", "http://prometheus-mcp:8001/mcp")

OPENSEARCH_MCP_URL = os.getenv("OPENSEARCH_MCP_URL", "http://opensearch-mcp:8002/mcp")

# OBSERVABILITY TOOL MANAGER
class ObservabilityTools:
    def __init__(self):
        self.prometheus_adapter = None
        self.opensearch_adapter = None
        self.tools = []
    async def start(self):
        # CONNECT TO PROMETHEUS MCP
        self.prometheus_adapter = MCPAdapter(PROMETHEUS_MCP_URL)

        await (
            self.prometheus_adapter
            .__aenter__()
        )

        prometheus_tools = (
            await
            self.prometheus_adapter
            .list_tools()
        )

        # CONNECT TO OPENSEARCH MCP
        self.opensearch_adapter = MCPAdapter(OPENSEARCH_MCP_URL)
        await (
            self.opensearch_adapter
            .__aenter__()
        )

        opensearch_tools = (
            await
            self.opensearch_adapter
            .list_tools()
        )

        # COMBINE TOOLS
        self.tools = (prometheus_tools + opensearch_tools)
        return self.tools

    async def close(self):
        # CLOSE PROMETHEUS MCP
        if self.prometheus_adapter:
            await (
                self.prometheus_adapter
                .__aexit__(
                    None,
                    None,
                    None,
                )
            )

        # CLOSE OPENSEARCH MCP
        if self.opensearch_adapter:
            await (
                self.opensearch_adapter
                .__aexit__(
                    None,
                    None,
                    None,
                )
            )