"""
FASTag Event Generator
Generates FASTag toll payment events with realistic failure patterns and evasion signatures
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..config import FASTAG_CONFIG, CHECKPOINTS, get_weather_condition

logger = logging.getLogger(__name__)

class FastagGenerator:
    """Generates FASTag events with realistic payment patterns and failures"""
    
    def __init__(self):
        self.failure_rates = FASTAG_CONFIG['failure_rates']
        self.delay_range = FASTAG_CONFIG['delay_range']
        
        # Transaction status probabilities
        self.status_probabilities = {
            'success': 1.0 - sum(self.failure_rates.values()),
            'low_balance': self.failure_rates['low_balance'],
            'failed': self.failure_rates['failed'],
            'blacklisted': self.failure_rates['blacklisted']
        }
    
    def generate_event(self, vehicle_data: Dict, checkpoint: Dict, 
                      timestamp: datetime, anpr_event: Optional[Dict] = None,
                      is_evasion: bool = False, evasion_type: str = None) -> Dict:
        """Generate a single FASTag event"""
        
        # Validate checkpoint has toll collection
        if not checkpoint.get('toll', False):
            logger.warning(f"FASTag event requested for non-toll checkpoint {checkpoint.get('id')}")
            return None
        
        # Base vehicle data
        plate_number = vehicle_data.get('plate_number', 'UNKNOWN')
        registered_class = vehicle_data.get('registered_class', 'Car')
        direction = vehicle_data.get('direction', 'MB')
        
        # Determine transaction status
        transaction_status = self._determine_transaction_status(is_evasion, evasion_type)
        
        # Determine vehicle class for toll calculation
        vehicle_class_tagged = self._determine_vehicle_class(registered_class, is_evasion, evasion_type)
        
        # Calculate toll amount
        amount_charged = self._calculate_toll_amount(checkpoint, vehicle_class_tagged, 
                                                   transaction_status, is_evasion)
        
        # Generate transaction ID
        transaction_id = f"TXN-{plate_number}-{int(timestamp.timestamp() * 1000)}"
        
        event = {
            'plate_number': plate_number,
            'checkpoint_id': checkpoint.get('id', 'CP-01'),
            'timestamp': timestamp.isoformat(),
            'transaction_id': transaction_id,
            'transaction_status': transaction_status,
            'amount_charged': amount_charged,
            'vehicle_class_tagged': vehicle_class_tagged,
            'vehicle_class_registered': registered_class,
            'direction': direction,
            'lane_number': random.randint(1, 6),  # Typical toll plaza lanes
            'tag_id': f"TAG-{plate_number[-6:]}",  # Simulated tag ID
            'plaza_id': checkpoint.get('id', 'CP-01'),
            'weather_condition': get_weather_condition(),
            'is_evasion': is_evasion,
            'evasion_type': evasion_type
        }
        
        # Add payment method and response time
        if transaction_status == 'success':
            event['payment_method'] = 'wallet'
            event['response_time_ms'] = random.randint(200, 800)
        else:
            event['payment_method'] = 'failed'
            event['response_time_ms'] = random.randint(1000, 3000)
            event['failure_reason'] = self._get_failure_reason(transaction_status)
        
        logger.debug(f"💳 FASTag event generated: {plate_number} at {checkpoint.get('id')} "
                    f"(status: {transaction_status}, amount: ₹{amount_charged})")
        
        return event
    
    def _determine_transaction_status(self, is_evasion: bool, evasion_type: str) -> str:
        """Determine transaction status based on failure rates and evasion"""
        
        # Evasion types that result in no FASTag event
        if is_evasion and evasion_type in ['toll_skip', 'ghost_plate']:
            # These evasion types should not generate FASTag events
            # This should be handled by the caller, but return failed if called
            return 'failed'
        
        # Class swapper evasion - transaction succeeds but with wrong class
        if is_evasion and evasion_type == 'class_swapper':
            return 'success'  # Payment goes through but with lower amount
        
        # Normal failure simulation
        rand = random.random()
        cumulative = 0.0
        
        for status, rate in self.status_probabilities.items():
            cumulative += rate
            if rand <= cumulative:
                return status
        
        return 'success'  # Default fallback
    
    def _determine_vehicle_class(self, registered_class: str, is_evasion: bool, evasion_type: str) -> str:
        """Determine vehicle class for toll calculation"""
        
        # Class swapper evasion: use lower class
        if is_evasion and evasion_type == 'class_swapper':
            # Demo bias: 90% are DIESEL trucks misrepresenting as CAR
            if registered_class in ['Truck', 'Bus', 'MAV'] and random.random() < 0.9:
                return 'Car'  # Heavy vehicle pretending to be car
        
        return registered_class
    
    def _calculate_toll_amount(self, checkpoint: Dict, vehicle_class: str, 
                           transaction_status: str, is_evasion: bool) -> int:
        """Calculate toll amount based on checkpoint rates and vehicle class"""
        
        # Get base toll rates for checkpoint
        toll_rates = checkpoint.get('rate', {})
        
        # Get amount for vehicle class
        if transaction_status in ['success', 'low_balance']:
            amount = toll_rates.get(vehicle_class, 0)
        else:
            # Failed transactions: no amount charged
            amount = 0
        
        # Apply evasion discount for class swapper
        if is_evasion and vehicle_class != checkpoint.get('vehicle_class_registered'):
            # Using lower class rate - already calculated in _determine_vehicle_class
            pass
        
        return amount
    
    def _get_failure_reason(self, transaction_status: str) -> str:
        """Get human-readable failure reason"""
        reasons = {
            'low_balance': 'Insufficient balance in FASTag wallet',
            'failed': 'Technical failure during transaction processing',
            'blacklisted': 'Tag is blacklisted by issuing authority'
        }
        return reasons.get(transaction_status, 'Unknown failure reason')
    
    def generate_paired_event(self, anpr_event: Dict, checkpoint: Dict) -> Dict:
        """Generate FASTag event paired with ANPR event"""
        
        # Extract data from ANPR event
        vehicle_data = {
            'plate_number': anpr_event.get('plate_number'),
            'registered_class': anpr_event.get('registered_class', 'Car'),
            'direction': anpr_event.get('direction', 'MB')
        }
        
        # Calculate FASTag timestamp (15-45 seconds after ANPR)
        anpr_timestamp = datetime.fromisoformat(anpr_event['timestamp'])
        delay_seconds = random.randint(self.delay_range['min'], self.delay_range['max'])
        fastag_timestamp = anpr_timestamp + timedelta(seconds=delay_seconds)
        
        # Check for evasion patterns
        is_evasion = anpr_event.get('is_evasion', False)
        evasion_type = anpr_event.get('evasion_type')
        
        return self.generate_event(vehicle_data, checkpoint, fastag_timestamp, 
                                 anpr_event, is_evasion, evasion_type)
    
    def generate_batch(self, count: int, checkpoint: Dict, 
                      start_time: datetime, time_interval: float = 1.0) -> List[Dict]:
        """Generate a batch of FASTag events"""
        events = []
        current_time = start_time
        
        for i in range(count):
            # Generate random vehicle data for batch generation
            vehicle_data = self._generate_random_vehicle()
            
            event = self.generate_event(vehicle_data, checkpoint, current_time)
            if event:  # Skip None events (non-toll checkpoints)
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
        """Get expected FASTag event rate for given hour"""
        # Based on traffic rates from config, but only for toll checkpoints
        from ..config import get_traffic_rate
        
        traffic_rate = get_traffic_rate(hour)
        
        # Count toll checkpoints
        toll_checkpoints = [cp for cp in CHECKPOINTS.values() if cp.get('toll', False)]
        toll_checkpoint_count = len(toll_checkpoints)
        
        # Assume each vehicle goes through ~60% of toll checkpoints
        avg_toll_checkpoints_per_vehicle = int(toll_checkpoint_count * 0.6)
        
        return int((traffic_rate * avg_toll_checkpoints_per_vehicle) / 60)  # per minute
    
    def is_toll_checkpoint(self, checkpoint_id: str) -> bool:
        """Check if checkpoint collects toll"""
        checkpoint = CHECKPOINTS.get(checkpoint_id, {})
        return checkpoint.get('toll', False)
    
    def get_toll_rate(self, checkpoint_id: str, vehicle_class: str) -> int:
        """Get toll rate for vehicle class at checkpoint"""
        checkpoint = CHECKPOINTS.get(checkpoint_id, {})
        if not checkpoint.get('toll', False):
            return 0
        
        rates = checkpoint.get('rate', {})
        return rates.get(vehicle_class, 0)