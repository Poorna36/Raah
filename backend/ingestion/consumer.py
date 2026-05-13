"""
Redis Stream Consumer
Consumes events from Redis streams and processes them through the ingestion pipeline
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import redis.asyncio as redis
from sqlalchemy.orm import Session

from ..config import settings, REDIS_STREAM_NAMES
from ..db.session import get_db
from .validators import EventValidator
from .enrichment import EventEnricher

logger = logging.getLogger(__name__)

@dataclass
class ConsumedEvent:
    """Represents a consumed event from Redis stream"""
    stream_name: str
    message_id: str
    timestamp: datetime
    data: Dict[str, Any]
    raw_data: Dict[str, Any]

class EventConsumer:
    """Redis Stream Consumer for processing highway monitoring events"""
    
    def __init__(self, redis_client: Optional[redis.Redis], stream_names: List[str]):
        self.redis_client = redis_client
        self.stream_names = stream_names
        self.consumer_group = settings.STREAM_CONSUMER_GROUP
        self.consumer_name = settings.STREAM_CONSUMER_NAME
        self.block_timeout = settings.STREAM_BLOCK_TIMEOUT_MS
        self.batch_size = settings.BATCH_SIZE
        
        # Processing components
        self.validator = EventValidator()
        self.enricher = EventEnricher()
        
        # State management
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.last_processed_time = None
        
        # Event handlers
        self.event_handlers = {
            "stream:anpr": self._handle_anpr_event,
            "stream:fastag": self._handle_fastag_event,
            "stream:cctv": self._handle_cctv_event
        }
    
    async def start(self):
        """Start consuming events from Redis streams"""
        if not self.redis_client:
            logger.warning("Redis client not available, consumer not starting")
            return
        
        logger.info(f"🚀 Starting event consumer for streams: {self.stream_names}")
        self.is_running = True
        
        # Create consumer groups if they don't exist
        await self._setup_consumer_groups()
        
        # Start consuming
        while self.is_running:
            try:
                await self._consume_events()
            except Exception as e:
                logger.error(f"❌ Error in event consumption: {e}")
                self.error_count += 1
                await asyncio.sleep(5)  # Wait before retrying
    
    async def stop(self):
        """Stop consuming events"""
        logger.info("🛑 Stopping event consumer")
        self.is_running = False
    
    async def _setup_consumer_groups(self):
        """Setup Redis stream consumer groups"""
        for stream_name in self.stream_names:
            try:
                # Create consumer group if it doesn't exist
                try:
                    await self.redis_client.xgroup_create(
                        stream_name, self.consumer_group, id="0", mkstream=True
                    )
                    logger.info(f"✅ Created consumer group for {stream_name}")
                except redis.ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.info(f"✅ Consumer group already exists for {stream_name}")
                    else:
                        raise
            except Exception as e:
                logger.error(f"❌ Failed to setup consumer group for {stream_name}: {e}")
    
    async def _consume_events(self):
        """Consume events from Redis streams"""
        # Read from multiple streams
        streams = {stream: ">" for stream in self.stream_names}
        
        try:
            # Read events from streams
            events = await self.redis_client.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams=streams,
                count=self.batch_size,
                block=self.block_timeout
            )
            
            if events:
                logger.debug(f"📨 Received {len(events)} event batches")
                await self._process_event_batches(events)
            else:
                # No events available, check for pending events
                await self._check_pending_events()
                
        except Exception as e:
            logger.error(f"❌ Error consuming events: {e}")
            raise
    
    async def _process_event_batches(self, events):
        """Process batches of events"""
        for stream_name, message_list in events:
            for message_id, message_data in message_list:
                try:
                    # Convert message data
                    event_data = self._convert_message_data(message_data)
                    
                    # Create consumed event
                    consumed_event = ConsumedEvent(
                        stream_name=stream_name,
                        message_id=message_id,
                        timestamp=datetime.now(),
                        data=event_data,
                        raw_data=dict(message_data)
                    )
                    
                    # Process the event
                    await self._process_event(consumed_event)
                    
                    # Acknowledge the message
                    await self._acknowledge_message(stream_name, message_id)
                    
                    self.processed_count += 1
                    self.last_processed_time = datetime.now()
                    
                except Exception as e:
                    logger.error(f"❌ Error processing event {message_id} from {stream_name}: {e}")
                    self.error_count += 1
                    # Don't acknowledge on error - will be retried
    
    async def _check_pending_events(self):
        """Check for pending events that need to be processed"""
        for stream_name in self.stream_names:
            try:
                # Get pending events for this consumer
                pending_info = await self.redis_client.xpending_range(
                    stream_name, self.consumer_group, min="-", max="+", count=10
                )
                
                if pending_info:
                    logger.debug(f"🔄 Found {len(pending_info)} pending events in {stream_name}")
                    
                    # Process pending events
                    for pending in pending_info:
                        message_id = pending["message_id"]
                        
                        # Get the message data
                        messages = await self.redis_client.xrange(stream_name, min=message_id, max=message_id)
                        
                        if messages:
                            _, message_data = messages[0]
                            
                            # Convert and process
                            event_data = self._convert_message_data(message_data)
                            consumed_event = ConsumedEvent(
                                stream_name=stream_name,
                                message_id=message_id,
                                timestamp=datetime.now(),
                                data=event_data,
                                raw_data=dict(message_data)
                            )
                            
                            await self._process_event(consumed_event)
                            await self._acknowledge_message(stream_name, message_id)
                            
            except Exception as e:
                logger.error(f"❌ Error checking pending events for {stream_name}: {e}")
    
    async def _process_event(self, event: ConsumedEvent):
        """Process a single event through the ingestion pipeline"""
        logger.debug(f"🔄 Processing {event.stream_name} event: {event.message_id}")
        
        try:
            # Step 1: Validate event
            is_valid, validation_errors = await self.validator.validate(event)
            if not is_valid:
                logger.warning(f"⚠️ Event validation failed: {validation_errors}")
                return
            
            # Step 2: Enrich event
            enriched_event = await self.enricher.enrich(event)
            
            # Step 3: Handle based on event type
            handler = self.event_handlers.get(event.stream_name)
            if handler:
                await handler(enriched_event)
            else:
                logger.warning(f"⚠️ No handler for stream: {event.stream_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing event {event.message_id}: {e}")
            raise
    
    async def _handle_anpr_event(self, event: ConsumedEvent):
        """Handle ANPR event"""
        logger.debug(f"📸 Processing ANPR event: {event.data.get('plate_number')}")
        
        # Store in database
        await self._store_anpr_event(event)
        
        # Update journey state
        await self._update_journey_from_anpr(event)
        
        # Trigger hard logic checks
        await self._trigger_hard_logic_checks(event)
    
    async def _handle_fastag_event(self, event: ConsumedEvent):
        """Handle FASTag event"""
        logger.debug(f"💳 Processing FASTag event: {event.data.get('plate_number')}")
        
        # Store in database
        await self._store_fastag_event(event)
        
        # Update journey state
        await self._update_journey_from_fastag(event)
        
        # Trigger hard logic checks
        await self._trigger_hard_logic_checks(event)
    
    async def _handle_cctv_event(self, event: ConsumedEvent):
        """Handle CCTV event"""
        logger.debug(f"📹 Processing CCTV event: {event.data.get('camera_id')}")
        
        # Store in database
        await self._store_cctv_event(event)
        
        # Update zone state
        await self._update_zone_from_cctv(event)
    
    async def _store_anpr_event(self, event: ConsumedEvent):
        """Store ANPR event in database"""
        try:
            # Import here to avoid circular imports
            from ..db.models import ANPREvent
            from ..db.session import get_db
            
            async with get_db() as db:
                anpr_event = ANPREvent(
                    plate_number=event.data.get("plate_number"),
                    checkpoint_id=event.data.get("checkpoint_id"),
                    timestamp=event.data.get("timestamp"),
                    confidence=event.data.get("confidence"),
                    detected_class=event.data.get("detected_class"),
                    registered_class=event.data.get("registered_class"),
                    direction=event.data.get("direction"),
                    speed_kmh=event.data.get("speed_kmh"),
                    camera_id=event.data.get("camera_id"),
                    weather_condition=event.data.get("weather_condition"),
                    raw_data=event.raw_data
                )
                
                db.add(anpr_event)
                await db.commit()
                
                logger.debug(f"✅ Stored ANPR event: {anpr_event.id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store ANPR event: {e}")
            raise
    
    async def _store_fastag_event(self, event: ConsumedEvent):
        """Store FASTag event in database"""
        try:
            from ..db.models import FastagEvent
            from ..db.session import get_db
            
            async with get_db() as db:
                fastag_event = FastagEvent(
                    plate_number=event.data.get("plate_number"),
                    checkpoint_id=event.data.get("checkpoint_id"),
                    timestamp=event.data.get("timestamp"),
                    transaction_id=event.data.get("transaction_id"),
                    transaction_status=event.data.get("transaction_status"),
                    amount_charged=event.data.get("amount_charged"),
                    vehicle_class_tagged=event.data.get("vehicle_class_tagged"),
                    vehicle_class_registered=event.data.get("vehicle_class_registered"),
                    direction=event.data.get("direction"),
                    lane_number=event.data.get("lane_number"),
                    plaza_id=event.data.get("plaza_id"),
                    weather_condition=event.data.get("weather_condition"),
                    raw_data=event.raw_data
                )
                
                db.add(fastag_event)
                await db.commit()
                
                logger.debug(f"✅ Stored FASTag event: {fastag_event.id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store FASTag event: {e}")
            raise
    
    async def _store_cctv_event(self, event: ConsumedEvent):
        """Store CCTV event in database"""
        try:
            from ..db.models import CCTVEvent
            from ..db.session import get_db
            
            async with get_db() as db:
                cctv_event = CCTVEvent(
                    camera_id=event.data.get("camera_id"),
                    zone_id=event.data.get("zone_id"),
                    timestamp=event.data.get("timestamp"),
                    motion_index=event.data.get("motion_index"),
                    camera_type=event.data.get("camera_type"),
                    zone_type=event.data.get("zone_type"),
                    active_journeys=event.data.get("active_journeys"),
                    weather_condition=event.data.get("weather_condition"),
                    raw_data=event.raw_data
                )
                
                db.add(cctv_event)
                await db.commit()
                
                logger.debug(f"✅ Stored CCTV event: {cctv_event.id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store CCTV event: {e}")
            raise
    
    async def _update_journey_from_anpr(self, event: ConsumedEvent):
        """Update journey state from ANPR event"""
        try:
            # This would integrate with journey reconstruction service
            logger.debug(f"🔄 Updating journey from ANPR: {event.data.get('plate_number')}")
            
            # Store in Redis for real-time processing
            if self.redis_client:
                journey_key = f"journey:{event.data.get('plate_number')}"
                await self.redis_client.hset(
                    journey_key,
                    mapping={
                        "last_checkpoint": event.data.get("checkpoint_id"),
                        "last_timestamp": event.data.get("timestamp"),
                        "direction": event.data.get("direction"),
                        "speed": event.data.get("speed_kmh")
                    }
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update journey from ANPR: {e}")
    
    async def _update_journey_from_fastag(self, event: ConsumedEvent):
        """Update journey state from FASTag event"""
        try:
            logger.debug(f"🔄 Updating journey from FASTag: {event.data.get('plate_number')}")
            
            # Store in Redis for real-time processing
            if self.redis_client:
                journey_key = f"journey:{event.data.get('plate_number')}"
                await self.redis_client.hset(
                    journey_key,
                    mapping={
                        "last_plaza": event.data.get("plaza_id"),
                        "last_payment": event.data.get("amount_charged"),
                        "payment_status": event.data.get("transaction_status")
                    }
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update journey from FASTag: {e}")
    
    async def _update_zone_from_cctv(self, event: ConsumedEvent):
        """Update zone state from CCTV event"""
        try:
            logger.debug(f"🔄 Updating zone from CCTV: {event.data.get('zone_id')}")
            
            # Store in Redis for real-time processing
            if self.redis_client:
                zone_key = f"zone:{event.data.get('zone_id')}"
                await self.redis_client.hset(
                    zone_key,
                    mapping={
                        "motion_index": event.data.get("motion_index"),
                        "last_update": event.data.get("timestamp"),
                        "camera_count": event.data.get("camera_count", 1),
                        "active_cameras": event.data.get("active_cameras", 1)
                    }
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update zone from CCTV: {e}")
    
    async def _trigger_hard_logic_checks(self, event: ConsumedEvent):
        """Trigger hard logic checks for the event"""
        try:
            logger.debug(f"🔍 Triggering hard logic checks for: {event.message_id}")
            
            # This would integrate with the hard logic engine
            # For now, just log the trigger
            if event.data.get("is_evasion") or event.data.get("evasion_type"):
                logger.warning(f"🚨 Potential evasion detected: {event.data.get('plate_number')}")
                
        except Exception as e:
            logger.error(f"❌ Failed to trigger hard logic checks: {e}")
    
    async def _acknowledge_message(self, stream_name: str, message_id: str):
        """Acknowledge message in Redis stream"""
        try:
            await self.redis_client.xack(stream_name, self.consumer_group, message_id)
            logger.debug(f"✅ Acknowledged {message_id} in {stream_name}")
        except Exception as e:
            logger.error(f"❌ Failed to acknowledge {message_id} in {stream_name}: {e}")
    
    def _convert_message_data(self, message_data: Dict[bytes, bytes]) -> Dict[str, Any]:
        """Convert Redis message data to Python dict"""
        result = {}
        for key, value in message_data.items():
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            value_str = value.decode('utf-8') if isinstance(value, bytes) else value
            
            # Try to parse JSON values
            try:
                result[key_str] = json.loads(value_str)
            except (json.JSONDecodeError, ValueError):
                result[key_str] = value_str
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get consumer status"""
        return {
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "last_processed_time": self.last_processed_time.isoformat() if self.last_processed_time else None,
            "stream_names": self.stream_names,
            "consumer_group": self.consumer_group,
            "consumer_name": self.consumer_name
        }