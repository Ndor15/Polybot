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
        url = f"{config.POLYMARKET_GAMMA_API}/markets"
        params = {
            "limit": 500,  # Get more markets
            "active": "true"
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()

        # Find markets mentioning the query
        matching_markets = []
        query_lower = query.lower()

        for market in markets:
            question = market.get("question", "").lower()
            if query_lower in question:
                matching_markets.append(market)

        logger.info(f"  Found {len(matching_markets)} markets")
        return matching_markets

    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []


def list_popular_markets():
    """List some popular markets for user to choose"""
    logger.info("🔍 Fetching popular markets...")

    try:
        import requests
        url = f"{config.POLYMARKET_GAMMA_API}/markets"
        params = {
            "limit": 20,
            "active": "true"
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()

        logger.info(f"\n📊 Top 20 Active Markets:")
        for i, market in enumerate(markets, 1):
            question = market.get("question", "N/A")
            logger.info(f"  {i}. {question[:80]}...")

        return markets

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
            # Get token IDs from market level
            yes_token = market.get("clobTokenIds", [None, None])[0]
            no_token = market.get("clobTokenIds", [None, None])[1]

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
                        for i, m in enumerate(markets[:20], 1):  # Show max 20
                            logger.info(f"  {i}. {m.get('question', 'N/A')}")
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
