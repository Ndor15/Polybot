"""
Real Polymarket Trading Client - Integrates py-clob-client for actual trading

This module replaces the mock trading with real order execution using py-clob-client.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
import requests
from web3 import Web3
from config import config

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL
    CLOB_AVAILABLE = True
except ImportError:
    CLOB_AVAILABLE = False
    logging.warning("py-clob-client not installed. Run: pip install py-clob-client")

logger = logging.getLogger(__name__)


@dataclass
class RealPosition:
    """Represents a real trading position on Polymarket"""
    position_id: str
    order_id: str
    market_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    size: float  # Amount in USDC
    price: float
    entry_price: float
    current_price: float
    entry_time: float
    game_id: Optional[str]
    team: str
    filled: bool
    fill_amount: float

    def get_pnl(self) -> float:
        """Calculate current P&L"""
        filled_size = self.fill_amount if self.filled else 0
        if self.side == "BUY":
            return (self.current_price - self.entry_price) * filled_size
        else:
            return (self.entry_price - self.current_price) * filled_size

    def get_pnl_percentage(self) -> float:
        """Calculate P&L as percentage"""
        pnl = self.get_pnl()
        filled_size = self.fill_amount if self.filled else self.size
        return (pnl / filled_size) * 100 if filled_size > 0 else 0.0

    def should_stop_loss(self) -> bool:
        """Check if position hit stop loss"""
        return self.get_pnl_percentage() <= -config.STOP_LOSS_PERCENTAGE

    def should_take_profit(self) -> bool:
        """Check if position hit take profit"""
        return self.get_pnl_percentage() >= config.TAKE_PROFIT_PERCENTAGE

    def is_expired(self) -> bool:
        """Check if position exceeded max holding time"""
        return (time.time() - self.entry_time) > config.MAX_POSITION_TIME_SECONDS


class PolymarketTrader:
    """
    Real Polymarket trading client using py-clob-client

    Features:
    - Actual order placement and execution
    - Position tracking with real fills
    - Balance checking
    - Order cancellation
    """

    def __init__(self):
        if not CLOB_AVAILABLE:
            raise ImportError(
                "py-clob-client is required for real trading. "
                "Install with: pip install py-clob-client"
            )

        self.host = "https://clob.polymarket.com"
        self.chain_id = config.CHAIN_ID
        self.private_key = config.POLYMARKET_PRIVATE_KEY

        if not self.private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY not set in .env file")

        # Get wallet address from private key
        try:
            from eth_account import Account
            account = Account.from_key(self.private_key)
            self.wallet_address = account.address
            logger.info(f"Wallet address: {self.wallet_address}")
        except Exception as e:
            logger.warning(f"Could not derive wallet address: {e}")
            self.wallet_address = None

        # Initialize client
        try:
            self.client = ClobClient(
                self.host,
                key=self.private_key,
                chain_id=self.chain_id,
                signature_type=0,  # 0 = EOA (standard wallet like MetaMask)
                funder=None  # Use key address as funder
            )

            # Generate and set API credentials
            logger.info("Generating API credentials...")
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)

            logger.info("✅ Successfully authenticated with Polymarket")

        except Exception as e:
            logger.error(f"Failed to initialize Polymarket client: {e}")
            raise

        self.positions: Dict[str, RealPosition] = {}

        # Polygon RPC for direct balance checks
        self.w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
        self.usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon

    def get_balance(self) -> float:
        """Get current USDC balance directly from blockchain"""
        try:
            if not self.wallet_address:
                logger.error("Wallet address not available")
                return 0.0

            # USDC contract ABI (just the balanceOf function)
            usdc_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]

            # Create contract instance
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.usdc_address),
                abi=usdc_abi
            )

            # Get balance
            balance_wei = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(self.wallet_address)
            ).call()

            # Convert from smallest unit (USDC has 6 decimals)
            balance = balance_wei / 1_000_000

            logger.debug(f"Current balance: ${balance:.2f} USDC")
            return balance

        except Exception as e:
            logger.error(f"Error fetching balance from blockchain: {e}")
            logger.error("Make sure you have USDC on Polygon network")
            return 0.0

    def get_market_info(self, token_id: str) -> Optional[Dict]:
        """Get detailed market information for a token"""
        try:
            market = self.client.get_market(token_id)
            return market
        except Exception as e:
            logger.error(f"Error fetching market info for {token_id}: {e}")
            return None

    def get_current_price(self, token_id: str) -> Optional[float]:
        """Get current market price for a token"""
        try:
            # Get order book using py-clob-client
            book = self.client.get_order_book(token_id)

            # Access bids using attribute access (book.bids) or dict access (book['bids'])
            if book:
                # Try attribute-style access first
                try:
                    bids = book.bids if hasattr(book, 'bids') else book.get('bids', [])
                    if bids and len(bids) > 0:
                        # bids[0] is an OrderSummary with price as string
                        best_bid = float(bids[0].price if hasattr(bids[0], 'price') else bids[0]['price'])
                        return best_bid
                except (AttributeError, KeyError, IndexError, TypeError):
                    pass

            return None
        except Exception as e:
            logger.error(f"Error fetching price for {token_id}: {e}")
            return None

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        game_id: Optional[str] = None,
        team: str = ""
    ) -> Optional[RealPosition]:
        """
        Place a real order on Polymarket

        Args:
            token_id: Market token ID
            side: "BUY" or "SELL"
            price: Limit price (0.0-1.0)
            size: Amount in USDC
            game_id: NBA game ID for tracking
            team: Team name for tracking

        Returns: RealPosition object if successful
        """
        logger.info(f"Placing {side} order: {size} USDC @ {price:.3f} on token {token_id}")

        try:
            # Check balance
            balance = self.get_balance()
            if balance < size:
                logger.error(f"Insufficient balance: ${balance:.2f} < ${size:.2f}")
                return None

            # Create order - convert side string to constant
            side_constant = BUY if side.upper() == "BUY" else SELL
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side_constant
            )

            # Place order
            response = self.client.create_order(order_args)

            if not response:
                logger.error("Order placement failed - no response")
                return None

            order_id = response.get("orderID")
            if not order_id:
                logger.error("Order placement failed - no order ID")
                return None

            # Create position
            position_id = f"pos_{int(time.time())}_{order_id[:8]}"

            position = RealPosition(
                position_id=position_id,
                order_id=order_id,
                market_id=token_id,
                token_id=token_id,
                side=side.upper(),
                size=size,
                price=price,
                entry_price=price,
                current_price=price,
                entry_time=time.time(),
                game_id=game_id,
                team=team,
                filled=False,
                fill_amount=0.0
            )

            self.positions[position_id] = position

            logger.info(f"✅ Order placed successfully: {order_id}")
            logger.info(f"   Position ID: {position_id}")
            logger.info(f"   Entry Price: {price:.3f}")
            logger.info(f"   Size: ${size:.2f} USDC")

            return position

        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None

    def place_market_order(
        self,
        token_id: str,
        side: str,
        size: float,
        game_id: Optional[str] = None,
        team: str = ""
    ) -> Optional[RealPosition]:
        """
        Place a market order (best available price)

        This is faster for execution but may have worse price
        """
        # Get current best price
        current_price = self.get_current_price(token_id)

        if current_price is None:
            logger.error("Could not get current price for market order")
            return None

        # Add slippage tolerance
        if side.upper() == "BUY":
            price = current_price * (1 + config.SLIPPAGE_TOLERANCE)
        else:
            price = current_price * (1 - config.SLIPPAGE_TOLERANCE)

        # Clamp to valid range
        price = max(0.01, min(0.99, price))

        return self.place_order(token_id, side, price, size, game_id, team)

    def close_position(self, position_id: str, reason: str = "") -> bool:
        """
        Close an open position by placing opposite order

        Args:
            position_id: Position to close
            reason: Reason for closing (for logging)

        Returns: True if successfully closed
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return False

        position = self.positions[position_id]

        try:
            # Update position status first
            self._update_position_status(position)

            pnl = position.get_pnl()
            pnl_pct = position.get_pnl_percentage()

            logger.info(f"Closing position {position_id}: P&L = ${pnl:.2f} ({pnl_pct:.2f}%) - {reason}")

            # Cancel original order if not filled
            if not position.filled:
                try:
                    self.client.cancel_order(position.order_id)
                    logger.debug(f"Cancelled unfilled order {position.order_id}")
                except Exception as e:
                    logger.warning(f"Could not cancel order: {e}")

            # If position was filled, place opposite order to close
            if position.filled and position.fill_amount > 0:
                opposite_side = "SELL" if position.side == "BUY" else "BUY"

                # Get current market price
                current_price = self.get_current_price(position.token_id)

                if current_price:
                    # Place closing order
                    close_price = current_price * (1 - config.SLIPPAGE_TOLERANCE) if opposite_side == "SELL" else current_price * (1 + config.SLIPPAGE_TOLERANCE)
                    close_price = max(0.01, min(0.99, close_price))

                    order_args = OrderArgs(
                        token_id=position.token_id,
                        price=close_price,
                        size=position.fill_amount,
                        side=opposite_side,
                        order_type=OrderType.GTC
                    )

                    self.client.create_order(order_args)
                    logger.info(f"✅ Closing order placed for {position.fill_amount} shares")

            # Remove from positions
            del self.positions[position_id]
            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            return False

    def _update_position_status(self, position: RealPosition):
        """Update position fill status and current price"""
        try:
            # Get order status
            order = self.client.get_order(position.order_id)

            if order:
                status = order.get("status", "")

                if status == "MATCHED":
                    position.filled = True
                    position.fill_amount = float(order.get("size_matched", 0))
                elif status == "PARTIALLY_FILLED":
                    position.filled = False
                    position.fill_amount = float(order.get("size_matched", 0))

            # Update current price
            current_price = self.get_current_price(position.token_id)
            if current_price:
                position.current_price = current_price

        except Exception as e:
            logger.debug(f"Error updating position status: {e}")

    def update_positions(self):
        """Update all positions with current prices and fill status"""
        for position in list(self.positions.values()):
            self._update_position_status(position)

    def get_active_positions(self) -> List[RealPosition]:
        """Get all currently open positions"""
        return list(self.positions.values())

    def check_exits(self) -> List[tuple]:
        """
        Check all positions for exit conditions (SL/TP/Time)
        Returns: List of (position, reason) tuples to close
        """
        to_close = []

        for position in self.positions.values():
            # Update status first
            self._update_position_status(position)

            # Only check filled positions
            if not position.filled or position.fill_amount == 0:
                continue

            if position.should_stop_loss():
                to_close.append((position, f"Stop Loss hit: {position.get_pnl_percentage():.2f}%"))

            elif position.should_take_profit():
                to_close.append((position, f"Take Profit hit: {position.get_pnl_percentage():.2f}%"))

            elif position.is_expired():
                to_close.append((position, f"Position expired: held for {(time.time() - position.entry_time)/60:.1f} minutes"))

        return to_close


if __name__ == "__main__":
    # Test the real trading client
    logging.basicConfig(level=logging.INFO)

    try:
        trader = PolymarketTrader()

        print("\n=== Polymarket Trader Test ===")

        # Get balance
        balance = trader.get_balance()
        print(f"Balance: ${balance:.2f} USDC")

        print("\n✅ Real trading client initialized successfully!")
        print("Ready to trade on Polymarket.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. py-clob-client is installed: pip install py-clob-client")
        print("2. POLYMARKET_PRIVATE_KEY is set in .env file")
