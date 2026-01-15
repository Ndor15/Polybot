"""
Configuration module for NBA Polymarket Trading Bot
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Central configuration for the trading bot"""

    # Polymarket Configuration
    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_SECRET: str = os.getenv("POLYMARKET_SECRET", "")
    POLYMARKET_PRIVATE_KEY: str = os.getenv("POLYMARKET_PRIVATE_KEY", "")
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "137"))

    # NBA API Configuration
    NBA_API_KEY: Optional[str] = os.getenv("NBA_API_KEY")
    NBA_API_BASE_URL: str = os.getenv("NBA_API_BASE_URL", "https://api.balldontlie.io/v1")

    # Polymarket API endpoints
    POLYMARKET_GAMMA_API: str = "https://gamma-api.polymarket.com"
    NBA_SERIES_ID: str = "10345"
    NBA_TAG_ID: str = "100639"  # NBA game bets (excluding futures)

    # Trading Configuration
    TRADE_SIZE_USDC: float = float(os.getenv("TRADE_SIZE_USDC", "5.0"))
    MAX_CONCURRENT_TRADES: int = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
    SLIPPAGE_TOLERANCE: float = float(os.getenv("SLIPPAGE_TOLERANCE", "0.02"))

    # Risk Management
    STOP_LOSS_PERCENTAGE: float = float(os.getenv("STOP_LOSS_PERCENTAGE", "2.5"))
    TAKE_PROFIT_PERCENTAGE: float = float(os.getenv("TAKE_PROFIT_PERCENTAGE", "3.0"))
    MAX_POSITION_TIME_SECONDS: int = int(os.getenv("MAX_POSITION_TIME_SECONDS", "3600"))
    MIN_LIQUIDITY_USDC: float = float(os.getenv("MIN_LIQUIDITY_USDC", "10.0"))

    # Signal Detection Thresholds
    MOMENTUM_RUN_THRESHOLD: int = int(os.getenv("MOMENTUM_RUN_THRESHOLD", "8"))
    LEAD_CHANGE_THRESHOLD: int = int(os.getenv("LEAD_CHANGE_THRESHOLD", "5"))
    UPDATE_INTERVAL_SECONDS: int = int(os.getenv("UPDATE_INTERVAL_SECONDS", "3"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "nba_polymarket_bot.log")

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_fields = [
            "POLYMARKET_PRIVATE_KEY",
        ]

        missing = []
        for field in required_fields:
            if not getattr(cls, field):
                missing.append(field)

        if missing:
            print(f"❌ Missing required configuration: {', '.join(missing)}")
            return False

        return True

    @classmethod
    def display(cls):
        """Display current configuration (hiding sensitive data)"""
        print("\n=== Bot Configuration ===")
        print(f"Chain ID: {cls.CHAIN_ID}")
        print(f"Trade Size: ${cls.TRADE_SIZE_USDC} USDC")
        print(f"Max Concurrent Trades: {cls.MAX_CONCURRENT_TRADES}")
        print(f"Stop Loss: {cls.STOP_LOSS_PERCENTAGE}%")
        print(f"Take Profit: {cls.TAKE_PROFIT_PERCENTAGE}%")
        print(f"Momentum Run Threshold: {cls.MOMENTUM_RUN_THRESHOLD} points")
        print(f"Lead Change Threshold: {cls.LEAD_CHANGE_THRESHOLD} points")
        print(f"Update Interval: {cls.UPDATE_INTERVAL_SECONDS}s")
        print("========================\n")


# Global config instance
config = Config()
