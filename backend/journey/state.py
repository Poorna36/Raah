"""
Journey State Management
Manages real-time journey state in Redis for fast access and reconstruction
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class JourneyCheckpoint:
    """Represents a checkpoint in a journey"""
    checkpoint_id: str
    timestamp: str
    event_type: str  # 'anpr' or 'fastag'
    event_id: str
    confidence: Optional[float] = None
    speed_kmh: Optional[float] = None
    direction: Optional[str] = None

@dataclass
class JourneyState:
    """Represents the current state of a vehicle journey"""
    plate_number: str
    journey_id: str
    direction: str  # 'MB' or 'BM'
    start_time: str
    last_update: str
    status: str  # 'active', 'completed', 'expired'
    
    checkpoints_visited: List[JourneyCheckpoint]
    checkpoints_expected: List[str]
    
    total_distance: float = 0.0
    total_time: int = 0  # seconds
    avg_speed: float = 0.0
    
    # Payment tracking
    total_toll_paid: float = 0.0
    toll_plazas_visited: int = 0
    toll_plazas_expected: int = 0
    payment_completeness: float = 0.0
    
    # Evasion tracking
    evasion_flags: List[str]  # List of evasion indicators
    evasion_score: float = 0.0
    
    # Journey metrics
    checkpoint_completeness: float = 0.0
    time_deviation: float = 0.0  # seconds from expected
    
    def __post_init__(self):
        if self.evasion_flags is None:
            self.evasion_flags = []
        if self.checkpoints_visited is None:
            self.checkpoints_visited = []
        if self.checkpoints_expected is None:
            self.checkpoints_expected = []

class JourneyStateManager:
    """Manages journey state in Redis for real-time tracking"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.journey_ttl = 3600  # 1 hour TTL for journey state
        self.checkpoint_ttl = 7200  # 2 hours TTL for checkpoint data
        
        # Journey tracking keys
        self.journey_key_prefix = "journey:"
        self.checkpoint_key_prefix = "checkpoint:"
        self.vehicle_key_prefix = "vehicle:"
        self.active_journeys_key = "active_journeys"
    
    async def get_or_create_journey(self, plate_number: str, direction: str, 
                                   start_time: str) -> JourneyState:
        """Get existing journey or create new one"""
        
        # Try to get existing journey
        existing_journey = await self.get_journey(plate_number)
        if existing_journey and existing_journey.status == 'active':
            return existing_journey
        
        # Create new journey
        journey_id = f"{plate_number}_{start_time}"
        journey = JourneyState(
            plate_number=plate_number,
            journey_id=journey_id,
            direction=direction,
            start_time=start_time,
            last_update=datetime.now().isoformat(),
            status='active',
            checkpoints_visited=[],
            checkpoints_expected=self._get_expected_checkpoints(direction),
            evasion_flags=[]
        )
        
        await self.save_journey(journey)
        return journey
    
    async def get_journey(self, plate_number: str) -> Optional[JourneyState]:
        """Get journey state for a vehicle"""
        
        try:
            journey_key = f"{self.journey_key_prefix}{plate_number}"
            journey_data = await self.redis_client.hgetall(journey_key)
            
            if not journey_data:
                return None
            
            # Convert bytes to strings
            journey_dict = {k.decode('utf-8'): v.decode('utf-8') for k, v in journey_data.items()}
            
            # Parse complex fields
            journey_dict['checkpoints_visited'] = json.loads(journey_dict.get('checkpoints_visited', '[]'))
            journey_dict['checkpoints_expected'] = json.loads(journey_dict.get('checkpoints_expected', '[]'))
            journey_dict['evasion_flags'] = json.loads(journey_dict.get('evasion_flags', '[]'))
            
            # Convert numeric fields
            numeric_fields = ['total_distance', 'total_time', 'avg_speed', 'total_toll_paid', 
                            'toll_plazas_visited', 'toll_plazas_expected', 'payment_completeness',
                            'evasion_score', 'checkpoint_completeness', 'time_deviation']
            
            for field in numeric_fields:
                if field in journey_dict:
                    journey_dict[field] = float(journey_dict[field])
            
            return JourneyState(**journey_dict)
            
        except Exception as e:
            logger.error(f"Failed to get journey for {plate_number}: {e}")
            return None
    
    async def save_journey(self, journey: JourneyState) -> bool:
        """Save journey state to Redis"""
        
        try:
            journey_key = f"{self.journey_key_prefix}{journey.plate_number}"
            
            # Convert journey to dict and handle complex fields
            journey_dict = asdict(journey)
            
            # Serialize complex fields
            journey_dict['checkpoints_visited'] = json.dumps([
                asdict(cp) for cp in journey.checkpoints_visited
            ])
            journey_dict['checkpoints_expected'] = json.dumps(journey.checkpoints_expected)
            journey_dict['evasion_flags'] = json.dumps(journey.evasion_flags)
            
            # Store in Redis
            await self.redis_client.hset(journey_key, mapping=journey_dict)
            await self.redis_client.expire(journey_key, self.journey_ttl)
            
            # Update active journeys set
            if journey.status == 'active':
                await self.redis_client.sadd(self.active_journeys_key, journey.plate_number)
            else:
                await self.redis_client.srem(self.active_journeys_key, journey.plate_number)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save journey {journey.journey_id}: {e}")
            return False
    
    async def add_checkpoint(self, plate_number: str, checkpoint: JourneyCheckpoint) -> bool:
        """Add a checkpoint to a journey"""
        
        journey = await self.get_journey(plate_number)
        if not journey:
            logger.warning(f"Journey not found for {plate_number}")
            return False
        
        # Add checkpoint to journey
        journey.checkpoints_visited.append(checkpoint)
        journey.last_update = datetime.now().isoformat()
        
        # Update journey metrics
        await self._update_journey_metrics(journey)
        
        # Save updated journey
        return await self.save_journey(journey)
    
    async def add_payment(self, plate_number: str, checkpoint_id: str, 
                         amount: float, timestamp: str) -> bool:
        """Add a payment record to a journey"""
        
        journey = await self.get_journey(plate_number)
        if not journey:
            logger.warning(f"Journey not found for {plate_number}")
            return False
        
        # Update payment tracking
        journey.total_toll_paid += amount
        journey.toll_plazas_visited += 1
        
        # Update payment completeness
        if journey.toll_plazas_expected > 0:
            journey.payment_completeness = journey.toll_plazas_visited / journey.toll_plazas_expected
        
        # Add payment checkpoint
        payment_checkpoint = JourneyCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp,
            event_type='fastag',
            event_id=f"payment_{timestamp}",
            direction=journey.direction
        )
        
        journey.checkpoints_visited.append(payment_checkpoint)
        journey.last_update = datetime.now().isoformat()
        
        return await self.save_journey(journey)
    
    async def add_evasion_flag(self, plate_number: str, flag_type: str, 
                              details: Optional[Dict] = None) -> bool:
        """Add an evasion flag to a journey"""
        
        journey = await self.get_journey(plate_number)
        if not journey:
            logger.warning(f"Journey not found for {plate_number}")
            return False
        
        # Add evasion flag
        flag_entry = f"{flag_type}:{datetime.now().isoformat()}"
        if details:
            flag_entry += f":{json.dumps(details)}"
        
        journey.evasion_flags.append(flag_entry)
        
        # Update evasion score (simplified calculation)
        journey.evasion_score = min(1.0, len(journey.evasion_flags) * 0.2)
        
        return await self.save_journey(journey)
    
    async def complete_journey(self, plate_number: str, end_time: str) -> bool:
        """Mark a journey as completed"""
        
        journey = await self.get_journey(plate_number)
        if not journey:
            logger.warning(f"Journey not found for {plate_number}")
            return False
        
        journey.status = 'completed'
        journey.last_update = end_time
        
        # Final calculations
        await self._finalize_journey_metrics(journey)
        
        return await self.save_journey(journey)
    
    async def get_active_journeys(self) -> List[str]:
        """Get list of active journey plate numbers"""
        
        try:
            active_plates = await self.redis_client.smembers(self.active_journeys_key)
            return [plate.decode('utf-8') for plate in active_plates]
        except Exception as e:
            logger.error(f"Failed to get active journeys: {e}")
            return []
    
    async def cleanup_expired_journeys(self) -> int:
        """Clean up expired journey states"""
        
        cleaned_count = 0
        try:
            active_plates = await self.get_active_journeys()
            current_time = datetime.now()
            
            for plate_number in active_plates:
                journey = await self.get_journey(plate_number)
                if journey:
                    # Check if journey has expired (no updates for > 1 hour)
                    last_update = datetime.fromisoformat(journey.last_update)
                    if (current_time - last_update) > timedelta(hours=1):
                        journey.status = 'expired'
                        await self.save_journey(journey)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired journeys")
            
        except Exception as e:
            logger.error(f"Error during journey cleanup: {e}")
        
        return cleaned_count
    
    async def get_journey_summary(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """Get summary statistics for a journey"""
        
        journey = await self.get_journey(plate_number)
        if not journey:
            return None
        
        return {
            'plate_number': journey.plate_number,
            'journey_id': journey.journey_id,
            'direction': journey.direction,
            'status': journey.status,
            'start_time': journey.start_time,
            'last_update': journey.last_update,
            'duration_minutes': journey.total_time / 60 if journey.total_time > 0 else 0,
            'total_distance': journey.total_distance,
            'avg_speed': journey.avg_speed,
            'checkpoints_visited': len(journey.checkpoints_visited),
            'checkpoints_expected': len(journey.checkpoints_expected),
            'checkpoint_completeness': journey.checkpoint_completeness,
            'total_toll_paid': journey.total_toll_paid,
            'toll_plazas_visited': journey.toll_plazas_visited,
            'toll_plazas_expected': journey.toll_plazas_expected,
            'payment_completeness': journey.payment_completeness,
            'evasion_score': journey.evasion_score,
            'evasion_flags': len(journey.evasion_flags),
            'time_deviation': journey.time_deviation
        }
    
    async def _update_journey_metrics(self, journey: JourneyState):
        """Update journey metrics based on checkpoints"""
        
        if not journey.checkpoints_visited:
            return
        
        # Calculate checkpoint completeness
        if journey.checkpoints_expected:
            journey.checkpoint_completeness = len(journey.checkpoints_visited) / len(journey.checkpoints_expected)
        
        # Calculate total distance (simplified - would use actual checkpoint distances)
        journey.total_distance = len(journey.checkpoints_visited) * 10  # Assume 10km between checkpoints
        
        # Calculate total time
        if len(journey.checkpoints_visited) >= 2:
            start_time = datetime.fromisoformat(journey.start_time)
            last_checkpoint_time = datetime.fromisoformat(journey.checkpoints_visited[-1].timestamp)
            journey.total_time = int((last_checkpoint_time - start_time).total_seconds())
            
            # Calculate average speed
            if journey.total_time > 0:
                journey.avg_speed = (journey.total_distance / journey.total_time) * 3600  # km/h
        
        # Calculate toll plaza metrics
        toll_plazas_visited = sum(1 for cp in journey.checkpoints_visited if self._is_toll_plaza(cp.checkpoint_id))
        journey.toll_plazas_visited = toll_plazas_visited
        
        # Calculate expected toll plazas
        journey.toll_plazas_expected = sum(1 for cp_id in journey.checkpoints_expected if self._is_toll_plaza(cp_id))
        
        if journey.toll_plazas_expected > 0:
            journey.payment_completeness = journey.toll_plazas_visited / journey.toll_plazas_expected
    
    async def _finalize_journey_metrics(self, journey: JourneyState):
        """Finalize journey metrics when journey is completed"""
        
        # Calculate final metrics
        await self._update_journey_metrics(journey)
        
        # Calculate time deviation (simplified)
        expected_duration = len(journey.checkpoints_expected) * 600  # 10 minutes per checkpoint
        if journey.total_time > 0:
            journey.time_deviation = journey.total_time - expected_duration
    
    def _get_expected_checkpoints(self, direction: str) -> List[str]:
        """Get expected checkpoint sequence for a direction"""
        
        all_checkpoints = [
            'CP-01', 'CP-02', 'CP-03', 'CP-04', 'CP-05', 'CP-06',
            'CP-07', 'CP-08', 'CP-09', 'CP-10', 'CP-11', 'CP-12'
        ]
        
        if direction == 'BM':  # Bangalore to Mysore (reverse)
            return list(reversed(all_checkpoints))
        
        return all_checkpoints  # Mysore to Bangalore
    
    def _is_toll_plaza(self, checkpoint_id: str) -> bool:
        """Check if checkpoint is a toll plaza"""
        toll_plazas = ['CP-03', 'CP-05', 'CP-08', 'CP-10']  # Toll collection points
        return checkpoint_id in toll_plazas
    
    def get_status(self) -> Dict[str, Any]:
        """Get state manager status"""
        
        return {
            'active_journeys': len(self.get_active_journeys()),
            'journey_ttl': self.journey_ttl,
            'checkpoint_ttl': self.checkpoint_ttl,
            'redis_connected': self.redis_client is not None
        }