"""Parse and display health check response"""
import json

health_response = {
    "status":"healthy",
    "timestamp":"2026-01-01T06:53:49.736441+00:00",
    "uptime_seconds":31,
    "circuit_breakers":{
        "mcp_server":{
            "state":"closed",
            "failure_count":1,
            "last_failure":"2026-01-01T06:53:25.705509"
        },
        "gemini_api":{
            "state":"closed",
            "failure_count":0,
            "last_failure":None
        }
    },
    "metrics":{
        "total_requests":0,
        "successful_requests":0,
        "failed_requests":0,
        "success_rate":0.0
    }
}

print("="*60)
print("FASTAPI SERVER HEALTH CHECK")
print("="*60)
print(f"\n✅ Status: {health_response['status'].upper()}")
print(f"⏱️  Uptime: {health_response['uptime_seconds']} seconds")
print(f"📅 Timestamp: {health_response['timestamp']}")

print("\n" + "="*60)
print("CIRCUIT BREAKERS")
print("="*60)

for name, breaker in health_response['circuit_breakers'].items():
    state_icon = "✅" if breaker['state'] == 'closed' else "⚠️" if breaker['state'] == 'half-open' else "❌"
    print(f"\n{state_icon} {name.upper()}")
    print(f"   State: {breaker['state'].upper()}")
    print(f"   Failures: {breaker['failure_count']}")
    if breaker['last_failure']:
        print(f"   Last Failure: {breaker['last_failure']}")
    else:
        print(f"   Last Failure: None")

print("\n" + "="*60)
print("METRICS")
print("="*60)
print(f"Total Requests: {health_response['metrics']['total_requests']}")
print(f"Successful: {health_response['metrics']['successful_requests']}")
print(f"Failed: {health_response['metrics']['failed_requests']}")
print(f"Success Rate: {health_response['metrics']['success_rate']*100:.1f}%")

print("\n" + "="*60)
print("VERIFICATION RESULTS")
print("="*60)

checks = []
checks.append(("Server Running", health_response['status'] == 'healthy'))
checks.append(("MCP Circuit Breaker", health_response['circuit_breakers']['mcp_server']['state'] == 'closed'))
checks.append(("Gemini Circuit Breaker", health_response['circuit_breakers']['gemini_api']['state'] == 'closed'))

all_pass = all(check[1] for check in checks)

for check_name, passed in checks:
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {check_name}")

print("\n" + "="*60)
if all_pass:
    print("✅ ALL CHECKS PASSED - Server is healthy!")
else:
    print("⚠️  Some checks failed - review circuit breaker states")
print("="*60)
