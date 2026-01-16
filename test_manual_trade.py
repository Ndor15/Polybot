"""
Manual trade test script - Test Polymarket trading with $1 bet
Press 'p' to place a $1 test trade on a specific market
"""
import logging
import sys
import time
from polymarket_trader import PolymarketTrader
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def search_markets(query):
    """Search for markets matching a query"""
    logger.info(f"🔍 Searching for markets containing '{query}'...")

    try:
        import requests
        from datetime import datetime

        # Use /events endpoint with closed=false (returns only active events)
        url = f"{config.POLYMARKET_GAMMA_API}/events"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 100
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        events = response.json()

        logger.info(f"  API returned {len(events)} active events")

        # Extract all markets from events and search
        matching_markets = []
        query_lower = query.lower()
        total_markets = 0

        for event in events:
            event_markets = event.get("markets", [])
            total_markets += len(event_markets)

            for market in event_markets:
                question = market.get("question", "")
                question_lower = question.lower()

                # Match query in question or event title
                event_title = event.get("title", "").lower()
                if query_lower in question_lower or query_lower in event_title:
                    # Add event title to market for context
                    market["event_title"] = event.get("title", "")
                    matching_markets.append(market)

        logger.info(f"  Searched {total_markets} markets from {len(events)} events")
        logger.info(f"  Found {len(matching_markets)} matching markets")
        return matching_markets

    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []


def list_popular_markets():
    """List some popular markets for user to choose"""
    logger.info("🔍 Fetching popular markets...")

    try:
        import requests

        # Use /events endpoint with closed=false (returns only active events)
        url = f"{config.POLYMARKET_GAMMA_API}/events"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 20
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        events = response.json()

        # Extract all markets from events
        markets = []
        for event in events:
            event_markets = event.get("markets", [])
            for market in event_markets:
                # Add event title to market for context
                market["event_title"] = event.get("title", "")
                markets.append(market)

            if len(markets) >= 20:
                break

        logger.info(f"\n📊 Top {len(markets)} Active Markets:")
        for i, market in enumerate(markets[:20], 1):
            question = market.get("question", "N/A")
            event_title = market.get("event_title", "")
            logger.info(f"  {i}. {question[:70]}...")
            if event_title:
                logger.info(f"      (Event: {event_title[:50]})")

        return markets[:20]

    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []


