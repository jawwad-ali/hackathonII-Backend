"""Check configuration before starting server"""
import os
from src.config import settings

print("Configuration Check")
print("=" * 60)

# Check critical settings
print(f"Gemini API Key: {'SET (length: ' + str(len(settings.GEMINI_API_KEY)) + ')' if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != 'your_gemini_api_key_here' else 'NOT SET'}")
print(f"Gemini Base URL: {settings.GEMINI_BASE_URL}")
print(f"Gemini Model: {settings.GEMINI_MODEL}")
print(f"\nMCP Transport Type: {settings.MCP_TRANSPORT_TYPE}")
print(f"MCP Server Command: {settings.MCP_SERVER_COMMAND}")
print(f"MCP Server Args: {settings.MCP_SERVER_ARGS}")
print(f"MCP Server Timeout: {settings.MCP_SERVER_TIMEOUT}s")
print(f"\nApp Environment: {settings.APP_ENV}")
print(f"App Host: {settings.APP_HOST}")
print(f"App Port: {settings.APP_PORT}")
print(f"Log Level: {settings.LOG_LEVEL}")

print("\n" + "=" * 60)

# Check if critical settings are present
issues = []
if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
    issues.append("GEMINI_API_KEY not configured")
if settings.MCP_TRANSPORT_TYPE not in ["stdio", "sse"]:
    issues.append(f"Invalid MCP_TRANSPORT_TYPE: {settings.MCP_TRANSPORT_TYPE}")

if issues:
    print("⚠️  CONFIGURATION ISSUES:")
    for issue in issues:
        print(f"  - {issue}")
    print("\nNote: Server may start in degraded mode")
else:
    print("✅ Configuration looks good!")
    print(f"✅ MCP Transport Type: {settings.MCP_TRANSPORT_TYPE} (correct)")
    print("Ready to start server")
