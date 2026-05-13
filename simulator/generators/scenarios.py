"""
Scenario Manager for Live Demo
Handles injection of interactive anomalies during the real-time pitch
"""

import random
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from ..config import ZONES, CHECKPOINTS, get_weather_condition

logger = logging.getLogger(__name__)

@dataclass
class Scenario:
    """Represents an active scenario"""
    scenario_type: str
    params: Dict
    start_time: datetime
    duration_minutes: int
    affected_zones: List[str] = field(default_factory=list)
    affected_checkpoints: List[str] = field(default_factory=list)
    is_active: bool = True

class ScenarioManager:
    """Manages live demo scenarios and their effects on event generation"""
    
    def __init__(self, generators: Dict, message_broker):
        self.generators = generators
        self.message_broker = message_broker
        self.active_scenarios: Dict[str, Scenario] = {}
        self.scenario_history: List[Scenario] = []
        
        # Scenario configuration
        self.scenario_configs = {
            'incident': {
                'description': 'Traffic incident causing partial blockage',
                'valid_zones': ['ZONE-02', 'ZONE-03', 'ZONE-04', 'ZONE-06', 'ZONE-07', 'ZONE-08', 'ZONE-09', 'ZONE-10'],
                'default_duration': 10,  # minutes
                'effects': ['cctv_motion_drop', 'checkpoint_closure', 'upstream_congestion']
            },
            'evasion': {
                'description': 'Vehicle evading toll plazas',
                'valid_zones': [],  # Affects journey pattern, not specific zones
                'default_duration': 0,  # Instant effect
                'effects': ['journey_modification', 'evasion_injection']
            },
            'wildlife': {
                'description': 'Wildlife activity in forest corridor',
                'valid_zones': ['ZONE-04', 'ZONE-05', 'ZONE-11'],  # Forest zones only
                'default_duration': 5,  # minutes
                'effects': ['traffic_gap', 'motion_pulse', 'speed_reduction']
            },
            'ghost_vehicle': {
                'description': 'Unregistered vehicle with no FASTag',
                'valid_zones': [],  # Affects specific vehicle, not zones
                'default_duration': 0,  # Instant effect
                'effects': ['ghost_plate_injection']
            },
            'high_risk_hour': {
                'description': 'Period of increased evasion and anomalies',
                'valid_zones': [],  # System-wide effect
                'default_duration': 5,  # minutes
                'effects': ['increased_evasion', 'more_failures', 'enhanced_variation']
            }
        }
    
    async def inject_scenario(self, scenario_type: str, params: Dict) -> Dict:
        """Inject a new scenario"""
        
        if scenario_type not in self.scenario_configs:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        
        config = self.scenario_configs[scenario_type]
        
        # Validate parameters
        self._validate_scenario_params(scenario_type, params)
        
        # Create scenario
        duration = params.get('duration_minutes', config['default_duration'])
        scenario_id = f"{scenario_type}_{datetime.now().strftime('%H%M%S')}"
        
        scenario = Scenario(
            scenario_type=scenario_type,
            params=params,
            start_time=datetime.now(),
            duration_minutes=duration,
            affected_zones=params.get('zone_id', []),
            affected_checkpoints=params.get('checkpoint_ids', [])
        )
        
        # Add to active scenarios
        self.active_scenarios[scenario_id] = scenario
        
        # Apply scenario effects
        await self._apply_scenario_effects(scenario)
        
        logger.info(f"📋 Scenario injected: {scenario_type} (ID: {scenario_id})")
        
        return {
            'scenario_id': scenario_id,
            'type': scenario_type,
            'status': 'active',
            'start_time': scenario.start_time.isoformat(),
            'duration_minutes': duration,
            'affected_zones': scenario.affected_zones,
            'message': f'Scenario {scenario_type} successfully injected'
        }
    
    def _validate_scenario_params(self, scenario_type: str, params: Dict):
        """Validate scenario parameters"""
        config = self.scenario_configs[scenario_type]
        
        if 'zone_id' in params:
            zone_id = params['zone_id']
            if config['valid_zones'] and zone_id not in config['valid_zones']:
                raise ValueError(f"Zone {zone_id} not valid for scenario {scenario_type}")
        
        if 'duration_minutes' in params:
            duration = params['duration_minutes']
            if duration < 0 or duration > 60:
                raise ValueError("Duration must be between 0 and 60 minutes")
    
    async def _apply_scenario_effects(self, scenario: Scenario):
        """Apply the effects of a scenario"""
        
        if scenario.scenario_type == 'incident':
            await self._apply_incident_scenario(scenario)
        elif scenario.scenario_type == 'evasion':
            await self._apply_evasion_scenario(scenario)
        elif scenario.scenario_type == 'wildlife':
            await self._apply_wildlife_scenario(scenario)
        elif scenario.scenario_type == 'ghost_vehicle':
            await self._apply_ghost_vehicle_scenario(scenario)
        elif scenario.scenario_type == 'high_risk_hour':
            await self._apply_high_risk_hour_scenario(scenario)
    
    async def _apply_incident_scenario(self, scenario: Scenario):
        """Apply incident scenario effects"""
        zone_id = scenario.params.get('zone_id', 'ZONE-06')
        
        # Generate incident vehicle and journey
        incident_vehicle = self._generate_incident_vehicle()
        
        # Create incident journey (enters but doesn't exit)
        await self._create_incident_journey(incident_vehicle, zone_id)
        
        # Trigger CCTV motion drop in affected zone
        await self._trigger_cctv_motion_drop(zone_id, scenario.duration_minutes)
        
        logger.info(f"🚗 Incident scenario applied to {zone_id}")
    
    async def _apply_evasion_scenario(self, scenario: Scenario):
        """Apply evasion scenario effects"""
        
        # Generate specific evasion vehicle
        evasion_vehicle = self._generate_evasion_vehicle()
        
        # Create evasion journey (skips intermediate checkpoints)
        await self._create_evasion_journey(evasion_vehicle)
        
        logger.info("🚘 Evasion scenario: vehicle skipping toll plazas")
    
    async def _apply_wildlife_scenario(self, scenario: Scenario):
        """Apply wildlife scenario effects"""
        zone_id = scenario.params.get('zone_id', 'ZONE-04')
        
        # Trigger traffic gap in forest zone
        await self._trigger_traffic_gap(zone_id, 60)  # 60 second gap
        
        # Trigger motion pulse in CCTV
        await self._trigger_wildlife_motion_pulse(zone_id)
        
        # Apply speed reduction to vehicles in zone
        await self._apply_speed_reduction(zone_id, 0.8, 240)  # 20% reduction for 4 minutes
        
        logger.info(f"🦌 Wildlife scenario applied to {zone_id}")
    
    async def _apply_ghost_vehicle_scenario(self, scenario: Scenario):
        """Apply ghost vehicle scenario effects"""
        
        # Generate ghost vehicle (plate not in database)
        ghost_vehicle = self._generate_ghost_vehicle()
        
        # Create ghost journey (ANPR events but no FASTag)
        await self._create_ghost_journey(ghost_vehicle)
        
        logger.info("👻 Ghost vehicle scenario: unregistered vehicle detected")
    
    async def _apply_high_risk_hour_scenario(self, scenario: Scenario):
        """Apply high risk hour scenario effects"""
        
        # Increase evasion injection rate
        await self._increase_evasion_rate(0.15)  # 15% instead of 5%
        
        # Add more OCR errors and class mismatches
        await self._increase_anomaly_rates()
        
        # Trigger random motion drops in 1-2 zones
        await self._trigger_random_motion_drops()
        
        logger.info("⚠️ High risk hour scenario: increased anomalies and evasion")
    
    def _generate_incident_vehicle(self) -> Dict:
        """Generate vehicle data for incident scenario"""
        return {
            'plate_number': 'KA09INC001',
            'registered_class': 'Car',
            'registration_state': 'KA',
            'registration_status': 'active',
            'owner_type': 'private',
            'fuel_type': 'PETROL',
            'maker_model': 'INCIDENT_VEHICLE',
            'direction': random.choice(['MB', 'BM'])
        }
    
    def _generate_evasion_vehicle(self) -> Dict:
        """Generate vehicle data for evasion scenario"""
        return {
            'plate_number': 'KA09EV0001',
            'registered_class': 'Car',
            'registration_state': 'KA',
            'registration_status': 'active',
            'owner_type': 'private',
            'fuel_type': 'PETROL',
            'maker_model': 'EVASION_VEHICLE',
            'direction': 'MB'  # Mysore to Bangalore for demo
        }
    
    def _generate_ghost_vehicle(self) -> Dict:
        """Generate vehicle data for ghost vehicle scenario"""
        return {
            'plate_number': 'XX99ZZ0000',  # Not in database
            'registered_class': 'Car',
            'registration_state': 'XX',
            'registration_status': 'unknown',
            'owner_type': 'unknown',
            'fuel_type': 'PETROL',
            'maker_model': 'GHOST_VEHICLE',
            'direction': random.choice(['MB', 'BM'])
        }
    
    async def _create_incident_journey(self, vehicle: Dict, zone_id: str):
        """Create journey for incident scenario"""
        # This would integrate with the main journey generator
        # For now, log the intent
        logger.info(f"Creating incident journey for {vehicle['plate_number']} in {zone_id}")
    
    async def _create_evasion_journey(self, vehicle: Dict):
        """Create journey for evasion scenario"""
        # Entry at CP-01, exit at CP-12, skip intermediate checkpoints
        logger.info(f"Creating evasion journey for {vehicle['plate_number']}: CP-01 -> CP-12 (skipping tolls)")
    
    async def _create_ghost_journey(self, vehicle: Dict):
        """Create journey for ghost vehicle scenario"""
        # ANPR at CP-01, CP-03, CP-06 but no FASTag events
        logger.info(f"Creating ghost journey for {vehicle['plate_number']}: ANPR only, no FASTag")
    
    async def _trigger_cctv_motion_drop(self, zone_id: str, duration_minutes: int):
        """Trigger CCTV motion index drop in affected zone"""
        logger.info(f"Triggering CCTV motion drop in {zone_id} for {duration_minutes} minutes")
        # This would integrate with CCTV generator
    
    async def _trigger_traffic_gap(self, zone_id: str, duration_seconds: int):
        """Trigger traffic gap in zone"""
        logger.info(f"Triggering {duration_seconds}s traffic gap in {zone_id}")
    
    async def _trigger_wildlife_motion_pulse(self, zone_id: str):
        """Trigger motion pulse for wildlife scenario"""
        logger.info(f"Triggering wildlife motion pulse in {zone_id}")
    
    async def _apply_speed_reduction(self, zone_id: str, reduction_factor: float, duration_seconds: int):
        """Apply speed reduction to vehicles in zone"""
        logger.info(f"Applying {reduction_factor}x speed reduction in {zone_id} for {duration_seconds}s")
    
    async def _increase_evasion_rate(self, new_rate: float):
        """Temporarily increase evasion injection rate"""
        logger.info(f"Increasing evasion rate to {new_rate * 100}%")
    
    async def _increase_anomaly_rates(self):
        """Increase anomaly rates for high risk hour"""
        logger.info("Increasing anomaly rates (OCR errors, class mismatches)")
    
    async def _trigger_random_motion_drops(self):
        """Trigger random motion drops in 1-2 zones"""
        affected_zones = random.sample(list(ZONES.keys()), k=random.randint(1, 2))
        logger.info(f"Triggering random motion drops in zones: {affected_zones}")
    
    def get_active_scenarios(self) -> List[Dict]:
        """Get list of currently active scenarios"""
        active = []
        for scenario_id, scenario in self.active_scenarios.items():
            if scenario.is_active:
                active.append({
                    'scenario_id': scenario_id,
                    'type': scenario.scenario_type,
                    'start_time': scenario.start_time.isoformat(),
                    'duration_minutes': scenario.duration_minutes,
                    'affected_zones': scenario.affected_zones,
                    'params': scenario.params
                })
        return active
    
    def cleanup_expired_scenarios(self):
        """Clean up expired scenarios"""
        current_time = datetime.now()
        expired_ids = []
        
        for scenario_id, scenario in self.active_scenarios.items():
            if scenario.is_active and scenario.duration_minutes > 0:
                elapsed = (current_time - scenario.start_time).total_seconds() / 60
                if elapsed >= scenario.duration_minutes:
                    scenario.is_active = False
                    self.scenario_history.append(scenario)
                    expired_ids.append(scenario_id)
                    logger.info(f"🧹 Scenario expired: {scenario.scenario_type} (ID: {scenario_id})")
        
        # Remove expired scenarios
        for scenario_id in expired_ids:
            del self.active_scenarios[scenario_id]
    
    def reset_scenarios(self):
        """Reset all scenarios"""
        self.active_scenarios.clear()
        self.scenario_history.clear()
        logger.info("🔄 All scenarios reset")