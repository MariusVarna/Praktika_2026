from typing import List, Dict, Tuple
from app.schemas.market_models import MarketBid, MarketResult, HourlyMarketInput
import random

class MarketEngine:
    """Core Market Clearing Engine - Pure logic, no database overhead."""

    @staticmethod
    def _group_by_price(sorted_bids: List[MarketBid]) -> List[List[MarketBid]]:
        if not sorted_bids: return []
        groups = [[sorted_bids[0]]]
        for bid in sorted_bids[1:]:
            if abs(bid.price - groups[-1][0].price) < 1e-9:
                groups[-1].append(bid)
            else:
                groups.append([bid])
        return groups

    def calculate_clearing(self, market_input: HourlyMarketInput) -> MarketResult:
        # Pre-process curves
        # 1. Add inelastic demand as a bid at INF price
        prepared_demand = sorted(market_input.demand_curve, key=lambda x: x.price, reverse=True)
        if market_input.inelastic_demand > 0:
            prepared_demand.insert(0, MarketBid(
                bid_id="system_demand_inelastic",
                volume=market_input.inelastic_demand,
                price=9999.0,
                bid_type="buy"
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

    def _distribute_fill(self, bid_group: List[MarketBid], volume: float, fill_map: Dict[str, float]):
        total_group_vol = sum(b.volume for b in bid_group)
        if total_group_vol <= 0: return
        ratio = volume / total_group_vol
        for bid in bid_group:
            fill = bid.volume * ratio
            fill_map[bid.bid_id] = fill_map.get(bid.bid_id, 0.0) + fill
