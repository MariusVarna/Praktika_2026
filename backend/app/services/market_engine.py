"""Market Engine - Delegates to pluggable clearing strategies.

Uses Strategy pattern for extensibility: supports different clearing algorithms
(pro-rata, discriminatory, full-fill, etc.) without modifying the engine.
"""

from app.services.clearing_strategy import ProRataClearingStrategy, ClearingStrategy
from app.schemas.market_models import HourlyMarketInput, MarketResult


class MarketEngine:
    """Core Market Clearing Engine - delegates to pluggable strategies.
    
    Responsibilities:
    - Route market clearing to appropriate strategy
    - Maintain consistent interface for consumers
    
    Open/Closed Principle: Open for extension (new strategies), closed for modification.
    """
    
    def __init__(self, strategy: ClearingStrategy = None):
        """Initialize with clearing strategy (defaults to pro-rata).
        
        Args:
            strategy: ClearingStrategy instance (defaults to ProRataClearingStrategy)
        """
        self.strategy = strategy or ProRataClearingStrategy()

    def set_strategy(self, strategy: ClearingStrategy):
        """Swap clearing strategy at runtime.
        
        Args:
            strategy: New ClearingStrategy instance
        """
        if not isinstance(strategy, ClearingStrategy):
            raise TypeError("Strategy must be an instance of ClearingStrategy")
        self.strategy = strategy

    def calculate_clearing(self, market_input: HourlyMarketInput) -> MarketResult:
        """Execute market clearing using current strategy.
        
        Args:
            market_input: Supply curves, demand curves, inelastic demand
            
        Returns:
            MarketResult with clearing price, volume, and fills
        """
        return self.strategy.calculate_clearing(market_input)

