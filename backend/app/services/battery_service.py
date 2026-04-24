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
    def apply_charge(current_battery_mwh: float, charge_needed_grid: float, battery_max_mwh: float, bandwidth_mw: float = 1e9, efficiency: float = 1.0) -> tuple[float, bool, float]:
        """Apply charging with efficiency factor and bandwidth constraint.
        
        Args:
            current_battery_mwh: Current battery level (MWh in battery)
            charge_needed_grid: Energy to charge from grid (MWh, already efficiency-adjusted via calculate_charge_needed)
            battery_max_mwh: Battery capacity limit (MWh)
            bandwidth_mw: Max charge rate allowed (MW/h)
            efficiency: Charging efficiency (0-1)
            
        Returns:
            (new_battery_level, charge_succeeded, actual_delivered_market_mwh) - 
            succeeded=False if over-capacity or over-bandwidth
            actual_delivered_market_mwh is the actual amount that was charged in MARKET units (MWh bought)
        """
        # Input validation
        if efficiency <= 0 or efficiency > 1.0:
            raise ValueError(f"Invalid efficiency: {efficiency}")
        if bandwidth_mw <= 0:
            return current_battery_mwh, True, 0.0
        
        # Limit by bandwidth (in grid units)
        effective_grid_mwh = min(charge_needed_grid, bandwidth_mw)
        
        if effective_grid_mwh <= 0:
            return current_battery_mwh, True, 0.0
        
        # Convert to battery units for capacity check
        effective_battery_mwh = effective_grid_mwh * efficiency
        
        if current_battery_mwh + effective_battery_mwh <= battery_max_mwh:
            # All fits
            new_level = current_battery_mwh + effective_battery_mwh
            # Return in MARKET units (MWh bought/sold)
            return round(new_level, 4), True, round(effective_battery_mwh, 4)
        else:
            # Partial - only what fits in battery
            space_available = battery_max_mwh - current_battery_mwh
            actual_battery = min(space_available, effective_battery_mwh)
            new_level = current_battery_mwh + actual_battery
            # Return in MARKET units
            return round(new_level, 4), False, round(actual_battery, 4)

    @staticmethod
    def apply_discharge(current_battery_mwh: float, discharge_needed_battery: float, bandwidth_mw: float = 1e9, efficiency: float = 1.0) -> tuple[float, bool, float]:
        """Apply discharging with constraint and bandwidth validation.
        
        Args:
            current_battery_mwh: Current battery level (MWh in battery)
            discharge_needed_battery: Energy to discharge from battery (MWh, already efficiency-adjusted via calculate_discharge_available)
            bandwidth_mw: Max discharge rate allowed (MW/h)
            efficiency: Discharging efficiency (0-1)
            
        Returns:
            (new_battery_level, discharge_succeeded, actual_delivered_market_mwh) -
            succeeded=False if insufficient battery or over-bandwidth
            actual_delivered_market_mwh is the actual amount that was discharged in MARKET units (MWh sold)
        """
        # Input validation
        if efficiency <= 0 or efficiency > 1.0:
            raise ValueError(f"Invalid efficiency: {efficiency}")
        if bandwidth_mw <= 0:
            return current_battery_mwh, True, 0.0
        
        # Limit by bandwidth (in battery units)
        effective_battery_mwh = min(discharge_needed_battery, bandwidth_mw)
        
        if effective_battery_mwh <= 0:
            return current_battery_mwh, True, 0.0
        
        if current_battery_mwh >= effective_battery_mwh:
            # All can be discharged
            new_level = current_battery_mwh - effective_battery_mwh
            # Convert to MARKET units (multiply by efficiency)
            return round(new_level, 4), True, round(effective_battery_mwh * efficiency, 4)
        else:
            # Only part can be discharged
            actual_battery = current_battery_mwh
            new_level = 0.0
            # Convert to MARKET units
            return round(new_level, 4), False, round(actual_battery * efficiency, 4)

    @staticmethod
    def calculate_charge_needed(filled_volume_mwh: float, efficiency_charge: float) -> float:
        """Calculate actual energy needed from grid for a given charging amount.
        
        Args:
            filled_volume_mwh: Volume cleared in market (MWh) - target to put in battery
            efficiency_charge: Battery charging efficiency (0-1)
            
        Returns:
            Energy needed from grid (MWh, accounting for efficiency loss)
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
            Required battery depletion (MWh from battery, accounting for efficiency loss)
        """
        if efficiency_discharge <= 0:
            return filled_volume_mwh
        return filled_volume_mwh / efficiency_discharge
