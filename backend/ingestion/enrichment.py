"""
Event Enrichment Service
Enriches incoming events with additional data from database and external sources
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import redis.asyncio as redis
from sqlalchemy.orm import Session

from ..config import settings
from ..db.session import get_db
from ..db.models import Vehicle, Checkpoint, Zone, Journey

logger = logging.getLogger(__name__)

@dataclass
class EnrichedEvent:
    """Represents an enriched event with additional metadata"""
    original_event: Any
    enriched_data: Dict[str, Any]
    vehicle_info: Optional[Dict[str, Any]] = None
    checkpoint_info: Optional[Dict[str, Any]] = None
    zone_info: Optional[Dict[str, Any]] = None
    journey_info: Optional[Dict[str, Any]] = None
    enrichment_errors: List[str] = None
    
    def __post_init__(self):
        if self.enrichment_errors is None:
            self.enrichment_errors = []

class EventEnricher:
    """Enriches events with vehicle, checkpoint, zone, and journey information"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.enrichment_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    async def enrich(self, event) -> EnrichedEvent:
        """Enrich an event with additional metadata"""
        
        enriched_event = EnrichedEvent(
            original_event=event,
            enriched_data=event.data.copy()
        )
        
        try:
            # Determine event type and enrich accordingly
            if 'anpr' in event.stream_name:
                await self._enrich_anpr_event(enriched_event)
            elif 'fastag' in event.stream_name:
                await self._enrich_fastag_event(enriched_event)
            elif 'cctv' in event.stream_name:
                await self._enrich_cctv_event(enriched_event)
            else:
                enriched_event.enrichment_errors.append(f"Unknown event stream: {event.stream_name}")
            
            # Add common enrichment data
            await self._add_common_enrichment(enriched_event)
            
        except Exception as e:
            logger.error(f"❌ Error enriching event {event.message_id}: {e}")
            enriched_event.enrichment_errors.append(f"Enrichment error: {str(e)}")
        
        return enriched_event
    
    async def _enrich_anpr_event(self, enriched_event: EnrichedEvent):
        """Enrich ANPR event with vehicle and checkpoint information"""
        
        plate_number = enriched_event.enriched_data.get('plate_number')
        checkpoint_id = enriched_event.enriched_data.get('checkpoint_id')
        
        # Enrich vehicle information
        if plate_number:
            vehicle_info = await self._get_vehicle_info(plate_number)
            if vehicle_info:
                enriched_event.vehicle_info = vehicle_info
                enriched_event.enriched_data['vehicle_db_match'] = True
                enriched_event.enriched_data['vehicle_registration_status'] = vehicle_info.get('registration_status')
                enriched_event.enriched_data['vehicle_owner_type'] = vehicle_info.get('owner_type')
                enriched_event.enriched_data['vehicle_fuel_type'] = vehicle_info.get('fuel_type')
                enriched_event.enriched_data['vehicle_puc_upto'] = vehicle_info.get('puc_upto')
                enriched_event.enriched_data['vehicle_insurance_upto'] = vehicle_info.get('insurance_upto')
                enriched_event.enriched_data['vehicle_fitness_upto'] = vehicle_info.get('fitness_upto')
                
                # Check for document expiry
                current_date = datetime.now().date()
                if vehicle_info.get('puc_upto') and vehicle_info['puc_upto'] < current_date:
                    enriched_event.enriched_data['puc_expired'] = True
                if vehicle_info.get('insurance_upto') and vehicle_info['insurance_upto'] < current_date:
                    enriched_event.enriched_data['insurance_expired'] = True
                if vehicle_info.get('fitness_upto') and vehicle_info['fitness_upto'] < current_date:
                    enriched_event.enriched_data['fitness_expired'] = True
            else:
                enriched_event.enriched_data['vehicle_db_match'] = False
                enriched_event.enrichment_errors.append(f"Vehicle not found in database: {plate_number}")
        
        # Enrich checkpoint information
        if checkpoint_id:
            checkpoint_info = await self._get_checkpoint_info(checkpoint_id)
            if checkpoint_info:
                enriched_event.checkpoint_info = checkpoint_info
                enriched_event.enriched_data['checkpoint_name'] = checkpoint_info.get('name')
                enriched_event.enriched_data['checkpoint_km_marker'] = checkpoint_info.get('km_marker')
                enriched_event.enriched_data['checkpoint_zone_id'] = checkpoint_info.get('zone_id')
                enriched_event.enriched_data['checkpoint_type'] = checkpoint_info.get('type')
                enriched_event.enriched_data['checkpoint_toll'] = checkpoint_info.get('toll')
                enriched_event.enriched_data['checkpoint_camera_count'] = checkpoint_info.get('camera_count')
            else:
                enriched_event.enrichment_errors.append(f"Checkpoint not found: {checkpoint_id}")
        
        # Enrich zone information
        if enriched_event.checkpoint_info:
            zone_id = enriched_event.checkpoint_info.get('zone_id')
            if zone_id:
                zone_info = await self._get_zone_info(zone_id)
                if zone_info:
                    enriched_event.zone_info = zone_info
                    enriched_event.enriched_data['zone_name'] = zone_info.get('name')
                    enriched_event.enriched_data['zone_type'] = zone_info.get('type')
                    enriched_event.enriched_data['zone_class'] = zone_info.get('class')
        
        # Get current journey information
        if plate_number:
            journey_info = await self._get_current_journey_info(plate_number)
            if journey_info:
                enriched_event.journey_info = journey_info
                enriched_event.enriched_data['journey_id'] = journey_info.get('journey_id')
                enriched_event.enriched_data['journey_start_time'] = journey_info.get('start_time')
                enriched_event.enriched_data['journey_direction'] = journey_info.get('direction')
                enriched_event.enriched_data['journey_checkpoints_visited'] = journey_info.get('checkpoints_visited', [])
                enriched_event.enriched_data['journey_last_checkpoint'] = journey_info.get('last_checkpoint')
    
    async def _enrich_fastag_event(self, enriched_event: EnrichedEvent):
        """Enrich FASTag event with vehicle and journey information"""
        
        plate_number = enriched_event.enriched_data.get('plate_number')
        checkpoint_id = enriched_event.enriched_data.get('checkpoint_id')
        
        # Enrich vehicle information (same as ANPR)
        if plate_number:
            vehicle_info = await self._get_vehicle_info(plate_number)
            if vehicle_info:
                enriched_event.vehicle_info = vehicle_info
                enriched_event.enriched_data['vehicle_db_match'] = True
                enriched_event.enriched_data['vehicle_class_registered'] = vehicle_info.get('registered_class')
                enriched_event.enriched_data['vehicle_registration_status'] = vehicle_info.get('registration_status')
            else:
                enriched_event.enriched_data['vehicle_db_match'] = False
                enriched_event.enrichment_errors.append(f"Vehicle not found in database: {plate_number}")
        
        # Enrich checkpoint information
        if checkpoint_id:
            checkpoint_info = await self._get_checkpoint_info(checkpoint_id)
            if checkpoint_info:
                enriched_event.checkpoint_info = checkpoint_info
                enriched_event.enriched_data['checkpoint_name'] = checkpoint_info.get('name')
                enriched_event.enriched_data['checkpoint_toll'] = checkpoint_info.get('toll')
                enriched_event.enriched_data['checkpoint_zone_id'] = checkpoint_info.get('zone_id')
                
                # Get toll rates for different vehicle classes
                toll_rates = checkpoint_info.get('toll_rates', {})
                enriched_event.enriched_data['checkpoint_toll_rates'] = toll_rates
            else:
                enriched_event.enrichment_errors.append(f"Checkpoint not found: {checkpoint_id}")
        
        # Calculate payment anomalies
        if enriched_event.vehicle_info and enriched_event.checkpoint_info:
            registered_class = enriched_event.vehicle_info.get('registered_class')
            tagged_class = enriched_event.enriched_data.get('vehicle_class_tagged')
            
            if registered_class and tagged_class and registered_class != tagged_class:
                enriched_event.enriched_data['class_mismatch'] = True
                enriched_event.enriched_data['class_mismatch_details'] = {
                    'registered_class': registered_class,
                    'tagged_class': tagged_class
                }
            else:
                enriched_event.enriched_data['class_mismatch'] = False
        
        # Get journey information for payment context
        if plate_number:
            journey_info = await self._get_current_journey_info(plate_number)
            if journey_info:
                enriched_event.journey_info = journey_info
                enriched_event.enriched_data['journey_id'] = journey_info.get('journey_id')
                enriched_event.enriched_data['journey_payment_history'] = journey_info.get('payment_history', [])
                enriched_event.enriched_data['journey_total_paid'] = journey_info.get('total_paid', 0)
    
    async def _enrich_cctv_event(self, enriched_event: EnrichedEvent):
        """Enrich CCTV event with zone and camera information"""
        
        camera_id = enriched_event.enriched_data.get('camera_id')
        zone_id = enriched_event.enriched_data.get('zone_id')
        
        # Enrich zone information
        if zone_id:
            zone_info = await self._get_zone_info(zone_id)
            if zone_info:
                enriched_event.zone_info = zone_info
                enriched_event.enriched_data['zone_name'] = zone_info.get('name')
                enriched_event.enriched_data['zone_type'] = zone_info.get('type')
                enriched_event.enriched_data['zone_class'] = zone_info.get('class')
                enriched_event.enriched_data['zone_km_start'] = zone_info.get('km_start')
                enriched_event.enriched_data['zone_km_end'] = zone_info.get('km_end')
                enriched_event.enriched_data['zone_length'] = zone_info.get('length')
            else:
                enriched_event.enrichment_errors.append(f"Zone not found: {zone_id}")
        
        # Enrich camera information
        if camera_id:
            camera_info = await self._get_camera_info(camera_id)
            if camera_info:
                enriched_event.enriched_data['camera_position'] = camera_info.get('position_km')
                enriched_event.enriched_data['camera_type'] = camera_info.get('type')
                enriched_event.enriched_data['camera_status'] = camera_info.get('status')
                enriched_event.enriched_data['camera_installation_date'] = camera_info.get('installation_date')
        
        # Calculate motion anomaly indicators
        motion_index = enriched_event.enriched_data.get('motion_index')
        if motion_index is not None:
            # Calculate baseline deviation
            baseline_motion = await self._get_zone_baseline_motion(zone_id)
            if baseline_motion:
                deviation = abs(motion_index - baseline_motion)
                enriched_event.enriched_data['motion_baseline_deviation'] = deviation
                
                # Flag significant deviations
                if deviation > 0.3:  # 30% deviation threshold
                    enriched_event.enriched_data['motion_anomaly'] = True
                    enriched_event.enriched_data['motion_anomaly_severity'] = 'high' if deviation > 0.5 else 'medium'
                else:
                    enriched_event.enriched_data['motion_anomaly'] = False
            
            # Calculate traffic density estimate
            active_journeys = enriched_event.enriched_data.get('active_journeys', 0)
            if active_journeys > 0 and enriched_event.zone_info:
                zone_length = enriched_event.zone_info.get('length', 1)
                density = active_journeys / zone_length
                enriched_event.enriched_data['estimated_traffic_density'] = density
    
    async def _add_common_enrichment(self, enriched_event: EnrichedEvent):
        """Add common enrichment data to all events"""
        
        # Add processing timestamp
        enriched_event.enriched_data['processed_at'] = datetime.now().isoformat()
        
        # Add enrichment version
        enriched_event.enriched_data['enrichment_version'] = "1.0"
        
        # Add data quality score
        quality_score = self._calculate_data_quality_score(enriched_event)
        enriched_event.enriched_data['data_quality_score'] = quality_score
        
        # Add event age (time since original event)
        original_timestamp = enriched_event.enriched_data.get('timestamp')
        if original_timestamp:
            try:
                event_time = datetime.fromisoformat(original_timestamp.replace('Z', '+00:00'))
                age_seconds = (datetime.now() - event_time).total_seconds()
                enriched_event.enriched_data['event_age_seconds'] = age_seconds
                
                # Flag stale events
                if age_seconds > 300:  # 5 minutes
                    enriched_event.enriched_data['stale_event'] = True
                else:
                    enriched_event.enriched_data['stale_event'] = False
            except (ValueError, AttributeError):
                pass
    
    async def _get_vehicle_info(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """Get vehicle information from database or cache"""
        
        cache_key = f"vehicle:{plate_number}"
        
        # Check cache first
        if self.redis_client:
            try:
                cached_data = await self.redis_client.hgetall(cache_key)
                if cached_data:
                    # Convert bytes to strings
                    vehicle_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in cached_data.items()}
                    return vehicle_info
            except Exception as e:
                logger.warning(f"Cache lookup failed for vehicle {plate_number}: {e}")
        
        # Query database
        try:
            async with get_db() as db:
                vehicle = await db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
                if vehicle:
                    vehicle_info = {
                        'id': vehicle.id,
                        'plate_number': vehicle.plate_number,
                        'registered_class': vehicle.registered_class,
                        'registration_state': vehicle.registration_state,
                        'registration_status': vehicle.registration_status,
                        'owner_type': vehicle.owner_type,
                        'fuel_type': vehicle.fuel_type,
                        'maker_model': vehicle.maker_model,
                        'manufacturing_year': vehicle.manufacturing_year,
                        'puc_upto': vehicle.puc_upto.isoformat() if vehicle.puc_upto else None,
                        'insurance_upto': vehicle.insurance_upto.isoformat() if vehicle.insurance_upto else None,
                        'fitness_upto': vehicle.fitness_upto.isoformat() if vehicle.fitness_upto else None,
                        'permit_status': vehicle.permit_status,
                        'permit_type': vehicle.permit_type,
                        'exemption_type': vehicle.exemption_type,
                        'created_at': vehicle.created_at.isoformat(),
                        'updated_at': vehicle.updated_at.isoformat()
                    }
                    
                    # Cache the result
                    if self.redis_client:
                        try:
                            await self.redis_client.hset(cache_key, mapping=vehicle_info)
                            await self.redis_client.expire(cache_key, self.cache_ttl)
                        except Exception as e:
                            logger.warning(f"Cache storage failed for vehicle {plate_number}: {e}")
                    
                    return vehicle_info
                    
        except Exception as e:
            logger.error(f"Database lookup failed for vehicle {plate_number}: {e}")
        
        return None
    
    async def _get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint information from database or cache"""
        
        cache_key = f"checkpoint:{checkpoint_id}"
        
        # Check cache first
        if self.redis_client:
            try:
                cached_data = await self.redis_client.hgetall(cache_key)
                if cached_data:
                    checkpoint_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in cached_data.items()}
                    # Convert numeric fields
                    if 'km_marker' in checkpoint_info:
                        checkpoint_info['km_marker'] = float(checkpoint_info['km_marker'])
                    if 'toll_rates' in checkpoint_info:
                        checkpoint_info['toll_rates'] = eval(checkpoint_info['toll_rates'])
                    return checkpoint_info
            except Exception as e:
                logger.warning(f"Cache lookup failed for checkpoint {checkpoint_id}: {e}")
        
        # Query database
        try:
            async with get_db() as db:
                checkpoint = await db.query(Checkpoint).filter(Checkpoint.checkpoint_id == checkpoint_id).first()
                if checkpoint:
                    checkpoint_info = {
                        'id': checkpoint.id,
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'name': checkpoint.name,
                        'km_marker': checkpoint.km_marker,
                        'zone_id': checkpoint.zone_id,
                        'type': checkpoint.type,
                        'toll': checkpoint.toll,
                        'toll_rates': checkpoint.toll_rates,
                        'camera_count': checkpoint.camera_count,
                        'sensor_reliability': checkpoint.sensor_reliability,
                        'created_at': checkpoint.created_at.isoformat(),
                        'updated_at': checkpoint.updated_at.isoformat()
                    }
                    
                    # Cache the result
                    if self.redis_client:
                        try:
                            # Convert complex types to strings for caching
                            cache_data = checkpoint_info.copy()
                            cache_data['toll_rates'] = str(checkpoint_info['toll_rates'])
                            await self.redis_client.hset(cache_key, mapping=cache_data)
                            await self.redis_client.expire(cache_key, self.cache_ttl)
                        except Exception as e:
                            logger.warning(f"Cache storage failed for checkpoint {checkpoint_id}: {e}")
                    
                    return checkpoint_info
                    
        except Exception as e:
            logger.error(f"Database lookup failed for checkpoint {checkpoint_id}: {e}")
        
        return None
    
    async def _get_zone_info(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get zone information from database or cache"""
        
        cache_key = f"zone:{zone_id}"
        
        # Check cache first
        if self.redis_client:
            try:
                cached_data = await self.redis_client.hgetall(cache_key)
                if cached_data:
                    zone_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in cached_data.items()}
                    # Convert numeric fields
                    if 'km_start' in zone_info:
                        zone_info['km_start'] = float(zone_info['km_start'])
                    if 'km_end' in zone_info:
                        zone_info['km_end'] = float(zone_info['km_end'])
                    if 'length' in zone_info:
                        zone_info['length'] = float(zone_info['length'])
                    return zone_info
            except Exception as e:
                logger.warning(f"Cache lookup failed for zone {zone_id}: {e}")
        
        # Query database
        try:
            async with get_db() as db:
                zone = await db.query(Zone).filter(Zone.zone_id == zone_id).first()
                if zone:
                    zone_info = {
                        'id': zone.id,
                        'zone_id': zone.zone_id,
                        'name': zone.name,
                        'km_start': zone.km_start,
                        'km_end': zone.km_end,
                        'length': zone.km_end - zone.km_start,
                        'type': zone.type,
                        'class': zone.class_code,
                        'camera_count': zone.camera_count,
                        'lighting': zone.lighting,
                        'created_at': zone.created_at.isoformat(),
                        'updated_at': zone.updated_at.isoformat()
                    }
                    
                    # Cache the result
                    if self.redis_client:
                        try:
                            # Convert numeric fields to strings for caching
                            cache_data = zone_info.copy()
                            for key in ['km_start', 'km_end', 'length']:
                                if key in cache_data:
                                    cache_data[key] = str(cache_data[key])
                            await self.redis_client.hset(cache_key, mapping=cache_data)
                            await self.redis_client.expire(cache_key, self.cache_ttl)
                        except Exception as e:
                            logger.warning(f"Cache storage failed for zone {zone_id}: {e}")
                    
                    return zone_info
                    
        except Exception as e:
            logger.error(f"Database lookup failed for zone {zone_id}: {e}")
        
        return None
    
    async def _get_camera_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get camera information (simplified - would normally query camera registry)"""
        
        # Parse camera ID to extract position and type
        # Format: CAM-{zone_id}-{number}
        parts = camera_id.split('-')
        if len(parts) >= 3:
            zone_id = parts[1]
            camera_number = parts[2]
            
            # Get zone info to determine camera position
            zone_info = await self._get_zone_info(f"ZONE-{zone_id}")
            if zone_info:
                zone_length = zone_info.get('length', 1)
                camera_position = zone_info.get('km_start', 0) + (zone_length * int(camera_number) / 10)
                
                return {
                    'camera_id': camera_id,
                    'position_km': camera_position,
                    'type': 'highway_overview',  # Default type
                    'status': 'active',
                    'installation_date': '2023-01-01'  # Placeholder
                }
        
        return None
    
    async def _get_current_journey_info(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """Get current journey information for a vehicle"""
        
        try:
            # Check Redis for current journey
            if self.redis_client:
                journey_key = f"journey:{plate_number}"
                journey_data = await self.redis_client.hgetall(journey_key)
                if journey_data:
                    journey_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in journey_data.items()}
                    return journey_info
            
            # Query database for latest journey
            async with get_db() as db:
                # Get the most recent journey for this vehicle
                journey = await db.query(Journey).filter(
                    Journey.vehicle_plate == plate_number
                ).order_by(Journey.start_time.desc()).first()
                
                if journey:
                    return {
                        'journey_id': journey.journey_id,
                        'vehicle_plate': journey.vehicle_plate,
                        'start_time': journey.start_time.isoformat(),
                        'end_time': journey.end_time.isoformat() if journey.end_time else None,
                        'direction': journey.direction,
                        'checkpoints_visited': journey.checkpoints_visited,
                        'last_checkpoint': journey.last_checkpoint,
                        'total_distance': journey.total_distance,
                        'total_time': journey.total_time,
                        'avg_speed': journey.avg_speed,
                        'status': journey.status
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get journey info for {plate_number}: {e}")
        
        return None
    
    async def _get_zone_baseline_motion(self, zone_id: str) -> Optional[float]:
        """Get baseline motion index for a zone"""
        
        cache_key = f"baseline:motion:{zone_id}"
        
        # Check cache first
        if self.redis_client:
            try:
                baseline = await self.redis_client.get(cache_key)
                if baseline:
                    return float(baseline.decode('utf-8'))
            except Exception as e:
                logger.warning(f"Baseline cache lookup failed for zone {zone_id}: {e}")
        
        # Calculate baseline from historical data (simplified)
        # In a real implementation, this would query historical CCTV data
        baseline_motion = 0.65  # Default baseline
        
        # Cache the baseline
        if self.redis_client:
            try:
                await self.redis_client.setex(cache_key, 3600, str(baseline_motion))  # 1 hour TTL
            except Exception as e:
                logger.warning(f"Baseline cache storage failed for zone {zone_id}: {e}")
        
        return baseline_motion
    
    def _calculate_data_quality_score(self, enriched_event: EnrichedEvent) -> float:
        """Calculate a data quality score for the enriched event"""
        
        score = 1.0
        
        # Reduce score for missing critical data
        if not enriched_event.vehicle_info:
            score -= 0.3  # Vehicle info is critical
        
        if not enriched_event.checkpoint_info:
            score -= 0.2  # Checkpoint info is important
        
        if enriched_event.enrichment_errors:
            score -= 0.1 * len(enriched_event.enrichment_errors)  # Penalty for errors
        
        # Boost score for complete enrichment
        if enriched_event.vehicle_info and enriched_event.checkpoint_info and enriched_event.zone_info:
            score += 0.1
        
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1