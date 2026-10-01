import os
import sys
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# Path configuration for the standalone MCP server built in Phase 2
MCP_SERVER_PYTHON = os.getenv(
    "MCP_SERVER_PYTHON",
    r"D:\Desktop\projects\docs-retriever-mcp\.venv\Scripts\python.exe"
)
MCP_SERVER_SCRIPT = os.getenv(
    "MCP_SERVER_SCRIPT",
    r"D:\Desktop\projects\docs-retriever-mcp\server.py"
)


async def _fetch_from_mcp_server(query: str, top_k: int = 3) -> list[str]:
    """Spawns the MCP server over stdio and executes the search_docs tool."""
    server_params = StdioServerParameters(
        command=MCP_SERVER_PYTHON,
        args=[MCP_SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection with the MCP server
            await session.initialize()

            # Execute the search_docs tool exposed by server.py
            result = await session.call_tool(
                name="search_docs",
                arguments={"query": query, "top_k": top_k}
            )

            if not result.content:
                return []

            # Extract formatted text from the tool call response
            raw_text = result.content[0].text

            # Split raw text into individual result chunks for the agent context
            raw_chunks = raw_text.split("--- Result ")
            chunks = [f"Result {c.strip()}" for c in raw_chunks if c.strip()]

            return chunks if chunks else [raw_text]


def get_relevant_docs(query: str, top_k: int = 3) -> list[str]:
    """
    Synchronous wrapper for Project 2's LangGraph retrieve_node.
    Calls the external MCP server over stdio instead of querying ChromaDB directly.
    """
    try:
        return asyncio.run(_fetch_from_mcp_server(query=query, top_k=top_k))
    except RuntimeError:
        # Handles environments with an already-running event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_fetch_from_mcp_server(query=query, top_k=top_k))


if __name__ == "__main__":
    test_query = "How to handle FastAPI internal server error?"
    print(f"Connecting to MCP server at: {MCP_SERVER_SCRIPT} via stdio...")
    results = get_relevant_docs(test_query)
    print(f"\n[MCP Client] Received {len(results)} chunks from server:")
    for idx, chunk in enumerate(results, 1):
        print(f"\n--- Chunk {idx} ---\n{chunk[:250]}...")