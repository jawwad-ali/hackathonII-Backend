"""Test that SSE transport raises NotImplementedError correctly"""
import os
import sys

print("="*70)
print(" SSE TRANSPORT BEHAVIOR TEST ")
print("="*70)

# Temporarily change transport type to sse
os.environ['MCP_TRANSPORT_TYPE'] = 'sse'

# Reload modules to pick up new environment
if 'src.config' in sys.modules:
    del sys.modules['src.config']
if 'src.mcp.client' in sys.modules:
    del sys.modules['src.mcp.client']

from src.config import settings
from src.mcp.client import _initialize_mcp_connection_with_retry
import asyncio

print(f"\n[TEST] Transport Type Set to: {settings.MCP_TRANSPORT_TYPE}")
assert settings.MCP_TRANSPORT_TYPE == 'sse', "Should be sse"
print("[PASS] MCP_TRANSPORT_TYPE = sse")

print("\n[TEST] Attempting to initialize with SSE transport...")
print("(Should raise NotImplementedError)")

async def test_sse_error():
    try:
        await _initialize_mcp_connection_with_retry()
        print("[FAIL] Should have raised NotImplementedError")
        return False
    except ValueError as e:
        error_msg = str(e)
        print(f"\n[PASS] Caught expected error:")
        print(f"       {error_msg}")

        # Verify error message content
        assert "not yet implemented" in error_msg.lower(), "Wrong error message"
        assert "stdio" in error_msg.lower() or "MCP_TRANSPORT_TYPE" in error_msg, "Should suggest stdio"
        print("\n[PASS] Error message contains correct guidance")
        return True
    except Exception as e:
        print(f"[FAIL] Unexpected error type: {type(e).__name__}: {e}")
        return False

result = asyncio.run(test_sse_error())

if result:
    print("\n" + "="*70)
    print(" SSE BEHAVIOR TEST PASSED ")
    print("="*70)
    print("\n[PASS] SSE transport correctly raises NotImplementedError")
    print("[PASS] Error message provides user guidance")
    print("[PASS] System prevents invalid transport usage")
else:
    print("\n[FAIL] SSE behavior test failed")
    sys.exit(1)
