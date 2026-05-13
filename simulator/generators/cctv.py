"""
CCTV Motion Detection Event Generator
Generates CCTV events with motion index computation based on traffic flow and scenarios
"""

import random
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..config import CCTV_CONFIG, ZONES, CHECKPOINTS, get_weather_condition, get_traffic_rate

logger = logging.getLogger(__name__)

class CCTVGenerator:
    """Generates CCTV motion detection events with realistic patterns"""
    
    def __init__(self):
        self.frame_window_seconds = CCTV_CONFIG['frame_window_seconds']
        self.motion_patterns = CCTV_CONFIG['motion_patterns']
        self.noise_range = CCTV_CONFIG['noise_range']
        
        # Camera configuration per zone
        self.cameras_per_zone = self._initialize_cameras()
        
        # Traffic flow tracking for motion calculation
        self.zone_traffic_counts = {zone_id: 0 for zone_id in ZONES.keys()}
        self.last_update_time = {}
    
    def _initialize_cameras(self) -> Dict[str, List[Dict]]:
        """Initialize camera configuration for each zone"""
        cameras = {}
        
        for zone_id, zone_config in ZONES.items():
            zone_type = zone_config.get('type', 'highway')
            
            # Determine number of cameras based on zone type and size
            zone_length = zone_config['km_end'] - zone_config['km_start']
            
            if zone_type == 'forest_corridor':
                camera_count = max(2, int(zone_length / 8))  # Sparse coverage
            elif zone_type == 'toll_plaza':
                camera_count = 6  # Full coverage at plazas
            else:
                camera_count = max(3, int(zone_length / 5))  # Standard highway coverage
            
            # Generate camera configurations
            cameras[zone_id] = []
            for i in range(camera_count):
                camera_id = f"CAM-{zone_id}-{i+1:02d}"
                
                # Calculate camera position along zone
                position_km = zone_config['km_start'] + (zone_length * (i + 0.5) / camera_count)
                
                cameras[zone_id].append({
                    'camera_id': camera_id,
                    'zone_id': zone_id,
                    'position_km': position_km,
                    'type': self._get_camera_type(zone_type, i),
                    'status': 'active',
                    'last_motion_index': 0.0
                })
        
        return cameras
    
    def _get_camera_type(self, zone_type: str, camera_index: int) -> str:
        """Determine camera type based on zone and position"""
        if zone_type == 'toll_plaza':
            return 'toll_booth' if camera_index < 4 else 'overview'
        elif zone_type == 'forest_corridor':
            return 'wildlife_monitor'
        else:
            return 'highway_overview'
    
    def generate_event(self, camera_id: str, timestamp: datetime, 
                      active_journeys: int = 0, is_scenario: bool = False,
                      scenario_type: str = None) -> Dict:
        """Generate a single CCTV motion detection event"""
        
        # Find camera configuration
        camera_config = self._find_camera_config(camera_id)
        if not camera_config:
            logger.warning(f"Camera {camera_id} not found")
            return None
        
        zone_id = camera_config['zone_id']
        zone_config = ZONES[zone_id]
        
        # Calculate base motion index
        motion_index = self._calculate_motion_index(zone_id, camera_config, 
                                                  active_journeys, timestamp)
        
        # Apply scenario effects if active
        if is_scenario and scenario_type:
            motion_index = self._apply_scenario_effect(motion_index, scenario_type, 
                                                     zone_id, timestamp)
        
        # Add noise
        noise = random.uniform(-self.noise_range, self.noise_range)
        motion_index = max(0.0, min(1.0, motion_index + noise))
        
        # Update camera state
        camera_config['last_motion_index'] = motion_index
        self.last_update_time[camera_id] = timestamp
        
        event = {
            'camera_id': camera_id,
            'zone_id': zone_id,
            'timestamp': timestamp.isoformat(),
            'motion_index': round(motion_index, 3),
            'camera_type': camera_config['type'],
            'zone_type': zone_config.get('type', 'highway'),
            'active_journeys': active_journeys,
            'weather_condition': get_weather_condition(),
            'is_scenario': is_scenario,
            'scenario_type': scenario_type,
            'camera_status': camera_config['status']
        }
        
        # Add additional metrics for different camera types
        if camera_config['type'] == 'toll_booth':
            event.update(self._get_toll_booth_metrics(zone_id, motion_index))
        elif camera_config['type'] == 'wildlife_monitor':
            event.update(self._get_wildlife_metrics(zone_id, motion_index))
        else:
            event.update(self._get_highway_metrics(zone_id, motion_index))
        
        logger.debug(f"📹 CCTV event generated: {camera_id} in {zone_id} "
                    f"(motion: {motion_index:.3f}, type: {camera_config['type']})")
        
        return event
    
    def _find_camera_config(self, camera_id: str) -> Optional[Dict]:
        """Find camera configuration by ID"""
        for zone_cameras in self.cameras_per_zone.values():
            for camera in zone_cameras:
                if camera['camera_id'] == camera_id:
                    return camera
        return None
    
    def _calculate_motion_index(self, zone_id: str, camera_config: Dict,
                              active_journeys: int, timestamp: datetime) -> float:
        """Calculate motion index based on traffic flow and zone characteristics"""
        
        zone_config = ZONES[zone_id]
        zone_type = zone_config.get('type', 'highway')
        
        # Base motion calculation
        if zone_type == 'toll_plaza':
            motion_index = self._calculate_toll_plaza_motion(active_journeys, timestamp)
        elif zone_type == 'forest_corridor':
            motion_index = self._calculate_forest_corridor_motion(active_journeys, timestamp)
        else:
            motion_index = self._calculate_highway_motion(active_journeys, timestamp)
        
        # Apply time-of-day effects
        motion_index = self._apply_time_effects(motion_index, timestamp)
        
        # Apply weather effects
        motion_index = self._apply_weather_effects(motion_index)
        
        return motion_index
    
    def _calculate_toll_plaza_motion(self, active_journeys: int, timestamp: datetime) -> float:
        """Calculate motion index for toll plaza cameras"""
        # Toll plazas have oscillating motion due to stop-and-go traffic
        
        # Base motion from vehicle count
        base_motion = min(0.9, 0.3 + (active_journeys * 0.01))
        
        # Add oscillating pattern (stop-and-go)
        time_seconds = timestamp.second + timestamp.minute * 60
        oscillation = 0.2 * (1 + (time_seconds % 30) / 30)  # 30-second cycle
        
        motion_index = base_motion + oscillation
        
        return min(1.0, motion_index)
    
    def _calculate_forest_corridor_motion(self, active_journeys: int, timestamp: datetime) -> float:
        """Calculate motion index for forest corridor cameras"""
        # Forest corridors have steady, lower motion
        
        # Base motion from vehicle count (lower than highway)
        base_motion = min(0.7, 0.2 + (active_journeys * 0.008))
        
        # Night time reduction
        if self._is_night_time(timestamp):
            base_motion *= 0.7
        
        return base_motion
    
    def _calculate_highway_motion(self, active_journeys: int, timestamp: datetime) -> float:
        """Calculate motion index for highway cameras"""
        # Standard highway motion calculation
        
        # Get current traffic rate for context
        current_hour = timestamp.hour
        traffic_rate = get_traffic_rate(current_hour)
        
        # Base motion from traffic rate and active journeys
        normalized_traffic = min(traffic_rate / 1800, 1.0)  # Normalize to peak rate
        base_motion = 0.4 + (normalized_traffic * 0.4) + (active_journeys * 0.0005)
        
        return min(0.9, base_motion)
    
    def _apply_time_effects(self, motion_index: float, timestamp: datetime) -> float:
        """Apply time-of-day effects to motion index"""
        hour = timestamp.hour
        
        if 7 <= hour < 10 or 17 <= hour < 21:  # Peak hours
            motion_index *= 1.2
        elif 21 <= hour < 7:  # Night hours
            motion_index *= 0.6
        else:  # Off-peak
            motion_index *= 0.9
        
        return min(1.0, motion_index)
    
    def _apply_weather_effects(self, motion_index: float) -> float:
        """Apply weather effects to motion index"""
        weather = get_weather_condition()
        
        if weather == 'WX-RA':  # Rain
            motion_index *= 0.8  # Reduced motion due to slower traffic
        elif weather == 'WX-FG':  # Fog
            motion_index *= 0.6  # Significantly reduced motion
        
        return motion_index
    
    def _apply_scenario_effect(self, motion_index: float, scenario_type: str,
                             zone_id: str, timestamp: datetime) -> float:
        """Apply scenario-specific effects to motion index"""
        
        if scenario_type == 'incident':
            # Incident scenario: progressive motion drop
            return self._calculate_incident_motion(motion_index, timestamp)
        
        elif scenario_type == 'wildlife':
            # Wildlife scenario: brief motion pulse then reduction
            return self._calculate_wildlife_motion(motion_index, timestamp)
        
        elif scenario_type == 'high_risk_hour':
            # High risk hour: more variation
            variation = random.uniform(-0.2, 0.2)
            return max(0.0, min(1.0, motion_index + variation))
        
        return motion_index
    
    def _calculate_incident_motion(self, base_motion: float, timestamp: datetime) -> float:
        """Calculate motion index for incident scenario"""
        # Incident causes progressive motion drop over 3 minutes
        
        # Use seconds from start of incident (simplified)
        incident_seconds = timestamp.second + timestamp.minute * 60
        
        if incident_seconds < 60:  # First minute
            motion_drop = 0.8 - (incident_seconds / 60) * 0.3  # 0.8 -> 0.5
        elif incident_seconds < 180:  # Next 2 minutes
            progress = (incident_seconds - 60) / 120
            motion_drop = 0.5 - progress * 0.4  # 0.5 -> 0.1
        else:  # After 3 minutes
            motion_drop = 0.1  # Minimum motion
        
        return max(0.1, min(base_motion, motion_drop))
    
    def _calculate_wildlife_motion(self, base_motion: float, timestamp: datetime) -> float:
        """Calculate motion index for wildlife scenario"""
        # Wildlife causes brief motion pulse then reduction
        
        incident_seconds = timestamp.second + timestamp.minute * 60
        
        if incident_seconds < 10:  # First 10 seconds: motion pulse
            pulse_intensity = 0.12 + (incident_seconds / 10) * 0.06  # 0.12 -> 0.18
            return pulse_intensity
        elif incident_seconds < 240:  # Next 4 minutes: reduced motion
            return base_motion * 0.7  # 30% reduction
        else:
            return base_motion  # Return to normal
    
    def _is_night_time(self, timestamp: datetime) -> bool:
        """Check if it's night time (21:00-05:00)"""
        hour = timestamp.hour
        return hour >= 21 or hour < 5
    
    def _get_toll_booth_metrics(self, zone_id: str, motion_index: float) -> Dict:
        """Get additional metrics for toll booth cameras"""
        return {
            'queue_length': int(motion_index * 10),  # Estimated queue length
            'avg_processing_time': 15 + int((1 - motion_index) * 30),  # Seconds
            'lane_utilization': motion_index,
            'throughput_per_hour': int(motion_index * 600)  # Vehicles per hour
        }
    
    def _get_wildlife_metrics(self, zone_id: str, motion_index: float) -> Dict:
        """Get additional metrics for wildlife monitor cameras"""
        return {
            'animal_detection_probability': 0.05 if motion_index < 0.3 else 0.01,
            'vegetation_movement': motion_index * 0.3,
            'thermal_anomaly': motion_index > 0.15,
            'sound_level_db': 30 + int(motion_index * 40)  # Simulated sound level
        }
    
    def _get_highway_metrics(self, zone_id: str, motion_index: float) -> Dict:
        """Get additional metrics for highway overview cameras"""
        return {
            'avg_vehicle_speed': 60 + int(motion_index * 40),  # km/h
            'traffic_density': motion_index,
            'flow_continuity': motion_index > 0.5,
            'estimated_vehicle_count': int(motion_index * 50)
        }
    
    def update_zone_traffic(self, zone_id: str, vehicle_count: int):
        """Update traffic count for a zone"""
        self.zone_traffic_counts[zone_id] = vehicle_count
    
    def generate_zone_events(self, zone_id: str, timestamp: datetime,
                           active_journeys: int = 0, is_scenario: bool = False,
                           scenario_type: str = None) -> List[Dict]:
        """Generate events for all cameras in a zone"""
        events = []
        
        if zone_id not in self.cameras_per_zone:
            return events
        
        for camera in self.cameras_per_zone[zone_id]:
            event = self.generate_event(
                camera['camera_id'], timestamp, active_journeys,
                is_scenario, scenario_type
            )
            if event:
                events.append(event)
        
        return events
    
    def generate_all_zone_events(self, timestamp: datetime,
                               zone_journey_counts: Dict[str, int] = None,
                               active_scenarios: Dict[str, str] = None) -> List[Dict]:
        """Generate events for all zones"""
        all_events = []
        
        for zone_id in ZONES.keys():
            # Get journey count for this zone
            journey_count = zone_journey_counts.get(zone_id, 0) if zone_journey_counts else 0
            
            # Check for active scenarios in this zone
            is_scenario = False
            scenario_type = None
            if active_scenarios and zone_id in active_scenarios:
                is_scenario = True
                scenario_type = active_scenarios[zone_id]
            
            # Generate events for this zone
            zone_events = self.generate_zone_events(
                zone_id, timestamp, journey_count, is_scenario, scenario_type
            )
            all_events.extend(zone_events)
        
        return all_events
    
    def get_camera_count(self) -> int:
        """Get total number of cameras"""
        return sum(len(cameras) for cameras in self.cameras_per_zone.values())
    
    def get_zone_camera_count(self, zone_id: str) -> int:
        """Get number of cameras in a specific zone"""
        return len(self.cameras_per_zone.get(zone_id, []))
    
    def get_event_rate(self) -> int:
        """Get expected CCTV event rate"""
        # One event per camera per frame window
        return self.get_camera_count()