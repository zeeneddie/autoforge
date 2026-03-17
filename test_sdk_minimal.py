"""Test: bundled CLI (no cli_path) vs system CLI - rate limit difference?"""
import asyncio
import sys
from pathlib import Path

async def main():
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    # Use bundled CLI (NO cli_path) - might have separate rate limit
    kwargs = {
        "model": "developer",
        "cwd": "/home/eddie/Projects/sudoku-solver",
        # NO cli_path - use SDK bundled CLI
    }

    print("Testing with bundled CLI (no cli_path)...")
    options = ClaudeAgentOptions(**kwargs)
    client = ClaudeSDKClient(options=options)

    await client.__aenter__()
    await client.query("Zeg alleen: het werkt")

    async for msg in client.receive_response():
        msg_type = type(msg).__name__
        if hasattr(msg, "content"):
            for block in msg.content:
                if hasattr(block, "text"):
                    print(f"   [{msg_type}] {block.text}")
        elif hasattr(msg, "subtype"):
            print(f"   [{msg_type}] {getattr(msg, 'subtype', '')}")

    print("Done!")
    await client.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(main())
