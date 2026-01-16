import requests
from datetime import datetime, timezone

# Test /events endpoint (correct one according to docs)
print("Testing Polymarket /events API...")

url = "https://gamma-api.polymarket.com/events"
params = {
    "active": "true",
    "closed": "false",
    "limit": 10
}

response = requests.get(url, params=params)
print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    events = response.json()
    print(f"Returned {len(events)} events\n")

    for i, event in enumerate(events[:5], 1):
        title = event.get("title", "N/A")[:60]
        active = event.get("active", "N/A")
        closed = event.get("closed", "N/A")
        markets = event.get("markets", [])

        print(f"{i}. Event: {title}")
        print(f"   active: {active}, closed: {closed}")
        print(f"   {len(markets)} market(s):")

        for m in markets[:2]:  # Show first 2 markets
            question = m.get("question", "N/A")[:60]
            tokens = m.get("clobTokenIds", "N/A")
            print(f"      - {question}")
            print(f"        tokens: {tokens}")
        print()
else:
    print(f"Error: {response.text}")
