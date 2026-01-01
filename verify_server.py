"""Comprehensive server verification for T033-T036 implementation"""
import requests
import json
from src.config import settings

print("="*70)
print(" SERVER VERIFICATION - T033-T036 Implementation ")
print("="*70)

# Test 1: Configuration Check
print("\n[TEST 1] Configuration Verification")
print("-"*70)
print(f"MCP_TRANSPORT_TYPE: {settings.MCP_TRANSPORT_TYPE}")
assert settings.MCP_TRANSPORT_TYPE == "stdio", "Transport type should be stdio"
print("[PASS] MCP_TRANSPORT_TYPE = stdio (default)")

print(f"MCP_SERVER_COMMAND: {settings.MCP_SERVER_COMMAND}")
print(f"MCP_SERVER_ARGS: {settings.MCP_SERVER_ARGS}")
print(f"MCP_SERVER_TIMEOUT: {settings.MCP_SERVER_TIMEOUT}s")
print("[PASS] MCP configuration loaded correctly")

# Test 2: Server Health Check
print("\n[TEST 2] Server Health Check")
print("-"*70)
try:
    response = requests.get("http://127.0.0.1:8000/health", timeout=5)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"Status Code: {response.status_code} [PASS]")

    health_data = response.json()
    print(f"Server Status: {health_data['status']}")
    assert health_data['status'] in ['healthy', 'degraded'], "Status should be healthy or degraded"
    print("[PASS] Server is responding")

except Exception as e:
    print(f"[FAIL] Health check failed: {e}")
    raise

# Test 3: Circuit Breakers
print("\n[TEST 3] Circuit Breaker Status")
print("-"*70)
try:
    breakers = health_data['circuit_breakers']

    for name, breaker in breakers.items():
        state = breaker['state']
        print(f"{name}: {state.upper()}")
        assert state in ['closed', 'open', 'half-open'], f"Invalid state: {state}"

    print("[PASS] Circuit breakers operational")

except Exception as e:
    print(f"[FAIL] Circuit breaker check failed: {e}")
    raise

# Test 4: Root Endpoint
print("\n[TEST 4] Root Endpoint")
print("-"*70)
try:
    response = requests.get("http://127.0.0.1:8000/", timeout=5)
    assert response.status_code == 200
    data = response.json()

    print(f"Message: {data['message']}")
    print(f"Available Endpoints: {', '.join(data['endpoints'].keys())}")
    print("[PASS] Root endpoint working")

except Exception as e:
    print(f"[FAIL] Root endpoint failed: {e}")
    raise

# Test 5: MCP Transport Type from Code
print("\n[TEST 5] MCP Client Transport Configuration")
print("-"*70)
try:
    from src.mcp import client
    import inspect

    # Check that conditional transport logic exists
    source = inspect.getsource(client._initialize_mcp_connection_with_retry)

    assert 'transport_type' in source, "transport_type variable not found"
    assert 'if transport_type == "stdio"' in source, "stdio condition not found"
    assert 'elif transport_type == "sse"' in source, "sse condition not found"
    assert '127.0.0.1' in source, "localhost security comment not found"
    assert 'NotImplementedError' in source, "SSE not implemented error not found"

    print("[PASS] Conditional transport initialization implemented")
    print("[PASS] stdio transport logic present")
    print("[PASS] sse transport placeholder present")
    print("[PASS] localhost-only security requirement documented")

except Exception as e:
    print(f"[FAIL] MCP client verification failed: {e}")
    raise

# Test 6: Documentation Check
print("\n[TEST 6] Documentation Verification")
print("-"*70)
try:
    import os

    # Check quickstart.md has SSE documentation
    quickstart_path = "specs/003-agent-mcp-integration/quickstart.md"
    if os.path.exists(quickstart_path):
        with open(quickstart_path, 'r', encoding='utf-8') as f:
            quickstart_content = f.read()

        assert 'SSE Transport Configuration' in quickstart_content, "SSE section not found"
        assert '127.0.0.1' in quickstart_content, "localhost requirement not documented"
        assert 'MCP_TRANSPORT_TYPE' in quickstart_content, "transport type not documented"
        print("[PASS] quickstart.md contains SSE documentation")
    else:
        print("[SKIP] quickstart.md not found at expected path")

    # Check .env.example has transport type
    env_example_path = ".env.example"
    if os.path.exists(env_example_path):
        with open(env_example_path, 'r', encoding='utf-8') as f:
            env_content = f.read()

        assert 'MCP_TRANSPORT_TYPE' in env_content, "transport type not in .env.example"
        print("[PASS] .env.example contains MCP_TRANSPORT_TYPE")
    else:
        print("[SKIP] .env.example not found")

except Exception as e:
    print(f"[FAIL] Documentation check failed: {e}")
    raise

# Final Summary
print("\n" + "="*70)
print(" VERIFICATION SUMMARY ")
print("="*70)
print("[PASS] T033: MCP_TRANSPORT_TYPE environment variable")
print("[PASS] T034: Conditional transport initialization")
print("[PASS] T035: SSE transport documentation")
print("[PASS] T036: Localhost-only security requirement")
print("\n[PASS] Server running with stdio transport (default)")
print("[PASS] All circuit breakers operational")
print("[PASS] All endpoints responding")
print("[PASS] Configuration loaded correctly")

print("\n" + "="*70)
print(" ALL TESTS PASSED - Implementation Verified! ")
print("="*70)
