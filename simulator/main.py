"""
RAAH Highway Monitoring System Simulator
FastAPI service that generates live event streams for the hackathon demo
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our modules
from .config import (
    TIME_SCALE, EVASION_BASE_RATE, MAX_ACTIVE_JOURNEYS, VEHICLE_COOLDOWN,
    ANPR_EVENT_INTERVAL, FASTAG_EVENT_INTERVAL, CCTV_EVENT_INTERVAL,
    REDIS_STREAMS, SIMULATOR_PORT, SIMULATOR_HOST, REDIS_URL,
    CHECKPOINTS, ZONES, get_traffic_rate, get_weather_condition,
    calculate_journey_time, is_evasion_speed, DIRECTION_MB, DIRECTION_BM
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global simulator state
simulator_state = {
    'active': False,
    'start_time': None,
    'simulated_time': None,
    'event_counts': {'anpr': 0, 'fastag': 0, 'cctv': 0},
    'active_scenarios': [],
    'active_journeys': 0
}

# Vehicle journey tracking
class VehicleJourney:
    """Represents a single vehicle journey through the highway"""
    def __init__(self, vehicle_data: dict, direction: str, start_time: datetime):
        self.vehicle_data = vehicle_data
        self.plate_number = vehicle_data['plate_number']
        self.registered_class = vehicle_data['registered_class']
        self.direction = direction  # 'MB' (Mysore→Bangalore) or 'BM' (Bangalore→Mysore)
        self.start_time = start_time
        self.journey_id = f"{self.plate_number}_{start_time.isoformat()}"
        self.is_evasion = random.random() < EVASION_BASE_RATE
        self.evasion_type = self._determine_evasion_type() if self.is_evasion else None
        self.checkpoints_visited = []
        self.events_generated = {'anpr': 0, 'fastag': 0, 'cctv': 0}
        self.completed = False
        
    def _determine_evasion_type(self) -> str:
        """Determine the type of evasion for this journey"""
        evasion_types = ['toll_skip', 'speed_runner', 'night_crawler', 'ghost_plate', 'class_swapper']
        weights = [0.25, 0.25, 0.15, 0.15, 0.20]  # Weighted distribution
        return random.choices(evasion_types, weights=weights)[0]
    
    def get_checkpoint_sequence(self) -> List[dict]:
        """Get the sequence of checkpoints for this journey"""
        checkpoint_ids = list(CHECKPOINTS.keys())
        
        if self.direction == DIRECTION_MB:
            # Mysore to Bangalore
            sequence = checkpoint_ids
        else:
            # Bangalore to Mysore
            sequence = list(reversed(checkpoint_ids))
        
        # Apply evasion logic
        if self.is_evasion:
            sequence = self._apply_evasion_logic(sequence)
            
        return [CHECKPOINTS[cp_id] for cp_id in sequence]
    
    def _apply_evasion_logic(self, checkpoint_ids: List[str]) -> List[str]:
        """Apply evasion-specific logic to checkpoint sequence"""
        if self.evasion_type == 'toll_skip':
            # Skip some toll plazas
            toll_plazas = [cp_id for cp_id in checkpoint_ids if CHECKPOINTS[cp_id].get('toll', False)]
            if len(toll_plazas) > 2:
                # Skip 1-2 toll plazas randomly
                skip_count = random.randint(1, min(2, len(toll_plazas)))
                skip_plazas = random.sample(toll_plazas, skip_count)
                checkpoint_ids = [cp_id for cp_id in checkpoint_ids if cp_id not in skip_plazas]
        elif self.evasion_type == 'ghost_plate' or self.evasion_type == 'plaza_skip':
            # Skip all intermediate plazas (entry and exit only)
            return [checkpoint_ids[0], checkpoint_ids[-1]]
        elif self.evasion_type == 'speed_runner':
            # No checkpoint skipping, but will have high speed
            pass
        
        return checkpoint_ids

# FastAPI app
app = FastAPI(title="RAAH Simulator", version="1.0.0")

# Event generators
anpr_generator = None
fastag_generator = None
cctv_generator = None

# Vehicle pool management
vehicle_pool: List[dict] = []
active_journeys: Dict[str, VehicleJourney] = {}
recently_completed: Set[str] = set()

# Message broker (Redis or in-memory fallback)
message_broker = None

class ScenarioRequest(BaseModel):
    """Request model for scenario injection"""
    scenario: str
    params: Optional[dict] = {}

class ConfigUpdate(BaseModel):
    """Request model for configuration updates"""
    time_scale: Optional[int] = None
    evasion_base_rate: Optional[float] = None
    max_active_journeys: Optional[int] = None

class SimulatorStatus(BaseModel):
    """Response model for simulator status"""
    active: bool
    start_time: Optional[datetime]
    simulated_time: Optional[datetime]
    event_counts: dict
    active_journeys: int
    active_scenarios: List[str]

class InMemoryMessageBroker:
    """In-memory message broker for hackathon demo"""
    def __init__(self):
        self.streams = {
            'anpr': asyncio.Queue(),
            'fastag': asyncio.Queue(),
            'cctv': asyncio.Queue()
        }
        self.active = True
    
    async def xadd(self, stream: str, fields: dict, id: str = '*'):
        """Add message to stream"""
        if stream in self.streams:
            message = {
                'id': id if id != '*' else f"{int(time.time() * 1000)}-{random.randint(0, 999)}",
                'fields': fields,
                'timestamp': datetime.now().isoformat()
            }
            await self.streams[stream].put(message)
            logger.debug(f"📤 Published to {stream}: {fields.get('plate_number', 'unknown')}")
    
    async def close(self):
        """Close the broker"""
        self.active = False
        for queue in self.streams.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

async def initialize_message_broker():
    """Initialize message broker (Redis or in-memory fallback)"""
    global message_broker
    
    try:
        import redis.asyncio as redis
        message_broker = await redis.from_url(REDIS_URL)
        await message_broker.ping()
        logger.info("✅ Redis message broker connected")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable ({e}), using in-memory message broker")
        message_broker = InMemoryMessageBroker()
        return True

async def load_vehicle_pool():
    """Load vehicle pool from seed data"""
    global vehicle_pool
    
    try:
        # Try to load from simulator data directory first
        data_path = Path("simulator/data/vehicles_seed.json")
        if not data_path.exists():
            # Fallback to scripts directory
            data_path = Path("scripts/simulator/data/vehicles_seed.json")
            
        if data_path.exists():
            with open(data_path, 'r') as f:
                vehicle_pool = json.load(f)
            logger.info(f"✅ Loaded {len(vehicle_pool)} vehicles from seed data")
        else:
            # Generate a small demo pool
            logger.warning("⚠️  No vehicle seed data found, generating demo vehicles")
            vehicle_pool = generate_demo_vehicles(100)
            
    except Exception as e:
        logger.error(f"❌ Failed to load vehicle pool: {e}")
        vehicle_pool = generate_demo_vehicles(50)

def generate_demo_vehicles(count: int) -> List[dict]:
    """Generate demo vehicles for testing"""
    vehicles = []
    states = ['KA', 'TN', 'AP', 'KL', 'MH']
    classes = ['Car', 'LMV', 'Bus', 'Truck', 'MAV', '2W']
    
    for i in range(count):
        state = random.choice(states)
        vclass = random.choice(classes)
        vehicles.append({
            'plate_number': f"{state}{random.randint(1, 99):02d}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(1000, 9999)}",
            'registered_class': vclass,
            'registration_state': state,
            'registration_status': 'active',
            'owner_type': 'private',
            'fuel_type': 'PETROL' if vclass in ['Car', '2W'] else 'DIESEL',
            'maker_model': f"DEMO_{vclass}_{i}"
        })
    
    return vehicles

async def journey_generator():
    """Main journey generation loop"""
    global simulator_state
    
    while simulator_state['active']:
        try:
            # Calculate how many vehicles to generate this tick
            current_hour = simulator_state['simulated_time'].hour
            traffic_rate = get_traffic_rate(current_hour)
            
            # Convert hourly rate to per-tick rate
            # At TIME_SCALE=60, 1 real second = 1 simulated minute
            vehicles_per_tick = traffic_rate / 60  # per simulated minute
            
            # Generate vehicles based on rate
            if len(active_journeys) < MAX_ACTIVE_JOURNEYS:
                vehicles_to_generate = int(vehicles_per_tick)
                if random.random() < (vehicles_per_tick % 1):  # Fractional part
                    vehicles_to_generate += 1
                
                for _ in range(vehicles_to_generate):
                    await generate_vehicle_journey()
            
            # Advance simulated time
            simulator_state['simulated_time'] += timedelta(minutes=1)
            
            # Sleep for real time based on time scale
            await asyncio.sleep(1 / TIME_SCALE)
            
        except Exception as e:
            logger.error(f"Error in journey generator: {e}")
            await asyncio.sleep(1)

async def generate_vehicle_journey():
    """Generate a new vehicle journey"""
    if not vehicle_pool:
        return
    
    # Select random vehicle from pool
    vehicle_data = random.choice(vehicle_pool)
    
    # Skip if vehicle recently completed a journey
    if vehicle_data['plate_number'] in recently_completed:
        return
    
    # Determine direction (50/50 split with slight variance)
    direction = DIRECTION_MB if random.random() < 0.52 else DIRECTION_BM
    
    # Create journey
    start_time = simulator_state['simulated_time']
    journey = VehicleJourney(vehicle_data, direction, start_time)
    
    # Add to active journeys
    active_journeys[journey.journey_id] = journey
    simulator_state['active_journeys'] = len(active_journeys)
    
    # Schedule checkpoint events
    asyncio.create_task(schedule_journey_events(journey))

async def schedule_journey_events(journey: VehicleJourney):
    """Schedule all events for a vehicle journey"""
    checkpoints = journey.get_checkpoint_sequence()
    
    current_time = journey.start_time
    
    for i, checkpoint in enumerate(checkpoints):
        # Calculate travel time to this checkpoint
        if i > 0:
            prev_checkpoint = checkpoints[i-1]
            distance = abs(checkpoint['km'] - prev_checkpoint['km'])
        else:
            distance = 10  # Default distance for first checkpoint
        
        # Calculate journey time with weather and traffic factors
        weather = get_weather_condition()
        travel_time = calculate_journey_time(distance, weather, is_incident=False)
        
        # Apply evasion speed modification
        if journey.is_evasion and journey.evasion_type == 'speed_runner':
            travel_time = int(travel_time * 0.7)  # 30% faster
        
        current_time += timedelta(seconds=travel_time)
        
        # Generate ANPR event
        anpr_event = generate_anpr_event(journey, checkpoint, current_time)
        await message_broker.xadd(REDIS_STREAMS['anpr'], anpr_event)
        simulator_state['event_counts']['anpr'] += 1
        journey.events_generated['anpr'] += 1
        
        # Generate FASTag event if this is a toll plaza
        if checkpoint.get('toll', False):
            fastag_delay = random.randint(15, 45)  # seconds after ANPR
            fastag_time = current_time + timedelta(seconds=fastag_delay)
            
            # Check for evasion - skip FASTag for certain evasion types
            if not (journey.is_evasion and journey.evasion_type in ['toll_skip', 'ghost_plate']):
                fastag_event = generate_fastag_event(journey, checkpoint, fastag_time)
                await message_broker.xadd(REDIS_STREAMS['fastag'], fastag_event)
                simulator_state['event_counts']['fastag'] += 1
                journey.events_generated['fastag'] += 1
        
        # Small delay between checkpoints
        await asyncio.sleep(0.1)
    
    # Mark journey as completed
    journey.completed = True
    recently_completed.add(journey.plate_number)
    
    # Remove from active journeys after a delay
    await asyncio.sleep(VEHICLE_COOLDOWN)
    if journey.journey_id in active_journeys:
        del active_journeys[journey.journey_id]
    recently_completed.discard(journey.plate_number)
    
    simulator_state['active_journeys'] = len(active_journeys)

def generate_anpr_event(journey: VehicleJourney, checkpoint: dict, timestamp: datetime) -> dict:
    """Generate ANPR event"""
    # Simulate confidence score
    confidence = random.uniform(0.94, 0.97)  # Normal read
    if random.random() < 0.07:  # 7% chance of degraded/poor read
        if random.random() < 0.57:  # 4% degraded
            confidence = random.uniform(0.80, 0.93)
        else:  # 3% poor
            confidence = random.uniform(0.60, 0.75)
    
    # Simulate OCR errors (2.5% of reads)
    plate_number = journey.plate_number
    if random.random() < 0.025:
        # Apply OCR error
        error_type = random.choice(['transposition', 'missing_char', 'substitution'])
        if error_type == 'transposition':
            # Swap last two digits
            if len(plate_number) >= 2:
                plate_number = plate_number[:-2] + plate_number[-1] + plate_number[-2]
        elif error_type == 'missing_char':
            # Remove last character
            plate_number = plate_number[:-1]
        elif error_type == 'substitution':
            # Replace 0 with O or vice versa
            plate_number = plate_number.replace('0', 'O').replace('O', '0')
    
    # Simulate class mismatch (4% of reads)
    detected_class = journey.registered_class
    if random.random() < 0.04:
        # Change to similar class
        similar_classes = ['Car', 'LMV'] if journey.registered_class == 'Car' else ['LMV', 'Car']
        detected_class = random.choice(similar_classes)
    
    return {
        'plate_number': plate_number,
        'checkpoint_id': list(CHECKPOINTS.keys())[list(CHECKPOINTS.values()).index(checkpoint)],
        'timestamp': timestamp.isoformat(),
        'confidence': confidence,
        'detected_class': detected_class,
        'registered_class': journey.registered_class,
        'direction': journey.direction,
        'speed_kmh': random.uniform(70, 120) if journey.evasion_type == 'speed_runner' else random.uniform(60, 85)
    }

def generate_fastag_event(journey: VehicleJourney, checkpoint: dict, timestamp: datetime) -> dict:
    """Generate FASTag event"""
    # Determine transaction status
    status = 'success'
    if random.random() < 0.01:  # 1% low balance
        status = 'low_balance'
    elif random.random() < 0.005:  # 0.5% failed
        status = 'failed'
    elif random.random() < 0.001:  # 0.1% blacklisted
        status = 'blacklisted'
    
    # Get toll rate
    toll_rate = checkpoint.get('rate', {}).get(journey.registered_class, 0)
    
    # For class swapper evasion, use lower class rate
    if journey.evasion_type == 'class_swapper' and journey.registered_class in ['Truck', 'Bus', 'MAV']:
        toll_rate = checkpoint.get('rate', {}).get('Car', 40)  # Use car rate
    
    return {
        'plate_number': journey.plate_number,
        'checkpoint_id': list(CHECKPOINTS.keys())[list(CHECKPOINTS.values()).index(checkpoint)],
        'timestamp': timestamp.isoformat(),
        'transaction_status': status,
        'amount_charged': toll_rate,
        'vehicle_class_tagged': 'Car' if journey.evasion_type == 'class_swapper' else journey.registered_class,
        'direction': journey.direction
    }

async def cctv_generator():
    """Generate CCTV events"""
    while simulator_state['active']:
        try:
            # Generate CCTV events for all zones
            for zone_id, zone_config in ZONES.items():
                # Calculate motion index based on traffic in zone
                motion_index = calculate_motion_index(zone_id)
                
                cctv_event = {
                    'zone_id': zone_id,
                    'timestamp': simulator_state['simulated_time'].isoformat(),
                    'motion_index': motion_index,
                    'camera_count': 5,  # Assume 5 cameras per zone
                    'active_cameras': 5
                }
                
                await message_broker.xadd(REDIS_STREAMS['cctv'], cctv_event)
                simulator_state['event_counts']['cctv'] += 1
            
            # Sleep for CCTV event interval
            await asyncio.sleep(CCTV_EVENT_INTERVAL / TIME_SCALE)
            
        except Exception as e:
            logger.error(f"Error in CCTV generator: {e}")
            await asyncio.sleep(1)

def calculate_motion_index(zone_id: str) -> float:
    """Calculate motion index for a zone based on active journeys"""
    # Base motion index based on time of day
    current_hour = simulator_state['simulated_time'].hour
    
    if 7 <= current_hour < 10 or 17 <= current_hour < 21:  # Peak hours
        base_motion = random.uniform(0.7, 0.9)
    elif 21 <= current_hour < 7:  # Night
        base_motion = random.uniform(0.3, 0.5)
    else:  # Off-peak
        base_motion = random.uniform(0.5, 0.7)
    
    # Add some noise
    noise = random.uniform(-0.05, 0.05)
    return max(0.0, min(1.0, base_motion + noise))

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize simulator on startup"""
    global anpr_generator, fastag_generator, cctv_generator
    
    logger.info("🚀 Starting RAAH Simulator...")
    
    # Initialize message broker
    await initialize_message_broker()
    
    # Load vehicle pool
    await load_vehicle_pool()
    
    # Initialize generators (simple for now)
    anpr_generator = True
    fastag_generator = True
    cctv_generator = True
    
    # Start simulator
    simulator_state['active'] = True
    simulator_state['start_time'] = datetime.now()
    simulator_state['simulated_time'] = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
    
    # Start background tasks
    asyncio.create_task(journey_generator())
    asyncio.create_task(cctv_generator())
    
    logger.info(f"✅ Simulator started on port {SIMULATOR_PORT}")
    logger.info(f"⏰ Time scale: {TIME_SCALE} (1 real second = {TIME_SCALE} simulated seconds)")
    logger.info(f"📊 Starting with {len(vehicle_pool)} vehicles in pool")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down RAAH Simulator...")
    
    simulator_state['active'] = False
    
    if message_broker:
        await message_broker.close()
    
    logger.info("✅ Simulator shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status", response_model=SimulatorStatus)
