"""
Journey Reconstruction Engine
Processes enriched events from ingestion pipeline and builds complete journey objects
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from sqlalchemy import select
from ..db.session import get_db_session
from ..db.models import Journey
from .state import JourneyStateManager, JourneyCheckpoint as StateCheckpoint

logger = logging.getLogger(__name__)

@dataclass
class ReconstructedJourney:
    """Complete reconstructed journey with all events and metrics"""
    journey_id: str
    plate_number: str
    direction: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # 'active', 'completed', 'expired'
    
    checkpoints: List[Dict[str, Any]]
    payment_events: List[Dict[str, Any]]
    
    # Calculated metrics
    total_distance: float
    total_time: int  # seconds
    avg_speed: float
    max_speed: float
    
    # Payment metrics
    total_toll_paid: float
    toll_plazas_visited: int
    toll_plazas_expected: int
    payment_completeness: float
    
    # Evasion metrics
    evasion_score: float
    evasion_flags: List[str]
    ml_evasion_probability: Optional[float]
    
    # Quality metrics
    checkpoint_completeness: float
    time_deviation: float  # seconds from expected
    data_quality_score: float

class JourneyReconstructionEngine:
    """Reconstructs complete journeys from enriched events"""
    
    def __init__(self, redis_client, db_session_factory=None):
        self.redis_client = redis_client
        self.db_session_factory = db_session_factory or get_db_session
        self.state_manager = JourneyStateManager(redis_client)
        
        # Journey reconstruction configuration
        self.journey_timeout_seconds = 7200  # 2 hours
        self.checkpoint_timeout_seconds = 300  # 5 minutes between checkpoints
        self.expected_checkpoint_interval = 600  # 10 minutes expected
        
        # Speed thresholds for evasion detection
        self.evasion_speed_threshold = 91.0  # km/h (from simulator config)
        self.normal_speed_range = (60, 85)  # km/h
        
        logger.info("🚀 Journey Reconstruction Engine initialized")
    
    async def process_enriched_event(self, enriched_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single enriched event and update journey reconstruction"""
        
        try:
            event_type = enriched_event.get('event_type')
            plate_number = enriched_event.get('plate_number')
            
            if not event_type or not plate_number:
                logger.warning("Missing event_type or plate_number in enriched event")
                return None
            
            # Process based on event type
            if event_type == 'anpr':
                return await self._process_anpr_event(enriched_event)
            elif event_type == 'fastag':
                return await self._process_fastag_event(enriched_event)
            elif event_type == 'cctv':
                return await self._process_cctv_event(enriched_event)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to process enriched event: {e}")
            return None
    
    async def _process_anpr_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an enriched ANPR event"""
        
        plate_number = event['plate_number']
        direction = event.get('direction', 'MB')
        timestamp = datetime.fromisoformat(event['timestamp'])
        checkpoint_id = event['checkpoint_id']
        
        # Get or create journey state
        journey = await self.state_manager.get_or_create_journey(
            plate_number, direction, timestamp.isoformat()
        )
        
        # Create checkpoint record
        checkpoint = StateCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp.isoformat(),
            event_type='anpr',
            event_id=event.get('event_id', ''),
            confidence=event.get('confidence'),
            speed_kmh=event.get('speed_kmh'),
            direction=direction
        )
        
        # Add checkpoint to journey
        await self.state_manager.add_checkpoint(plate_number, checkpoint)
        
        # Check for evasion indicators
        await self._check_anpr_evasion_indicators(journey, event)
        
        # Update journey metrics
        await self._update_journey_from_anpr(journey, event)
        
        # Check if journey should be completed
        if await self._should_complete_journey(journey):
            return await self._complete_journey_reconstruction(journey)
        
        return {
            'status': 'processed',
            'journey_id': journey.journey_id,
            'checkpoint_added': checkpoint_id,
            'evasion_flags': journey.evasion_flags
        }
    
    async def _process_fastag_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an enriched FASTag event"""
        
        plate_number = event['plate_number']
        timestamp = datetime.fromisoformat(event['timestamp'])
        checkpoint_id = event['checkpoint_id']
        amount = event.get('amount_charged', 0.0)
        transaction_status = event.get('transaction_status', 'success')
        
        # Get existing journey
        journey = await self.state_manager.get_journey(plate_number)
        if not journey:
            logger.warning(f"No active journey found for {plate_number} when processing FASTag")
            return None
        
        # Add payment to journey
        await self.state_manager.add_payment(plate_number, checkpoint_id, amount, timestamp.isoformat())
        
        # Check for payment anomalies
        await self._check_payment_anomalies(journey, event)
        
        # Check for evasion indicators
        await self._check_fastag_evasion_indicators(journey, event)
        
        return {
            'status': 'processed',
            'journey_id': journey.journey_id,
            'payment_added': checkpoint_id,
            'amount': amount,
            'transaction_status': transaction_status
        }
    
    async def _process_cctv_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an enriched CCTV event"""
        
        # CCTV events are used for zone state aggregation, not journey reconstruction
        # Just log and return basic info
        zone_id = event.get('zone_id')
        motion_index = event.get('motion_index')
        
        return {
            'status': 'processed',
            'zone_id': zone_id,
            'motion_index': motion_index,
            'note': 'CCTV events used for zone aggregation'
        }
    
    async def _check_anpr_evasion_indicators(self, journey, event: Dict[str, Any]):
        """Check ANPR event for evasion indicators"""
        
        # Speed-based evasion (E5)
        speed = event.get('speed_kmh')
        if speed and speed > self.evasion_speed_threshold:
            await self.state_manager.add_evasion_flag(
                journey.plate_number, 
                'E5_SPEED_ANOMALY',
                {'speed': speed, 'threshold': self.evasion_speed_threshold}
            )
        
        # Confidence-based evasion (mud/obstruction simulation)
        confidence = event.get('confidence')
        if confidence and confidence < 0.85:
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'LOW_CONFIDENCE_READ',
                {'confidence': confidence}
            )
        
        # Class mismatch evasion (E3)
        detected_class = event.get('detected_class')
        registered_class = event.get('registered_class')
        if detected_class and registered_class and detected_class != registered_class:
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'E3_CLASS_MISMATCH',
                {'detected': detected_class, 'registered': registered_class}
            )
        
        # Ghost vehicle (E4)
        vehicle_db_match = event.get('vehicle_db_match')
        if vehicle_db_match is False:
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'E4_UNREGISTERED_VEHICLE',
                {'plate': event.get('plate_number')}
            )
    
    async def _check_fastag_evasion_indicators(self, journey, event: Dict[str, Any]):
        """Check FASTag event for evasion indicators"""
        
        # No FASTag where expected (E1)
        transaction_status = event.get('transaction_status')
        if transaction_status == 'failed':
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'E1_NO_FASTAG',
                {'checkpoint': event.get('checkpoint_id')}
            )
        
        # Class swapper evasion (E2/E3)
        vehicle_class_tagged = event.get('vehicle_class_tagged')
        vehicle_class_registered = event.get('vehicle_class_registered')
        if (vehicle_class_tagged and vehicle_class_registered and 
            vehicle_class_tagged != vehicle_class_registered):
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'E2_CLASS_SWAP',
                {'tagged': vehicle_class_tagged, 'registered': vehicle_class_registered}
            )
    
    async def _check_payment_anomalies(self, journey, event: Dict[str, Any]):
        """Check for payment anomalies"""
        
        transaction_status = event.get('transaction_status')
        
        if transaction_status == 'low_balance':
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'LOW_BALANCE_WARNING',
                {'checkpoint': event.get('checkpoint_id')}
            )
        
        elif transaction_status == 'blacklisted':
            await self.state_manager.add_evasion_flag(
                journey.plate_number,
                'BLACKLISTED_TAG',
                {'checkpoint': event.get('checkpoint_id')}
            )
    
    async def _update_journey_from_anpr(self, journey, event: Dict[str, Any]):
        """Update journey metrics from ANPR event"""
        
        # Update max speed if this event has higher speed
        speed = event.get('speed_kmh')
        if speed and speed > journey.max_speed:
            journey.max_speed = speed
    
    async def _should_complete_journey(self, journey) -> bool:
        """Determine if journey should be marked as completed"""
        
        # Check if we've seen both entry and exit checkpoints
        checkpoint_ids = [cp.checkpoint_id for cp in journey.checkpoints_visited]
        
        if journey.direction == 'MB':  # Mysore to Bangalore
            has_entry = 'CP-01' in checkpoint_ids
            has_exit = 'CP-12' in checkpoint_ids
        else:  # Bangalore to Mysore
            has_entry = 'CP-12' in checkpoint_ids
            has_exit = 'CP-01' in checkpoint_ids
        
        # Complete if we have both entry and exit
        if has_entry and has_exit:
            return True
        
        # Or if journey has been active too long (timeout)
        start_time = datetime.fromisoformat(journey.start_time)
        if (datetime.now() - start_time).total_seconds() > self.journey_timeout_seconds:
            return True
        
        return False
    
    async def _complete_journey_reconstruction(self, journey) -> Dict[str, Any]:
        """Complete journey reconstruction and save to database"""
        
        # Mark journey as completed in state
        await self.state_manager.complete_journey(journey.plate_number, datetime.now().isoformat())
        
        # Build complete reconstructed journey
        reconstructed = await self._build_reconstructed_journey(journey)
        
        # Save to database
        await self._save_reconstructed_journey(reconstructed)
        
        # Generate alerts if needed
        alerts = await self._generate_journey_alerts(reconstructed)
        
        logger.info(f"🛣️ Journey reconstruction completed: {journey.journey_id} "
                   f"(evasion_score: {reconstructed.evasion_score:.2f})")
        
        return {
            'status': 'journey_completed',
            'journey_id': reconstructed.journey_id,
            'evasion_score': reconstructed.evasion_score,
            'alerts_generated': len(alerts)
        }
    
    async def _build_reconstructed_journey(self, journey) -> ReconstructedJourney:
        """Build complete reconstructed journey from state"""
        
        # Separate checkpoints by type
        checkpoints = []
        payment_events = []
        
        for cp in journey.checkpoints_visited:
            if cp.event_type == 'anpr':
                checkpoints.append({
                    'checkpoint_id': cp.checkpoint_id,
                    'timestamp': cp.timestamp,
                    'confidence': cp.confidence,
                    'speed_kmh': cp.speed_kmh,
                    'direction': cp.direction
                })
            elif cp.event_type == 'fastag':
                payment_events.append({
                    'checkpoint_id': cp.checkpoint_id,
                    'timestamp': cp.timestamp,
                    'amount': 0.0  # Would need to track amounts separately
                })
        
        # Calculate final metrics
        start_time = datetime.fromisoformat(journey.start_time)
        end_time = datetime.fromisoformat(journey.last_update) if journey.last_update else None
        
        total_time = journey.total_time if journey.total_time > 0 else 0
        avg_speed = journey.avg_speed if journey.avg_speed > 0 else 0.0
        
        # Extract evasion flags
        evasion_flags = []
        for flag in journey.evasion_flags:
            if ':' in flag:
                flag_type = flag.split(':')[0]
                evasion_flags.append(flag_type)
        
        return ReconstructedJourney(
            journey_id=journey.journey_id,
            plate_number=journey.plate_number,
            direction=journey.direction,
            start_time=start_time,
            end_time=end_time,
            status=journey.status,
            checkpoints=checkpoints,
            payment_events=payment_events,
            total_distance=journey.total_distance,
            total_time=total_time,
            avg_speed=avg_speed,
            max_speed=journey.max_speed if hasattr(journey, 'max_speed') else 0.0,
            total_toll_paid=journey.total_toll_paid,
            toll_plazas_visited=journey.toll_plazas_visited,
            toll_plazas_expected=journey.toll_plazas_expected,
            payment_completeness=journey.payment_completeness,
            evasion_score=journey.evasion_score,
            evasion_flags=evasion_flags,
            ml_evasion_probability=None,  # Will be set by ML service
            checkpoint_completeness=journey.checkpoint_completeness,
            time_deviation=journey.time_deviation,
            data_quality_score=0.0  # Would calculate based on confidence scores, etc.
        )
    
    async def _save_reconstructed_journey(self, journey: ReconstructedJourney) -> bool:
        """Save reconstructed journey to database"""
        
        try:
            async with self.db_session_factory() as session:
                # Create journey record matching database schema
                db_journey = Journey(
                    journey_id=journey.journey_id,
                    highway_id='NH-275',
                    plate=journey.plate_number,
                    direction=journey.direction,
                    vehicle_class_anpr=None,  # Would need to track from checkpoints
                    vehicle_class_registered=None,
                    vehicle_class_fastag=None,
                    entry_checkpoint=journey.checkpoints[0]['checkpoint_id'] if journey.checkpoints else None,
                    exit_checkpoint=journey.checkpoints[-1]['checkpoint_id'] if journey.checkpoints else None,
                    entry_time=journey.start_time,
                    exit_time=journey.end_time,
                    last_checkpoint=journey.checkpoints[-1]['checkpoint_id'] if journey.checkpoints else None,
                    last_seen=journey.end_time or journey.start_time,
                    checkpoints_visited=[cp['checkpoint_id'] for cp in journey.checkpoints],
                    expected_checkpoints=[],  # Would need to track expected sequence
                    status=journey.status,
                    journey_start=journey.start_time,
                    updated_at=datetime.now()
                )
                
                session.add(db_journey)
                await session.commit()
                logger.info(f"💾 Saved reconstructed journey to database: {journey.journey_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save reconstructed journey: {e}")
            return False
    
    async def _generate_journey_alerts(self, journey: ReconstructedJourney) -> List[Dict[str, Any]]:
        """Generate alerts based on journey reconstruction"""
        
        alerts = []
        
        # High evasion score alert
        if journey.evasion_score > 0.7:
            alerts.append({
                'alert_type': 'HIGH_EVASION_PROBABILITY',
                'severity': 'high',
                'journey_id': journey.journey_id,
                'plate_number': journey.plate_number,
                'details': {
                    'evasion_score': journey.evasion_score,
                    'flags': journey.evasion_flags
                }
            })
        
        # Low payment completeness alert
        if journey.payment_completeness < 0.5:
            alerts.append({
                'alert_type': 'LOW_PAYMENT_COMPLETENESS',
                'severity': 'medium',
                'journey_id': journey.journey_id,
                'plate_number': journey.journey_id,
                'details': {
                    'completeness': journey.payment_completeness,
                    'visited': journey.toll_plazas_visited,
                    'expected': journey.toll_plazas_expected
                }
            })
        
        return alerts
    
    async def get_journey_reconstruction(self, journey_id: str) -> Optional[ReconstructedJourney]:
        """Get reconstructed journey by ID"""
        
        try:
            async with self.db_session_factory() as session:
                # Query journey from database
                result = await session.execute(
                    select(Journey).where(Journey.journey_id == journey_id)
                )
                db_journey = result.scalar_one_or_none()
                
                if not db_journey:
                    return None
                
                # Build reconstructed journey with available fields
                return ReconstructedJourney(
                    journey_id=db_journey.journey_id,
                    plate_number=db_journey.plate,
                    direction=db_journey.direction,
                    start_time=db_journey.journey_start,
                    end_time=db_journey.exit_time,
                    status=db_journey.status,
                    checkpoints=[],  # Would load from database
                    payment_events=[],
                    total_distance=0.0,  # Not available in current schema
                    total_time=0,  # Not available in current schema
                    avg_speed=0.0,  # Not available in current schema
                    max_speed=0.0,  # Not available in current schema
                    total_toll_paid=0.0,  # Not available in current schema
                    toll_plazas_visited=0,  # Not available in current schema
                    toll_plazas_expected=0,  # Not available in current schema
                    payment_completeness=0.0,  # Not available in current schema
                    evasion_score=0.0,  # Not available in current schema
                    ml_evasion_probability=None,  # Not available in current schema
                    checkpoint_completeness=0.0,  # Not available in current schema
                    time_deviation=0.0,  # Not available in current schema
                    data_quality_score=0.0,  # Not available in current schema
                    evasion_flags=[]  # Would load from flags
                )
                
        except Exception as e:
            logger.error(f"Failed to get journey reconstruction: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get reconstruction engine status"""
        
        return {
            'engine_status': 'active',
            'state_manager_connected': self.state_manager is not None,
            'journey_timeout_seconds': self.journey_timeout_seconds,
            'checkpoint_timeout_seconds': self.checkpoint_timeout_seconds,
            'evasion_speed_threshold': self.evasion_speed_threshold
        }