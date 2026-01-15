"""
Script to test and inspect real Polymarket NBA markets
"""
import requests
import json
import sys
import io

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass

def test_polymarket_markets():
    """Fetch and display real NBA markets from Polymarket"""

    print("🔍 Fetching NBA markets from Polymarket...\n")

    # Test 1: Get all NBA events
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "series_id": "10345",  # NBA
        "active": "true",
        "closed": "false",
        "limit": "5"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        events = response.json()

        print(f"✅ Found {len(events)} NBA events\n")

        # Display first few events
        for i, event in enumerate(events[:3], 1):
            print(f"=" * 60)
            print(f"Event {i}:")
            print(f"  Title: {event.get('title', 'N/A')}")
            print(f"  Description: {event.get('description', 'N/A')}")
            print(f"  Start Time: {event.get('startDate', 'N/A')}")

            # Show markets
            markets = event.get('markets', [])
            print(f"  Markets: {len(markets)}")

            for j, market in enumerate(markets[:2], 1):
                print(f"\n  Market {j}:")
                print(f"    Question: {market.get('question', 'N/A')}")
                print(f"    Market ID: {market.get('condition_id', 'N/A')}")

                # Show outcomes
                outcomes = market.get('outcomes', [])
                print(f"    Outcomes:")
                for outcome in outcomes:
                    if isinstance(outcome, dict):
                        print(f"      - {outcome.get('name', 'N/A')}: {outcome.get('price', 'N/A')}")
                    else:
                        print(f"      - {outcome}")

            print()

        # Save full response for inspection
        with open('polymarket_nba_sample.json', 'w') as f:
            json.dump(events[:3], f, indent=2)

        print("\n✅ Full response saved to: polymarket_nba_sample.json")

        return events

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_team_name_formats():
    """Check what team name formats Polymarket uses"""

    print("\n" + "=" * 60)
    print("🏀 Analyzing Team Name Formats")
    print("=" * 60 + "\n")

    events = test_polymarket_markets()

    if not events:
        return

    # Extract all unique team name patterns
    team_patterns = set()

    for event in events:
        title = event.get('title', '')
        description = event.get('description', '')

        # Look for team names in various fields
        if ' vs ' in title:
            teams = title.split(' vs ')
            team_patterns.add(teams[0].strip())
            if len(teams) > 1:
                team_patterns.add(teams[1].strip())

        if ' @ ' in title:
            teams = title.split(' @ ')
            team_patterns.add(teams[0].strip())
            if len(teams) > 1:
                team_patterns.add(teams[1].strip())

        # Check markets
        for market in event.get('markets', []):
            question = market.get('question', '')

            # Extract team names from question
            for outcome in market.get('outcomes', []):
                if isinstance(outcome, dict):
                    name = outcome.get('name', '')
                    if name not in ['Yes', 'No', 'Over', 'Under']:
                        team_patterns.add(name)
                elif isinstance(outcome, str):
                    if outcome not in ['Yes', 'No', 'Over', 'Under']:
                        team_patterns.add(outcome)

    print("Found team name patterns:")
    for pattern in sorted(team_patterns):
        print(f"  - {pattern}")

    print(f"\nTotal unique patterns: {len(team_patterns)}")


if __name__ == "__main__":
    test_team_name_formats()
