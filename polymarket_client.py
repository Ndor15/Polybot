"""
Polymarket Client - Handles order execution and market data
"""
import requests
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
from config import config

logger = logging.getLogger(__name__)


@dataclass
class Market:
    """Represents a Polymarket betting market"""
    market_id: str
    question: str
    event_id: str
    game_id: Optional[str]  # NBA game ID if available
    home_team: Optional[str]
    away_team: Optional[str]
    outcomes: List[Dict]  # [{"name": "Yes", "price": 0.52, "token_id": "..."}]
    active: bool
    closed: bool
    volume: float
    liquidity: float

    def get_outcome_price(self, outcome_name: str) -> Optional[float]:
        """Get current price for an outcome"""
        for outcome in self.outcomes:
            if outcome["name"].lower() == outcome_name.lower():
                return outcome.get("price", 0.5)
        return None

    def get_token_id(self, outcome_name: str) -> Optional[str]:
        """Get token ID for an outcome"""
        for outcome in self.outcomes:
            if outcome["name"].lower() == outcome_name.lower():
                return outcome.get("token_id")
        return None


@dataclass
class Position:
    """Represents an open trading position"""
    position_id: str
    market_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    size: float  # Amount in USDC
    entry_price: float
    current_price: float
    entry_time: float
    game_id: Optional[str]
    team: str

    def get_pnl(self) -> float:
        """Calculate current P&L"""
        if self.side == "BUY":
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size

    def get_pnl_percentage(self) -> float:
        """Calculate P&L as percentage"""
        pnl = self.get_pnl()
        return (pnl / self.size) * 100 if self.size > 0 else 0.0

    def should_stop_loss(self) -> bool:
        """Check if position hit stop loss"""
        return self.get_pnl_percentage() <= -config.STOP_LOSS_PERCENTAGE

    def should_take_profit(self) -> bool:
        """Check if position hit take profit"""
        return self.get_pnl_percentage() >= config.TAKE_PROFIT_PERCENTAGE

    def is_expired(self) -> bool:
        """Check if position exceeded max holding time"""
        return (time.time() - self.entry_time) > config.MAX_POSITION_TIME_SECONDS


