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


def find_iran_israel_market(trader):
    """Find the Israel/Iran strike market"""
    logger.info("🔍 Searching for Israel/Iran markets...")

    try:
        # Search for markets containing "Israel" and "Iran"
        import requests
        url = f"{config.POLYMARKET_GAMMA_API}/markets"
        params = {
            "limit": 100,
            "active": "true"
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()

        # Find markets mentioning Israel and Iran
        matching_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            if "israel" in question and "iran" in question:
                matching_markets.append(market)
                logger.info(f"  - Found: {market.get('question', 'N/A')}")

        if not matching_markets:
            logger.warning("No Israel/Iran markets found")
            return None

        # Return first match
        return matching_markets[0]

    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return None


def place_test_trade(trader, market):
    """Place a $1 test trade on the market"""
    question = market.get("question", "Unknown")
    logger.info(f"\n📊 Market: {question}")

    # Get outcomes
    outcomes = market.get("outcomes", [])
    if not outcomes:
        logger.error("No outcomes found in market")
        return False

    logger.info("\n📋 Available outcomes:")
    for i, outcome in enumerate(outcomes):
        if isinstance(outcome, dict):
            name = outcome.get("name", outcome.get("label", "Unknown"))
            price = outcome.get("price", 0.5)
            token_id = outcome.get("token_id", outcome.get("tokenId", "N/A"))
            logger.info(f"  {i+1}. {name} @ {price:.3f} (token: {token_id})")
        else:
            logger.info(f"  {i+1}. {outcome}")

    # Get token ID for "Yes" or first outcome
    token_id = None
    bet_on = "Yes"

    for outcome in outcomes:
        if isinstance(outcome, dict):
            name = outcome.get("name", outcome.get("label", ""))
            if name.lower() == "yes":
                token_id = outcome.get("token_id") or outcome.get("tokenId")
                break

    # Fallback to first outcome
    if not token_id and outcomes:
        if isinstance(outcomes[0], dict):
            token_id = outcomes[0].get("token_id") or outcomes[0].get("tokenId")
            bet_on = outcomes[0].get("name", outcomes[0].get("label", "First option"))

    if not token_id:
        logger.error("Could not find token ID")
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

    # Find the market
    market = find_iran_israel_market(trader)
    if not market:
        logger.error("\nCould not find Israel/Iran market")
        logger.info("\n💡 You can modify the search in find_iran_israel_market() function")
        return

    # Wait for user input
    logger.info("\n" + "=" * 60)
    logger.info("Press 'p' then Enter to place $1 test trade")
    logger.info("Press 'q' then Enter to quit")
    logger.info("=" * 60)

    while True:
        try:
            user_input = input("\n> ").strip().lower()

            if user_input == 'p':
                logger.info("\n🚀 Placing test trade...")
                success = place_test_trade(trader, market)

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
