"""Penalty Service - Handles physics and prediction penalties calculation."""

class PenaltyService:
    """Manages penalty calculation for bid pricing accuracy and physics violations.
    
    Responsibilities:
    - Calculate physics violation penalties (over-charge, under-discharge)
    - Calculate price prediction/accuracy penalties
    - Combine independent penalty components
    """
    
    @staticmethod
    def calculate_penalty(unfilled_volume_mwh: float, clearing_price: float,
                          penalty_price: float, penalty_k: float, penalty_b: float) -> float:
        """Calculate penalty using unfilled volume with fixed and dynamic components.
        
        Formula: penalty = (unfilled * penalty_price) + (unfilled * (clearing_price * k + b))
        
        Args:
            unfilled_volume_mwh: Volume that could not be physically delivered (MWh)
            clearing_price: Market clearing price (€/MWh)
            penalty_price: Fixed penalty per unfilled MWh (€/MWh)
            penalty_k: Slope coefficient for dynamic penalty (€/MWh per €/MWh)
            penalty_b: Base penalty for any violation (€)
            
        Returns:
            Total penalty amount (€)
        """
        if unfilled_volume_mwh <= 0:
            return 0.0
        
        fixed_penalty = unfilled_volume_mwh * penalty_price
        dynamic_penalty = unfilled_volume_mwh * (clearing_price * penalty_k + penalty_b)
        
        return round(fixed_penalty + dynamic_penalty, 2)