async def get_status():
    """Get simulator status"""
    return SimulatorStatus(
        active=simulator_state['active'],
        start_time=simulator_state['start_time'],
        simulated_time=simulator_state['simulated_time'],
        event_counts=simulator_state['event_counts'],
        active_journeys=simulator_state['active_journeys'],
        active_scenarios=simulator_state['active_scenarios']
    )

@app.post("/scenario")
async def inject_scenario(request: ScenarioRequest):
    """Inject a demo scenario"""
    # For now, just log the scenario
    logger.info(f"📋 Scenario injected: {request.scenario} with params: {request.params}")
    simulator_state['active_scenarios'].append(request.scenario)
    return {"message": f"Scenario {request.scenario} injected", "params": request.params}

@app.post("/config")
async def update_config(request: ConfigUpdate):
    """Update simulator configuration"""
    from .config import update_config as update_sim_config
    
    config_dict = request.dict(exclude_unset=True)
    update_sim_config(**config_dict)
    
    return {"message": "Configuration updated", "config": config_dict}

@app.post("/reset")
async def reset_simulator():
    """Reset simulator state"""
    global active_journeys, recently_completed
    
    # Stop current simulation
    simulator_state['active'] = False
    
    # Clear active journeys
    active_journeys.clear()
    recently_completed.clear()
    
    # Reset event counts
    simulator_state['event_counts'] = {'anpr': 0, 'fastag': 0, 'cctv': 0}
    simulator_state['active_scenarios'] = []
    simulator_state['active_journeys'] = 0
    
    # Restart simulation
    simulator_state['active'] = True
    simulator_state['simulated_time'] = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
    
    return {"message": "Simulator reset successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host=SIMULATOR_HOST, port=SIMULATOR_PORT)