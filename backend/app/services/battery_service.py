"""Battery Physics Service - Handles charge/discharge calculations and constraint validation."""

class BatteryService:
    """Manages battery state transitions and physics constraints.
    
    Responsibilities:
    - Apply charging with efficiency factor
    - Apply discharging with efficiency validation
    - Check battery capacity constraints
    - Determine physics violations (over-charge, under-discharge)
    """
    
    @staticmethod
    def apply_charge(current_battery_mwh: float, charge_needed: float, battery_max_mwh: float) -> tuple[float, bool]:
        """Apply charging with efficiency factor.
        
        Args:
            current_battery_mwh: Current battery level (MWh)
            charge_needed: Energy to charge (already efficiency-adjusted, MWh)
            battery_max_mwh: Battery capacity limit (MWh)
            
        Returns:
            (new_battery_level, charge_succeeded) - succeeded=False if over-capacity
        """
        new_level = current_battery_mwh + charge_needed
        if new_level <= battery_max_mwh:
            return round(new_level, 4), True
        else:
            return current_battery_mwh, False

    @staticmethod
    def apply_discharge(current_battery_mwh: float, discharge_needed: float) -> tuple[float, bool]:
        """Apply discharging with constraint validation.
        
        Args:
            current_battery_mwh: Current battery level (MWh)
            discharge_needed: Energy to discharge (accounting for efficiency, MWh)
            
        Returns:
            (new_battery_level, discharge_succeeded) - succeeded=False if insufficient battery
        """
        if current_battery_mwh >= discharge_needed:
            new_level = current_battery_mwh - discharge_needed
            return round(new_level, 4), True
        else:
            return current_battery_mwh, False

    @staticmethod
    def calculate_charge_needed(filled_volume_mwh: float, efficiency_charge: float) -> float:
        """Calculate actual energy needed from grid for a given charging amount.
        
        Args:
            filled_volume_mwh: Volume cleared in market (MWh)
            efficiency_charge: Battery charging efficiency (0-1)
            
        Returns:
            Adjusted volume accounting for efficiency
        """
        return filled_volume_mwh * efficiency_charge

    @staticmethod
    def calculate_discharge_available(filled_volume_mwh: float, efficiency_discharge: float) -> float:
        """Calculate required battery discharge to deliver filled volume.
        
        Args:
            filled_volume_mwh: Volume to deliver to market (MWh)
            efficiency_discharge: Battery discharging efficiency (0-1)
            
        Returns:
            Required battery depletion (always higher due to efficiency loss)
        """
        return filled_volume_mwh / efficiency_discharge
