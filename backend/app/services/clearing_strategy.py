"""Clearing Algorithm Strategy Pattern - Abstract interface for different market clearing approaches."""

from abc import ABC, abstractmethod
from app.schemas.market_models import HourlyMarketInput, MarketResult


class ClearingStrategy(ABC):
    """Abstract base for market clearing algorithms.
    
    Enables pluggable clearing implementations (pro-rata, full-fill, discriminatory, etc.)
    without modifying MarketEngine or dependent code.
    
    Open/Closed Principle: Open for extension (new strategies), closed for modification (engine).
    """
    
    @abstractmethod
    def calculate_clearing(self, market_input: HourlyMarketInput) -> MarketResult:
        """Execute market clearing algorithm.
        
        Args:
            market_input: Supply curves, demand curves, inelastic demand for one hour
            
        Returns:
            MarketResult with clearing price, volume, and fills dictionary
        """
        pass


class ProRataClearingStrategy(ClearingStrategy):
    """Pro-rata market clearing with sequential price discovery.
    
    Algorithm:
    1. Sort supply by ascending price, demand by descending price
    2. Group bids at same price level for pro-rata distribution
    3. Iterate through price groups, clearing at intersection
    4. Distribute volume pro-rata within same-price groups
    
    Properties:
    - Non-discriminatory: All bids at clearing price treated equally
    - Price-fair: Clears at intersection of supply and demand
    """
    
    @staticmethod
    def _group_by_price(sorted_bids):
        if not sorted_bids: return []
        groups = [[sorted_bids[0]]]
        for bid in sorted_bids[1:]:
            if abs(bid.price - groups[-1][0].price) < 1e-9:
                groups[-1].append(bid)
            else:
                groups.append([bid])
        return groups

    def calculate_clearing(self, market_input: HourlyMarketInput) -> MarketResult:
        from app.schemas.market_models import MarketBid
        
        # Get demand multiplier from hour_data if available
        demand_multiplier = 1.0
        if market_input.hour_data and 'demand_forecast_profile' in market_input.hour_data:
            demand_multiplier = market_input.hour_data.get('demand_forecast_profile', 1.0)
        
        # Pre-process curves
        prepared_demand = sorted(market_input.demand_curve, key=lambda x: x.price, reverse=True)
        
# Add inelastic demand (50% - reduced from 70% to allow elastic bots to smooth price swings)
        if market_input.inelastic_demand > 0:
            inelastic_vol = market_input.inelastic_demand * 0.5
            prepared_demand.insert(0, MarketBid(
                bid_id="system_demand_inelastic",
                volume=inelastic_vol,
                price=9999.0,
                bid_type=True
            ))
        
        # Add elastic demand bots (50% - increased from 30%)
        # Use more bots with square-root distribution for smooth price curve
        elastic_vol_total = market_input.inelastic_demand * 0.5
        num_elastic_bots = 150
        
        max_bot_price = 400 * demand_multiplier
        min_bot_price = 20 * demand_multiplier
        price_range = max_bot_price - min_bot_price
        
        v_per_bot = elastic_vol_total / num_elastic_bots if num_elastic_bots > 0 else 0
        
        for i in range(num_elastic_bots):
            normalized = (i / num_elastic_bots) ** 0.7
            price = max_bot_price - normalized * price_range
            prepared_demand.append(MarketBid(
                bid_id=f"system_demand_{i}",
                volume=v_per_bot,
                price=round(price, 2),
                bid_type=True
            ))

        prepared_supply = sorted(market_input.supply_curve, key=lambda x: x.price)

        # Grouping for pro-rata handling
        supply_groups = self._group_by_price(prepared_supply)
        demand_groups = self._group_by_price(prepared_demand)

        fill_map = {}
        clearing_price = 0.0
        total_volume = 0.0

        s_idx, d_idx = 0, 0
        s_vol_rem = sum(b.volume for b in supply_groups[s_idx]) if supply_groups else 0
        d_vol_rem = sum(b.volume for b in demand_groups[d_idx]) if demand_groups else 0

        while s_idx < len(supply_groups) and d_idx < len(demand_groups):
            s_price = supply_groups[s_idx][0].price
            d_price = demand_groups[d_idx][0].price

            if d_price >= s_price:
                clearing_price = s_price
                trade_vol = min(s_vol_rem, d_vol_rem)
                total_volume += trade_vol

                # Distribute via pro-rata
                self._distribute_fill(supply_groups[s_idx], trade_vol, fill_map)
                self._distribute_fill(demand_groups[d_idx], trade_vol, fill_map)

                s_vol_rem -= trade_vol
                d_vol_rem -= trade_vol

                if abs(s_vol_rem) < 1e-12:
                    s_idx += 1
                    if s_idx < len(supply_groups):
                        s_vol_rem = sum(b.volume for b in supply_groups[s_idx])
                if abs(d_vol_rem) < 1e-12:
                    d_idx += 1
                    if d_idx < len(demand_groups):
                        d_vol_rem = sum(b.volume for b in demand_groups[d_idx])
            else:
                break

        return MarketResult(
            hour=market_input.hour,
            clearing_price=round(clearing_price, 2),
            clearing_volume=round(total_volume, 4),
            fills={bid_id: round(vol, 4) for bid_id, vol in fill_map.items()}
        )

    @staticmethod
    def _distribute_fill(bid_group, volume: float, fill_map: dict):
        """Distribute volume pro-rata among all bids in group."""
        total_group_vol = sum(b.volume for b in bid_group)
        if total_group_vol <= 0: return
        ratio = volume / total_group_vol
        for bid in bid_group:
            fill = bid.volume * ratio
            fill_map[bid.bid_id] = fill_map.get(bid.bid_id, 0.0) + fill