class PolymarketClient:
    """
    Client for interacting with Polymarket

    Note: This is a simplified implementation. For production,
    you'll need to integrate with py-clob-client for order execution.
    """

    def __init__(self):
        self.base_url = config.POLYMARKET_GAMMA_API
        self.session = requests.Session()
        self.positions: Dict[str, Position] = {}

    def get_nba_markets(self, active_only: bool = True) -> List[Market]:
        """
        Fetch all NBA betting markets
        Returns: List of Market objects
        """
        try:
            params = {
                "series_id": config.NBA_SERIES_ID,
                "tag_id": config.NBA_TAG_ID,  # Game bets only
                "active": "true" if active_only else None,
                "closed": "false",
                "order": "startTime",
                "ascending": "true"
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = self.session.get(
                f"{self.base_url}/events",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            markets = []

            for event in data:
                # Extract markets from event
                for market_data in event.get("markets", []):
                    market = self._parse_market(market_data, event)
                    if market:
                        markets.append(market)

            logger.info(f"Fetched {len(markets)} NBA markets")
            return markets

        except Exception as e:
            logger.error(f"Error fetching NBA markets: {e}")
            return []

    def _parse_market(self, market_data: Dict, event: Dict) -> Optional[Market]:
        """Parse market data from API response"""
        try:
            # Parse outcomes
            outcomes = []
            for outcome in market_data.get("outcomes", []):
                outcomes.append({
                    "name": outcome.get("name", ""),
                    "price": float(outcome.get("price", 0.5)),
                    "token_id": outcome.get("token_id", "")
                })

            # Try to extract team names from event
            home_team = None
            away_team = None
            game_id = None

            # Event description might contain team names
            description = event.get("description", "")
            title = event.get("title", "")

            # TODO: Parse team names from description/title
            # For now, store full title
            home_team = title.split(" vs ")[0] if " vs " in title else None
            away_team = title.split(" vs ")[1] if " vs " in title and len(title.split(" vs ")) > 1 else None

            return Market(
                market_id=market_data.get("condition_id", ""),
                question=market_data.get("question", ""),
                event_id=event.get("id", ""),
                game_id=game_id,
                home_team=home_team,
                away_team=away_team,
                outcomes=outcomes,
                active=market_data.get("active", True),
                closed=market_data.get("closed", False),
                volume=float(market_data.get("volume", 0)),
                liquidity=float(market_data.get("liquidity", 0))
            )

        except Exception as e:
            logger.error(f"Error parsing market: {e}")
            return None

    def find_market_for_game(self, game_id: str, markets: List[Market]) -> Optional[Market]:
        """
        Find the market corresponding to a NBA game
        This is a simplified matching - in production, you'd need better matching logic
        """
        # For now, just return any active market with sufficient liquidity
        for market in markets:
            if market.active and not market.closed:
                if market.liquidity >= config.MIN_LIQUIDITY_USDC:
                    return market
        return None

    def place_order(
        self,
        market: Market,
        outcome_name: str,
        side: str,
        size: float,
        game_id: Optional[str] = None,
        team: str = ""
    ) -> Optional[Position]:
        """
        Place an order on Polymarket

        Args:
            market: Market object
            outcome_name: "Yes" or "No" or team name
            side: "BUY" or "SELL"
            size: Amount in USDC
            game_id: NBA game ID for tracking
            team: Team name for tracking

        Returns: Position object if successful

        Note: This is a MOCK implementation. In production, integrate with py-clob-client
        """
        logger.info(f"[MOCK] Placing {side} order: {size} USDC on {outcome_name} for {market.question}")

        try:
            # Get price and token ID
            price = market.get_outcome_price(outcome_name)
            token_id = market.get_token_id(outcome_name)

            if price is None or token_id is None:
                logger.error(f"Could not find outcome {outcome_name}")
                return None

            # TODO: Integrate with py-clob-client for actual order placement
            # For now, create a mock position

            position_id = f"pos_{int(time.time())}_{market.market_id}"

            position = Position(
                position_id=position_id,
                market_id=market.market_id,
                token_id=token_id,
                side=side,
                size=size,
                entry_price=price,
                current_price=price,
                entry_time=time.time(),
                game_id=game_id,
                team=team
            )

            self.positions[position_id] = position

            logger.info(f"✅ Position opened: {position_id} at price {price}")
            return position

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def close_position(self, position_id: str, reason: str = "") -> bool:
        """
        Close an open position

        Note: This is a MOCK implementation. In production, integrate with py-clob-client
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return False

        position = self.positions[position_id]
        pnl = position.get_pnl()
        pnl_pct = position.get_pnl_percentage()

        logger.info(f"[MOCK] Closing position {position_id}: P&L = ${pnl:.2f} ({pnl_pct:.2f}%) - {reason}")

        # TODO: Integrate with py-clob-client to actually close position

        del self.positions[position_id]
        return True

    def update_positions(self, markets: List[Market]):
        """Update current prices for all open positions"""
        for position in list(self.positions.values()):
            # Find the market
            market = next((m for m in markets if m.market_id == position.market_id), None)

            if market:
                # Update current price
                for outcome in market.outcomes:
                    if outcome["token_id"] == position.token_id:
                        position.current_price = outcome["price"]
                        break

    def get_active_positions(self) -> List[Position]:
        """Get all currently open positions"""
        return list(self.positions.values())

    def check_exits(self) -> List[tuple]:
        """
        Check all positions for exit conditions (SL/TP/Time)
        Returns: List of (position, reason) tuples to close
        """
        to_close = []

        for position in self.positions.values():
            if position.should_stop_loss():
                to_close.append((position, f"Stop Loss hit: {position.get_pnl_percentage():.2f}%"))

            elif position.should_take_profit():
                to_close.append((position, f"Take Profit hit: {position.get_pnl_percentage():.2f}%"))

            elif position.is_expired():
                to_close.append((position, f"Position expired: held for {(time.time() - position.entry_time)/60:.1f} minutes"))

        return to_close


if __name__ == "__main__":
    # Test the Polymarket client
    logging.basicConfig(level=logging.DEBUG)
    client = PolymarketClient()

    print("Fetching NBA markets...")
    markets = client.get_nba_markets()

    if markets:
        print(f"\nFound {len(markets)} markets")
        for market in markets[:3]:
            print(f"\n📊 {market.question}")
            print(f"   Liquidity: ${market.liquidity:,.0f}")
            for outcome in market.outcomes:
                print(f"   - {outcome['name']}: {outcome['price']:.3f}")
    else:
        print("No markets found")
