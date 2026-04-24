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
    def apply_charge(current_battery_mwh: float, charge_needed: float, battery_max_mwh: float, bandwidth_mw: float = 1e9, efficiency: float = 1.0) -> tuple[float, bool, float]:
        """Apply charging with efficiency factor and bandwidth constraint.
        
        Args:
            current_battery_mwh: Current battery level (MWh)
            charge_needed: Energy to charge (already efficiency-adjusted via calculate_charge_needed, MWh)
            battery_max_mwh: Battery capacity limit (MWh)
            bandwidth_mw: Max charge rate allowed (MW/h)
            efficiency: Charging efficiency (0-1)
            
        Returns:
            (new_battery_level, charge_succeeded, actual_delivered_mwh) - 
            succeeded=False if over-capacity or over-bandwidth
            actual_delivered_mwh is the actual amount that was charged (may be less than requested)
        """
        effective_bandwidth = min(charge_needed, bandwidth_mw)
        
        if effective_bandwidth <= 0:
            return current_battery_mwh, True, 0.0

        new_level = current_battery_mwh + effective_bandwidth
        if new_level <= battery_max_mwh:
            return round(new_level, 4), True, round(effective_bandwidth, 4)
        else:
            space_available = battery_max_mwh - current_battery_mwh
            actual_charged = min(space_available, effective_bandwidth)
            new_level = current_battery_mwh + actual_charged
            return round(new_level, 4), False, round(actual_charged, 4)

    @staticmethod
    def apply_discharge(current_battery_mwh: float, discharge_needed: float, bandwidth_mw: float = 1e9, efficiency: float = 1.0) -> tuple[float, bool, float]:
        """Apply discharging with constraint and bandwidth validation.
        
        Args:
            current_battery_mwh: Current battery level (MWh)
            discharge_needed: Energy to discharge (already efficiency-adjusted via calculate_discharge_available, MWh)
            bandwidth_mw: Max discharge rate allowed (MW/h)
            efficiency: Discharging efficiency (0-1)
            
        Returns:
            (new_battery_level, discharge_succeeded, actual_delivered_mwh) -
            succeeded=False if insufficient battery or over-bandwidth
            actual_delivered_mwh is the actual amount that was discharged (may be less than requested)
        """
        effective_bandwidth = min(discharge_needed, bandwidth_mw)
        
        if effective_bandwidth <= 0:
            return current_battery_mwh, True, 0.0

        if current_battery_mwh >= effective_bandwidth:
            new_level = current_battery_mwh - effective_bandwidth
            return round(new_level, 4), True, round(effective_bandwidth, 4)
        else:
            actual_discharged = current_battery_mwh
            new_level = 0.0
            return round(new_level, 4), False, round(actual_discharged, 4)

    @staticmethod
    def calculate_charge_needed(filled_volume_mwh: float, efficiency_charge: float) -> float:
        """Calculate actual energy needed from grid for a given charging amount.
        
        Args:
            filled_volume_mwh: Volume cleared in market (MWh) - target to put in battery
            efficiency_charge: Battery charging efficiency (0-1)
            
        Returns:
            Energy needed from grid (accounting for efficiency loss)
        """
        if efficiency_charge <= 0:
            return filled_volume_mwh
        return filled_volume_mwh / efficiency_charge

    @staticmethod
    def calculate_discharge_available(filled_volume_mwh: float, efficiency_discharge: float) -> float:
        """Calculate required battery discharge to deliver filled volume.
        
        Args:
            filled_volume_mwh: Volume to deliver to market (MWh)
            efficiency_discharge: Battery discharging efficiency (0-1)
            
        Returns:
            Required battery depletion (accounting for efficiency loss)
        """
        if efficiency_discharge <= 0:
            return filled_volume_mwh
        return filled_volume_mwh / efficiency_discharge
