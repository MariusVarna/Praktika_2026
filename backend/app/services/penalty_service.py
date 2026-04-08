"""Penalty Service - Handles physics and prediction penalties calculation."""

class PenaltyService:
    """Manages penalty calculation for bid pricing accuracy and physics violations.
    
    Responsibilities:
    - Calculate physics violation penalties (over-charge, under-discharge)
    - Calculate price prediction/accuracy penalties
    - Combine independent penalty components
    """
    
    @staticmethod
    def calculate_physics_penalty(charge_success: bool, discharge_success: bool, 
                                  filled_volume_mwh: float, penalty_price: float) -> float:
        """Calculate penalty for battery physics violations.
        
        Args:
            charge_success: Whether charge operation succeeded
            discharge_success: Whether discharge operation succeeded
            filled_volume_mwh: Volume that was filled in market (MWh)
            penalty_price: Penalty per MWh for physics violations (€)
            
        Returns:
            Physics penalty amount (€), 0 if no violation
        """
        if (not charge_success) or (not discharge_success):
            # Physics violation: promised to buy/sell but battery constraint failed
            return round(filled_volume_mwh * penalty_price, 2)
        return 0.0

    @staticmethod
    def calculate_prediction_penalty(player_price: float, clearing_price: float, 
                                    penalty_k: float, penalty_b: float) -> float:
        """Calculate penalty for price prediction inaccuracy.
        
        Incentivizes players to predict market clearing price accurately.
        Linear penalty: penalty = k * |price_diff| + b
        
        Args:
            player_price: Price bid by player (€/MWh)
            clearing_price: Actual market clearing price (€/MWh)
            penalty_k: Slope coefficient for price difference sensitivity
            penalty_b: Base penalty floor (€)
            
        Returns:
            Prediction penalty amount (€)
        """
        price_diff = abs(player_price - clearing_price)
        return round((penalty_k * price_diff) + penalty_b, 2)

    @staticmethod
    def combine_penalties(physics_penalty: float, prediction_penalty: float) -> float:
        """Combine independent penalty components.
        
        Args:
            physics_penalty: Penalty for battery constraint violations (€)
            prediction_penalty: Penalty for price prediction accuracy (€)
            
        Returns:
            Total penalty amount (€)
        """
        return round(physics_penalty + prediction_penalty, 2)
