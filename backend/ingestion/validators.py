"""
Event Validation Utilities
Validates incoming events from Redis streams before processing
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..db.session import get_db
from ..db.models import Vehicle, Checkpoint

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of event validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_data: Dict[str, Any]

class EventValidator:
    """Validates incoming events from Redis streams"""
    
    def __init__(self):
        # Plate number patterns for different states
        self.plate_patterns = {
            'KA': re.compile(r'^KA\d{2}[A-Z]{2}\d{4}$'),  # Karnataka
            'TN': re.compile(r'^TN\d{2}[A-Z]{2}\d{4}$'),  # Tamil Nadu
            'AP': re.compile(r'^AP\d{2}[A-Z]{2}\d{4}$'),  # Andhra Pradesh
            'KL': re.compile(r'^KL\d{2}[A-Z]{2}\d{4}$'),  # Kerala
            'MH': re.compile(r'^MH\d{2}[A-Z]{2}\d{4}$'),  # Maharashtra
            'DL': re.compile(r'^DL\d{2}[A-Z]{2}\d{4}$'),  # Delhi
            'GJ': re.compile(r'^GJ\d{2}[A-Z]{2}\d{4}$'),  # Gujarat
            'RJ': re.compile(r'^RJ\d{2}[A-Z]{2}\d{4}$'),  # Rajasthan
            'WB': re.compile(r'^WB\d{2}[A-Z]{2}\d{4}$'),  # West Bengal
            'OR': re.compile(r'^OR\d{2}[A-Z]{2}\d{4}$'),  # Odisha
            'HR': re.compile(r'^HR\d{2}[A-Z]{2}\d{4}$'),  # Haryana
            'PB': re.compile(r'^PB\d{2}[A-Z]{2}\d{4}$'),  # Punjab
            'UP': re.compile(r'^UP\d{2}[A-Z]{2}\d{4}$'),  # Uttar Pradesh
            'BR': re.compile(r'^BR\d{2}[A-Z]{2}\d{4}$'),  # Bihar
            'MP': re.compile(r'^MP\d{2}[A-Z]{2}\d{4}$'),  # Madhya Pradesh
            'CG': re.compile(r'^CG\d{2}[A-Z]{2}\d{4}$'),  # Chhattisgarh
            'JH': re.compile(r'^JH\d{2}[A-Z]{2}\d{4}$'),  # Jharkhand
            'TS': re.compile(r'^TS\d{2}[A-Z]{2}\d{4}$'),  # Telangana
            'GA': re.compile(r'^GA\d{2}[A-Z]{2}\d{4}$'),  # Goa
            'PY': re.compile(r'^PY\d{2}[A-Z]{2}\d{4}$'),  # Puducherry
            'CH': re.compile(r'^CH\d{2}[A-Z]{2}\d{4}$'),  # Chandigarh
            'HP': re.compile(r'^HP\d{2}[A-Z]{2}\d{4}$'),  # Himachal Pradesh
            'JK': re.compile(r'^JK\d{2}[A-Z]{2}\d{4}$'),  # Jammu & Kashmir
            'UK': re.compile(r'^UK\d{2}[A-Z]{2}\d{4}$'),  # Uttarakhand
            'SK': re.compile(r'^SK\d{2}[A-Z]{2}\d{4}$'),  # Sikkim
            'AR': re.compile(r'^AR\d{2}[A-Z]{2}\d{4}$'),  # Arunachal Pradesh
            'AS': re.compile(r'^AS\d{2}[A-Z]{2}\d{4}$'),  # Assam
            'ML': re.compile(r'^ML\d{2}[A-Z]{2}\d{4}$'),  # Meghalaya
            'MN': re.compile(r'^MN\d{2}[A-Z]{2}\d{4}$'),  # Manipur
            'MZ': re.compile(r'^MZ\d{2}[A-Z]{2}\d{4}$'),  # Mizoram
            'NL': re.compile(r'^NL\d{2}[A-Z]{2}\d{4}$'),  # Nagaland
            'TR': re.compile(r'^TR\d{2}[A-Z]{2}\d{4}$'),  # Tripura
        }
        
        # Valid vehicle classes
        self.valid_vehicle_classes = [
            'Car', 'LMV', 'Bus', 'Truck', 'MAV', '2W', '3W', 'Tractor', 'Trailer'
        ]
        
        # Valid directions
        self.valid_directions = ['MB', 'BM']  # Mysore to Bangalore, Bangalore to Mysore
        
        # Valid checkpoint IDs
        self.valid_checkpoint_ids = [
            'CP-01', 'CP-02', 'CP-03', 'CP-04', 'CP-05', 'CP-06',
            'CP-07', 'CP-08', 'CP-09', 'CP-10', 'CP-11', 'CP-12'
        ]
        
        # Valid zone IDs
        self.valid_zone_ids = [
            'ZONE-01', 'ZONE-02', 'ZONE-03', 'ZONE-04', 'ZONE-05',
            'ZONE-06', 'ZONE-07', 'ZONE-08', 'ZONE-09', 'ZONE-10', 'ZONE-11'
        ]
        
        # Valid camera types
        self.valid_camera_types = ['toll_booth', 'overview', 'wildlife_monitor', 'highway_overview']
        
        # Valid transaction statuses
        self.valid_transaction_statuses = ['success', 'low_balance', 'failed', 'blacklisted']
        
        # Valid weather conditions
        self.valid_weather_conditions = ['WX-CLR', 'WX-RA', 'WX-FG']
    
    async def validate(self, event) -> ValidationResult:
        """Validate an event based on its type"""
        
        errors = []
        warnings = []
        normalized_data = {}
        
        try:
            # Determine event type from stream name
            if 'anpr' in event.stream_name:
                return await self._validate_anpr_event(event)
            elif 'fastag' in event.stream_name:
                return await self._validate_fastag_event(event)
            elif 'cctv' in event.stream_name:
                return await self._validate_cctv_event(event)
            else:
                errors.append(f"Unknown event stream: {event.stream_name}")
                return ValidationResult(False, errors, warnings, {})
                
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(False, errors, warnings, {})
    
    async def _validate_anpr_event(self, event) -> ValidationResult:
        """Validate ANPR event"""
        errors = []
        warnings = []
        normalized_data = event.data.copy()
        
        # Validate plate number
        plate_number = event.data.get('plate_number')
        if not plate_number:
            errors.append("Missing plate_number")
        else:
            plate_number = str(plate_number).upper().strip()
            state_code = plate_number[:2]
            
            if state_code in self.plate_patterns:
                if not self.plate_patterns[state_code].match(plate_number):
                    errors.append(f"Invalid plate number format: {plate_number}")
            else:
                warnings.append(f"Unknown state code: {state_code}")
            
            normalized_data['plate_number'] = plate_number
        
        # Validate checkpoint ID
        checkpoint_id = event.data.get('checkpoint_id')
        if not checkpoint_id:
            errors.append("Missing checkpoint_id")
        elif checkpoint_id not in self.valid_checkpoint_ids:
            errors.append(f"Invalid checkpoint_id: {checkpoint_id}")
        
        # Validate timestamp
        timestamp = event.data.get('timestamp')
        if not timestamp:
            errors.append("Missing timestamp")
        else:
            try:
                # Parse ISO format timestamp
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid timestamp format: {timestamp}")
        
        # Validate confidence score
        confidence = event.data.get('confidence')
        if confidence is not None:
            try:
                confidence = float(confidence)
                if not 0.0 <= confidence <= 1.0:
                    errors.append(f"Confidence must be between 0.0 and 1.0: {confidence}")
                normalized_data['confidence'] = confidence
            except (ValueError, TypeError):
                errors.append(f"Invalid confidence value: {confidence}")
        
        # Validate vehicle class
        detected_class = event.data.get('detected_class')
        if detected_class and detected_class not in self.valid_vehicle_classes:
            warnings.append(f"Unknown vehicle class: {detected_class}")
        
        registered_class = event.data.get('registered_class')
        if registered_class and registered_class not in self.valid_vehicle_classes:
            warnings.append(f"Unknown registered vehicle class: {registered_class}")
        
        # Validate direction
        direction = event.data.get('direction')
        if direction and direction not in self.valid_directions:
            errors.append(f"Invalid direction: {direction}. Must be MB or BM")
        
        # Validate speed
        speed = event.data.get('speed_kmh')
        if speed is not None:
            try:
                speed = float(speed)
                if speed < 0 or speed > 200:
                    warnings.append(f"Unusual speed value: {speed} km/h")
                normalized_data['speed_kmh'] = speed
            except (ValueError, TypeError):
                errors.append(f"Invalid speed value: {speed}")
        
        # Validate camera ID format
        camera_id = event.data.get('camera_id')
        if camera_id:
            if not re.match(r'^CAM-[A-Z0-9-]+-\d+$', str(camera_id)):
                warnings.append(f"Unusual camera ID format: {camera_id}")
        
        # Validate weather condition
        weather = event.data.get('weather_condition')
        if weather and weather not in self.valid_weather_conditions:
            warnings.append(f"Unknown weather condition: {weather}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, normalized_data)
    
    async def _validate_fastag_event(self, event) -> ValidationResult:
        """Validate FASTag event"""
        errors = []
        warnings = []
        normalized_data = event.data.copy()
        
        # Validate plate number (same as ANPR)
        plate_number = event.data.get('plate_number')
        if not plate_number:
            errors.append("Missing plate_number")
        else:
            plate_number = str(plate_number).upper().strip()
            state_code = plate_number[:2]
            
            if state_code in self.plate_patterns:
                if not self.plate_patterns[state_code].match(plate_number):
                    errors.append(f"Invalid plate number format: {plate_number}")
            else:
                warnings.append(f"Unknown state code: {state_code}")
            
            normalized_data['plate_number'] = plate_number
        
        # Validate checkpoint ID
        checkpoint_id = event.data.get('checkpoint_id')
        if not checkpoint_id:
            errors.append("Missing checkpoint_id")
        elif checkpoint_id not in self.valid_checkpoint_ids:
            errors.append(f"Invalid checkpoint_id: {checkpoint_id}")
        
        # Validate timestamp
        timestamp = event.data.get('timestamp')
        if not timestamp:
            errors.append("Missing timestamp")
        else:
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid timestamp format: {timestamp}")
        
        # Validate transaction status
        transaction_status = event.data.get('transaction_status')
        if transaction_status and transaction_status not in self.valid_transaction_statuses:
            errors.append(f"Invalid transaction status: {transaction_status}")
        
        # Validate amount charged
        amount = event.data.get('amount_charged')
        if amount is not None:
            try:
                amount = float(amount)
                if amount < 0:
                    errors.append(f"Amount charged cannot be negative: {amount}")
                elif amount > 1000:
                    warnings.append(f"Unusually high amount charged: ₹{amount}")
                normalized_data['amount_charged'] = amount
            except (ValueError, TypeError):
                errors.append(f"Invalid amount charged: {amount}")
        
        # Validate vehicle classes
        tagged_class = event.data.get('vehicle_class_tagged')
        if tagged_class and tagged_class not in self.valid_vehicle_classes:
            warnings.append(f"Unknown tagged vehicle class: {tagged_class}")
        
        registered_class = event.data.get('vehicle_class_registered')
        if registered_class and registered_class not in self.valid_vehicle_classes:
            warnings.append(f"Unknown registered vehicle class: {registered_class}")
        
        # Validate direction
        direction = event.data.get('direction')
        if direction and direction not in self.valid_directions:
            errors.append(f"Invalid direction: {direction}. Must be MB or BM")
        
        # Validate lane number
        lane_number = event.data.get('lane_number')
        if lane_number is not None:
            try:
                lane_number = int(lane_number)
                if lane_number < 1 or lane_number > 10:
                    warnings.append(f"Unusual lane number: {lane_number}")
                normalized_data['lane_number'] = lane_number
            except (ValueError, TypeError):
                errors.append(f"Invalid lane number: {lane_number}")
        
        # Validate plaza ID
        plaza_id = event.data.get('plaza_id')
        if plaza_id and plaza_id not in self.valid_checkpoint_ids:
            errors.append(f"Invalid plaza_id: {plaza_id}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, normalized_data)
    
    async def _validate_cctv_event(self, event) -> ValidationResult:
        """Validate CCTV event"""
        errors = []
        warnings = []
        normalized_data = event.data.copy()
        
        # Validate camera ID
        camera_id = event.data.get('camera_id')
        if not camera_id:
            errors.append("Missing camera_id")
        else:
            if not re.match(r'^CAM-[A-Z0-9-]+-\d+$', str(camera_id)):
                warnings.append(f"Unusual camera ID format: {camera_id}")
        
        # Validate zone ID
        zone_id = event.data.get('zone_id')
        if not zone_id:
            errors.append("Missing zone_id")
        elif zone_id not in self.valid_zone_ids:
            errors.append(f"Invalid zone_id: {zone_id}")
        
        # Validate timestamp
        timestamp = event.data.get('timestamp')
        if not timestamp:
            errors.append("Missing timestamp")
        else:
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid timestamp format: {timestamp}")
        
        # Validate motion index
        motion_index = event.data.get('motion_index')
        if motion_index is not None:
            try:
                motion_index = float(motion_index)
                if not 0.0 <= motion_index <= 1.0:
                    errors.append(f"Motion index must be between 0.0 and 1.0: {motion_index}")
                normalized_data['motion_index'] = motion_index
            except (ValueError, TypeError):
                errors.append(f"Invalid motion index: {motion_index}")
        
        # Validate camera type
        camera_type = event.data.get('camera_type')
        if camera_type and camera_type not in self.valid_camera_types:
            warnings.append(f"Unknown camera type: {camera_type}")
        
        # Validate zone type
        zone_type = event.data.get('zone_type')
        valid_zone_types = ['highway', 'toll_plaza', 'forest_corridor', 'urban', 'rural']
        if zone_type and zone_type not in valid_zone_types:
            warnings.append(f"Unknown zone type: {zone_type}")
        
        # Validate active journeys count
        active_journeys = event.data.get('active_journeys')
        if active_journeys is not None:
            try:
                active_journeys = int(active_journeys)
                if active_journeys < 0:
                    errors.append(f"Active journeys cannot be negative: {active_journeys}")
                elif active_journeys > 1000:
                    warnings.append(f"Unusually high active journeys: {active_journeys}")
                normalized_data['active_journeys'] = active_journeys
            except (ValueError, TypeError):
                errors.append(f"Invalid active journeys: {active_journeys}")
        
        # Validate weather condition
        weather = event.data.get('weather_condition')
        if weather and weather not in self.valid_weather_conditions:
            warnings.append(f"Unknown weather condition: {weather}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, normalized_data)
    
    async def validate_vehicle_exists(self, plate_number: str) -> Tuple[bool, Optional[Dict]]:
        """Check if vehicle exists in database"""
        try:
            async with get_db() as db:
                vehicle = await db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
                if vehicle:
                    return True, {
                        'id': vehicle.id,
                        'plate_number': vehicle.plate_number,
                        'registered_class': vehicle.registered_class,
                        'registration_state': vehicle.registration_state,
                        'registration_status': vehicle.registration_status,
                        'owner_type': vehicle.owner_type,
                        'fuel_type': vehicle.fuel_type,
                        'puc_upto': vehicle.puc_upto,
                        'insurance_upto': vehicle.insurance_upto,
                        'fitness_upto': vehicle.fitness_upto
                    }
                return False, None
        except Exception as e:
            logger.error(f"Error checking vehicle existence: {e}")
            return False, None
    
    async def validate_checkpoint_exists(self, checkpoint_id: str) -> Tuple[bool, Optional[Dict]]:
        """Check if checkpoint exists in database"""
        try:
            async with get_db() as db:
                checkpoint = await db.query(Checkpoint).filter(Checkpoint.checkpoint_id == checkpoint_id).first()
                if checkpoint:
                    return True, {
                        'id': checkpoint.id,
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'name': checkpoint.name,
                        'km_marker': checkpoint.km_marker,
                        'zone_id': checkpoint.zone_id,
                        'type': checkpoint.type,
                        'toll': checkpoint.toll,
                        'camera_count': checkpoint.camera_count
                    }
                return False, None
        except Exception as e:
            logger.error(f"Error checking checkpoint existence: {e}")
            return False, None
    
    def validate_timestamp_sequence(self, current_timestamp: str, previous_timestamp: str) -> bool:
        """Validate that current timestamp is after previous timestamp"""
        try:
            current = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            previous = datetime.fromisoformat(previous_timestamp.replace('Z', '+00:00'))
            return current >= previous
        except (ValueError, AttributeError):
            return False