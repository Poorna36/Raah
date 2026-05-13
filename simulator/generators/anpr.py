"""
ANPR (Automatic Number Plate Recognition) Event Generator
Generates ANPR events with realistic confidence scores and error patterns
"""

import random
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..config import ANPR_CONFIG, get_weather_condition

logger = logging.getLogger(__name__)

class ANPRGenerator:
    """Generates ANPR events with realistic patterns and errors"""
    
    def __init__(self):
        self.ocr_error_types = ['transposition', 'missing_char', 'substitution']
        self.confidence_distributions = {
            'normal': ANPR_CONFIG['confidence_normal'],
            'degraded': ANPR_CONFIG['confidence_degraded'], 
            'poor': ANPR_CONFIG['confidence_poor']
        }
    
    def generate_event(self, vehicle_data: Dict, checkpoint: Dict, timestamp: datetime, 
                      is_evasion: bool = False, evasion_type: str = None) -> Dict:
        """Generate a single ANPR event"""
        
        # Base plate number from vehicle data
        plate_number = vehicle_data.get('plate_number', 'UNKNOWN')
        registered_class = vehicle_data.get('registered_class', 'Car')
        
        # Generate confidence score based on conditions
        confidence = self._generate_confidence_score(is_evasion, evasion_type)
        
        # Apply OCR errors if needed
        raw_plate = plate_number
        if random.random() < ANPR_CONFIG['ocr_error_rate']:
            raw_plate = self._apply_ocr_error(plate_number)
        
        # Generate detected class (may differ from registered)
        detected_class = self._generate_detected_class(registered_class, is_evasion)
        
        # Generate speed (affects evasion detection)
        speed_kmh = self._generate_speed(is_evasion, evasion_type)
        
        # Determine direction
        direction = vehicle_data.get('direction', 'MB')
        
        event = {
            'plate_number': raw_plate,  # What the camera actually read
            'registered_plate': plate_number,  # What should be in database
            'checkpoint_id': checkpoint.get('id', 'CP-01'),
            'timestamp': timestamp.isoformat(),
            'confidence': confidence,
            'detected_class': detected_class,
            'registered_class': registered_class,
            'direction': direction,
            'speed_kmh': speed_kmh,
            'camera_id': f"CAM-{checkpoint.get('id', 'CP-01')}-01",
            'weather_condition': get_weather_condition(),
            'is_evasion': is_evasion,
            'evasion_type': evasion_type
        }
        
        # Add night bias for heavy vehicles
        if self._is_night_time(timestamp) and random.random() < ANPR_CONFIG['night_heavy_vehicle_bias']:
            event['detected_class'] = self._get_heavy_vehicle_class()
        
        logger.debug(f"📸 ANPR event generated: {plate_number} at {checkpoint.get('id')} "
                    f"(confidence: {confidence:.3f}, speed: {speed_kmh}km/h)")
        
        return event
    
    def _generate_confidence_score(self, is_evasion: bool, evasion_type: str) -> float:
        """Generate confidence score based on distributions and evasion bias"""
        
        # Demo bias: 80% of toll_skip evasions have confidence < 0.85
        if is_evasion and evasion_type == 'toll_skip' and random.random() < 0.8:
            return random.uniform(0.60, 0.84)
        
        # Normal confidence generation
        rand = random.random()
        cumulative = 0.0
        
        for quality, config in self.confidence_distributions.items():
            cumulative += config['frequency']
            if rand <= cumulative:
                return random.uniform(config['min'], config['max'])
        
        # Fallback to normal
        return random.uniform(0.94, 0.97)
    
    def _apply_ocr_error(self, plate_number: str) -> str:
        """Apply OCR error to plate number"""
        if not plate_number or len(plate_number) < 4:
            return plate_number
        
        error_type = random.choice(self.ocr_error_types)
        
        if error_type == 'transposition':
            # Swap last two characters (usually digits)
            if len(plate_number) >= 2:
                return plate_number[:-2] + plate_number[-1] + plate_number[-2]
        
        elif error_type == 'missing_char':
            # Remove last character
            return plate_number[:-1]
        
        elif error_type == 'substitution':
            # Common substitutions: 0↔O, 1↔I, 2↔Z, 5↔S, 8↔B
            substitutions = {'0': 'O', 'O': '0', '1': 'I', 'I': '1', 
                           '2': 'Z', 'Z': '2', '5': 'S', 'S': '5', '8': 'B', 'B': '8'}
            
            # Find a character to substitute
            for i, char in enumerate(plate_number):
                if char in substitutions:
                    return plate_number[:i] + substitutions[char] + plate_number[i+1:]
        
        return plate_number
    
    def _generate_detected_class(self, registered_class: str, is_evasion: bool) -> str:
        """Generate detected vehicle class (may differ from registered)"""
        
        # Class mismatch simulation (4% of reads)
        if random.random() < ANPR_CONFIG['class_mismatch_rate']:
            # Usually one tier off
            class_tiers = {
                '2W': ['Car'],  # 2W often misread as Car
                'Car': ['LMV', '2W'],
                'LMV': ['Car', 'Bus'],
                'Bus': ['LMV', 'Truck'],
                'Truck': ['Bus', 'MAV'],
                'MAV': ['Truck']
            }
            
            similar_classes = class_tiers.get(registered_class, ['Car'])
            return random.choice(similar_classes)
        
        # For class_swapper evasion, deliberately use lower class
        if is_evasion and random.random() < 0.9:  # 90% demo bias
            if registered_class in ['Truck', 'Bus', 'MAV']:
                return 'Car'  # Heavy vehicle pretending to be car
        
        return registered_class
    
    def _generate_speed(self, is_evasion: bool, evasion_type: str) -> float:
        """Generate vehicle speed with evasion patterns"""
        
        # Demo-optimized signatures: Speed > 91km/h for evaders
        if is_evasion and evasion_type == 'speed_runner':
            # 80% of evaders drive at 91-120 km/h
            return random.uniform(91, 120)
        
        # Normal speed distribution
        if random.random() < 0.95:  # 95% of non-evaders
            return random.uniform(70, 84)  # 70-84 km/h
        else:
            return random.uniform(60, 90)  # Wider range for remaining 5%
    
    def _is_night_time(self, timestamp: datetime) -> bool:
        """Check if it's night time (21:00-05:00)"""
        hour = timestamp.hour
        return hour >= 21 or hour < 5
    
    def _get_heavy_vehicle_class(self) -> str:
        """Get a heavy vehicle class for night bias"""
        heavy_classes = ['Bus', 'Truck', 'MAV']
        weights = [0.3, 0.5, 0.2]  # Bias towards trucks
        return random.choices(heavy_classes, weights=weights)[0]
    
    def generate_batch(self, count: int, checkpoint: Dict, 
                      start_time: datetime, time_interval: float = 1.0) -> List[Dict]:
        """Generate a batch of ANPR events"""
        events = []
        current_time = start_time
        
        for i in range(count):
            # Generate random vehicle data for batch generation
            vehicle_data = self._generate_random_vehicle()
            
            event = self.generate_event(vehicle_data, checkpoint, current_time)
            events.append(event)
            
            # Advance time
            current_time += timedelta(seconds=time_interval)
        
        return events
    
    def _generate_random_vehicle(self) -> Dict:
        """Generate random vehicle data for testing"""
        states = ['KA', 'TN', 'AP', 'KL', 'MH']
        classes = ['Car', 'LMV', 'Bus', 'Truck', 'MAV', '2W']
        
        state = random.choice(states)
        vclass = random.choice(classes)
        
        # Generate realistic plate number
        district = random.randint(1, 99)
        series = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
        number = random.randint(1000, 9999)
        
        return {
            'plate_number': f"{state}{district:02d}{series}{number}",
            'registered_class': vclass,
            'registration_state': state,
            'direction': random.choice(['MB', 'BM'])
        }
    
    def get_event_rate(self, hour: int) -> int:
        """Get expected ANPR event rate for given hour"""
        # Based on traffic rates from config
        from ..config import get_traffic_rate
        
        traffic_rate = get_traffic_rate(hour)
        
        # Assume each vehicle generates 1 ANPR event per checkpoint
        # With 12 checkpoints, but not all vehicles go through all checkpoints
        avg_checkpoints_per_vehicle = 8
        
        return int((traffic_rate * avg_checkpoints_per_vehicle) / 60)  # per minute