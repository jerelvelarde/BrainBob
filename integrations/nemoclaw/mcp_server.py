"""stdio only; NOT yet run inside a NemoClaw sandbox.

Override FastMCP dispatch so unknown fields cannot be silently discarded by
Pydantic coercion. Schemas and strict validation share the adapter contract.
"""
import json
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, Tool
from brainbob_tools import BrainBobTools, INPUT_SCHEMAS, OUTPUT_SCHEMAS


class BrainBobMCP(FastMCP):
    def __init__(self):
        self.adapter = BrainBobTools()
        super().__init__('BrainBob')

    async def list_tools(self):
        return [Tool(name=name, description={
            'read_memory': 'Read scoped memories ranked by keyword overlap; retired entries retain their status.',
            'read_source': 'Read an accessible source episode; never broaden identity.',
            'propose_memory': 'Submit a discussion episode, never an approved commitment.',
        }[name], inputSchema=schema, outputSchema=OUTPUT_SCHEMAS[name])
                for name, schema in INPUT_SCHEMAS.items()]

    async def call_tool(self, name, arguments):
        result = self.adapter.call(name, arguments)
        return ([TextContent(type='text', text=json.dumps(result))], result)


if __name__ == '__main__':
    BrainBobMCP().run(transport='stdio')