def place_test_trade(trader, market):
    """Place a $1 test trade on the market"""
    import json

    question = market.get("question", "Unknown")
    logger.info(f"\n📊 Market: {question}")

    # Get outcomes - sometimes it's a JSON string, sometimes it's already a list
    outcomes = market.get("outcomes", [])

    # Parse if it's a JSON string
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
            logger.debug(f"Parsed outcomes from JSON string")
        except:
            logger.error("Could not parse outcomes JSON")
            return False

    if not outcomes:
        logger.error("No outcomes found in market")
        return False

    logger.info(f"\n📋 Available outcomes (type: {type(outcomes).__name__}):")

    # Handle different outcome formats
    parsed_outcomes = []

    if isinstance(outcomes, list) and len(outcomes) > 0:
        # Check if outcomes are strings like ["Yes", "No"]
        if isinstance(outcomes[0], str):
            # Get token IDs from market level (may be JSON string)
            clob_token_ids = market.get("clobTokenIds", [])

            # Parse if it's a JSON string
            if isinstance(clob_token_ids, str):
                try:
                    clob_token_ids = json.loads(clob_token_ids)
                except:
                    clob_token_ids = []

            # Ensure we have at least 2 tokens
            if len(clob_token_ids) < 2:
                clob_token_ids = [None, None]

            yes_token = clob_token_ids[0]
            no_token = clob_token_ids[1]

            for i, outcome_name in enumerate(outcomes):
                token = yes_token if i == 0 else no_token
                parsed_outcomes.append({
                    "name": outcome_name,
                    "token_id": token
                })
                logger.info(f"  {i+1}. {outcome_name} (token: {token})")

        # Or if outcomes are dicts
        elif isinstance(outcomes[0], dict):
            for i, outcome in enumerate(outcomes):
                name = outcome.get("name", outcome.get("label", "Unknown"))
                token = outcome.get("token_id", outcome.get("tokenId"))
                price = outcome.get("price", 0.5)
                parsed_outcomes.append({
                    "name": name,
                    "token_id": token,
                    "price": price
                })
                logger.info(f"  {i+1}. {name} @ {price:.3f} (token: {token})")

    # Get token ID for "Yes" or first outcome
    token_id = None
    bet_on = "Yes"

    for outcome in parsed_outcomes:
        name = outcome.get("name", "")
        if name.lower() == "yes":
            token_id = outcome.get("token_id")
            bet_on = name
            break

    # Fallback to first outcome
    if not token_id and parsed_outcomes:
        token_id = parsed_outcomes[0].get("token_id")
        bet_on = parsed_outcomes[0].get("name", "First option")

    if not token_id:
        logger.error("Could not find token ID")
        logger.error(f"DEBUG: Market data: {market}")
        return False

    logger.info(f"\n💰 Will bet $1 on: {bet_on}")
    logger.info(f"🎯 Token ID: {token_id}")

    # Place the trade
    try:
        logger.info("\n📤 Placing $1 market order...")
        position = trader.place_market_order(
            token_id=token_id,
            side="BUY",
            size=1.0,
            game_id=None,
            team=bet_on
        )

        if position:
            logger.info(f"✅ TRADE SUCCESSFUL!")
            logger.info(f"   Position ID: {position.position_id}")
            logger.info(f"   Order ID: {position.order_id}")
            logger.info(f"   Size: ${position.size:.2f}")
            logger.info(f"   Price: {position.price:.3f}")
            return True
        else:
            logger.error("❌ Trade failed - no position returned")
            return False

    except Exception as e:
        logger.error(f"❌ Trade failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("🧪 Manual Trade Test Script")
    logger.info("=" * 60)

    # Validate config
    if not config.validate():
        logger.error("Configuration validation failed. Check .env file")
        return

    # Initialize trader
    try:
        logger.info("\n💼 Initializing Polymarket trader...")
        trader = PolymarketTrader()

        # Get balance
        balance = trader.get_balance()
        logger.info(f"💵 Current balance: ${balance:.2f} USDC")

        if balance < 1.0:
            logger.error("Insufficient balance for $1 test trade")
            return

    except Exception as e:
        logger.error(f"Failed to initialize trader: {e}")
        import traceback
        traceback.print_exc()
        return

    # Interactive market selection
    selected_market = None
    markets = []

    logger.info("\n" + "=" * 60)
    logger.info("📋 Market Selection")
    logger.info("=" * 60)
    logger.info("Commands:")
    logger.info("  's <keyword>' - Search markets (e.g., 's israel')")
    logger.info("  'l' - List top 20 popular markets")
    logger.info("  '<number>' - Select market by number")
    logger.info("  'q' - Quit")
    logger.info("=" * 60)

    while not selected_market:
        try:
            user_input = input("\n> ").strip()

            if user_input.lower() == 'q':
                logger.info("Exiting...")
                return

            elif user_input.lower() == 'l':
                markets = list_popular_markets()
                if not markets:
                    logger.warning("No markets found")

            elif user_input.lower().startswith('s '):
                query = user_input[2:].strip()
                if query:
                    markets = search_markets(query)
                    if markets:
                        logger.info(f"\n📊 Found {len(markets)} markets:")
                        from datetime import datetime
                        for i, m in enumerate(markets[:20], 1):  # Show max 20
                            question = m.get('question', 'N/A')
                            end_date = m.get("endDate", "")
                            try:
                                dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                                date_str = dt.strftime("%Y-%m-%d")
                            except:
                                date_str = "N/A"
                            logger.info(f"  {i}. {question[:70]}... (ends: {date_str})")
                    else:
                        logger.warning(f"No markets found for '{query}'")
                else:
                    logger.warning("Please provide a search query (e.g., 's israel')")

            elif user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(markets):
                    selected_market = markets[idx]
                    logger.info(f"\n✅ Selected: {selected_market.get('question', 'N/A')}")
                else:
                    logger.warning(f"Invalid number. Choose 1-{len(markets)}")
            else:
                logger.info("Commands: 's <keyword>' to search, 'l' to list, '<number>' to select, 'q' to quit")

        except KeyboardInterrupt:
            logger.info("\n\nExiting...")
            return
        except Exception as e:
            logger.error(f"Error: {e}")

    if not selected_market:
        logger.error("No market selected")
        return

    # Confirm and place trade
    logger.info("\n" + "=" * 60)
    logger.info("Press 'p' then Enter to place $1 test trade")
    logger.info("Press 'q' then Enter to quit")
    logger.info("=" * 60)

    while True:
        try:
            user_input = input("\n> ").strip().lower()

            if user_input == 'p':
                logger.info("\n🚀 Placing test trade...")
                success = place_test_trade(trader, selected_market)

                if success:
                    logger.info("\n✅ Test trade completed successfully!")
                    logger.info("Check your Polymarket account to verify the order")
                    break
                else:
                    logger.error("\n❌ Test trade failed")
                    logger.info("Press 'p' to retry or 'q' to quit")

            elif user_input == 'q':
                logger.info("Exiting...")
                break
            else:
                logger.info("Press 'p' to place trade or 'q' to quit")

        except KeyboardInterrupt:
            logger.info("\n\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            break


if __name__ == "__main__":
    main()
