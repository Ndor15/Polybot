import requests
from datetime import datetime, timezone

# Test different API endpoints
print("Testing Polymarket API...")

# Try without 'active' filter
url = "https://gamma-api.polymarket.com/markets"
params = {"limit": 10}

response = requests.get(url, params=params)
print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    markets = response.json()
    print(f"Returned {len(markets)} markets\n")

    now = datetime.now(timezone.utc)

    for i, market in enumerate(markets[:5], 1):
        question = market.get("question", "N/A")[:60]
        end_date = market.get("endDate", "N/A")
        closed = market.get("closed", "N/A")
        active = market.get("active", "N/A")

        # Try to parse end date
        if end_date and end_date != "N/A":
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                is_future = end_dt > now
                print(f"{i}. {question}")
                print(f"   endDate: {end_date} (future: {is_future})")
                print(f"   closed: {closed}, active: {active}\n")
            except:
                print(f"{i}. {question}")
                print(f"   endDate: {end_date} (parse failed)")
                print(f"   closed: {closed}, active: {active}\n")
        else:
            print(f"{i}. {question}")
            print(f"   NO ENDDATE")
            print(f"   closed: {closed}, active: {active}\n")
else:
    print(f"Error: {response.text}")
