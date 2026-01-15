"""
Quick test to check what NBA API is returning right now
"""
import requests
from datetime import datetime
from config import config

def test_nba_api_now():
    """Test what the NBA API returns right now"""

    print("Testing NBA API...\n")

    url = f"{config.NBA_API_BASE_URL}/games"
    params = {
        "dates[]": datetime.now().strftime("%Y-%m-%d")
    }

    headers = {}
    if config.NBA_API_KEY:
        headers["Authorization"] = config.NBA_API_KEY

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            games = data.get("data", [])

            print(f"\nTotal games today: {len(games)}\n")

            for game in games:
                home = game["home_team"]["full_name"]
                away = game["visitor_team"]["full_name"]
                status = game.get("status", "unknown")
                home_score = game.get("home_team_score", 0)
                away_score = game.get("visitor_team_score", 0)
                period = game.get("period", 0)

                print(f"{away} @ {home}")
                print(f"  Status: {status}")
                print(f"  Score: {away_score} - {home_score}")
                print(f"  Period: {period}")
                print()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nba_api_now()
