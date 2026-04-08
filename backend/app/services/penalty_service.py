"""Penalty Service - Handles physics and prediction penalties calculation."""

class PenaltyService:
    """Manages penalty calculation for bid pricing accuracy and physics violations.
    
    Responsibilities:
    - Calculate physics violation penalties (over-charge, under-discharge)
    - Calculate price prediction/accuracy penalties
    - Combine independent penalty components
    """
    
    @staticmethod
    def calculate_total_penalty(charge_success: bool, discharge_success: bool, 
                               filled_volume_mwh: float, penalty_k: float, penalty_b: float) -> float:
        """Calculate total penalty using physical violation linear model (k*v + b).
        
        Args:
            charge_success: Whether charge operation succeeded
            discharge_success: Whether discharge operation succeeded
            filled_volume_mwh: Volume that was filled in market (MWh)
            penalty_k: Slope coefficient for violation volume (€/MWh)
            penalty_b: Base penalty floor for any violation (€)
            
        Returns:
            Total penalty amount (€), 0 if no violation
        """
        if (not charge_success) or (not discharge_success):
            # Physics violation: battery hit limit (SOC 0 or 100)
            return round((penalty_k * filled_volume_mwh) + penalty_b, 2)
        return 0.0
