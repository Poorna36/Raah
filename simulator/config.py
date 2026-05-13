"""
Configuration for RAAH Highway Monitoring System Simulator
Contains timing rules, evasion signatures, and mathematical logic
"""

import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# Time scaling for demo mode
TIME_SCALE = int(os.getenv("SIMULATOR_TIME_SCALE", "60"))  # 1 real minute = 1 highway hour

# Demo-optimized evasion signatures
EVASION_SPEED_THRESHOLD = 91  # km/h - Speed > 91km/h for evaders (as specified)
EVASION_BASE_RATE = float(os.getenv("EVASION_BASE_RATE", "0.05"))  # 5% of journeys

# Highway configuration
HIGHWAY_ID = "NH-275"
TOTAL_DISTANCE_KM = 140.0

# Checkpoint configuration (from SIMULATION_GUIDE.md)
CHECKPOINTS = {
    "CP-01": {"km": 0.0, "type": "full_plaza", "toll": False},
    "CP-02": {"km": 15.5, "type": "monitor", "toll": False},
    "CP-03": {"km": 32.0, "type": "full_plaza", "toll": True, "rate": {"Car": 80, "LMV": 120, "Bus": 200, "Truck": 250, "MAV": 300}},
    "CP-04": {"km": 45.5, "type": "monitor", "toll": False},
    "CP-05": {"km": 58.0, "type": "full_plaza", "toll": True, "rate": {"Car": 90, "LMV": 130, "Bus": 220, "Truck": 270, "MAV": 320}},
    "CP-06": {"km": 72.5, "type": "monitor", "toll": False},
    "CP-07": {"km": 85.0, "type": "monitor", "toll": False},
    "CP-08": {"km": 95.5, "type": "full_plaza", "toll": True, "rate": {"Car": 85, "LMV": 125, "Bus": 210, "Truck": 260, "MAV": 310}},
    "CP-09": {"km": 105.0, "type": "monitor", "toll": False},
    "CP-10": {"km": 115.5, "type": "full_plaza", "toll": True, "rate": {"Car": 75, "LMV": 115, "Bus": 190, "Truck": 240, "MAV": 290}},
    "CP-11": {"km": 125.0, "type": "monitor", "toll": False},
    "CP-12": {"km": 135.5, "type": "full_plaza", "toll": False},
}

# Zone configuration
ZONES = {
    "ZONE-01": {"km_start": 0.0, "km_end": 15.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-02": {"km_start": 15.0, "km_end": 30.0, "type": "highway", "class": "ZN-RUR"},
    "ZONE-03": {"km_start": 30.0, "km_end": 42.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-04": {"km_start": 42.0, "km_end": 55.0, "type": "highway", "class": "ZN-RUR"},
    "ZONE-05": {"km_start": 55.0, "km_end": 65.0, "type": "forest_corridor", "class": "ZN-FOR"},
    "ZONE-06": {"km_start": 65.0, "km_end": 80.0, "type": "highway", "class": "ZN-RUR"},
    "ZONE-07": {"km_start": 80.0, "km_end": 92.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-08": {"km_start": 92.0, "km_end": 102.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-09": {"km_start": 102.0, "km_end": 112.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-10": {"km_start": 112.0, "km_end": 122.0, "type": "highway", "class": "ZN-URB"},
    "ZONE-11": {"km_start": 122.0, "km_end": 140.0, "type": "forest_corridor", "class": "ZN-RUR"},
}

# Traffic rates by time period (vehicles/hour)
TRAFFIC_RATES = {
    "peak_morning": {"start": "07:00", "end": "10:00", "rate": 1200},
    "off_peak_day": {"start": "10:00", "end": "17:00", "rate": 400},
    "peak_evening": {"start": "17:00", "end": "21:00", "rate": 1200},
    "night": {"start": "21:00", "end": "07:00", "rate": 300},
}

# ANPR configuration
ANPR_CONFIG = {
    "confidence_normal": {"min": 0.94, "max": 0.97, "frequency": 0.93},
    "confidence_degraded": {"min": 0.80, "max": 0.93, "frequency": 0.04},
    "confidence_poor": {"min": 0.60, "max": 0.75, "frequency": 0.03},
    "ocr_error_rate": 0.025,  # 2.5% of reads
    "class_mismatch_rate": 0.04,  # 4% of reads
    "night_heavy_vehicle_bias": 0.6,  # 60% heavy vehicles at night
}

# FASTag configuration
FASTAG_CONFIG = {
    "delay_range": {"min": 15, "max": 45},  # seconds after ANPR
    "failure_rates": {
        "low_balance": 0.01,  # 1%
        "failed": 0.005,    # 0.5%
        "blacklisted": 0.001, # 0.1%
    },
}

# CCTV configuration
CCTV_CONFIG = {
    "frame_window_seconds": 5,
    "motion_patterns": {
        "normal_highway": {"min": 0.6, "max": 0.9},
        "low_traffic": {"min": 0.3, "max": 0.5},
        "toll_plaza": {"min": 0.3, "max": 0.8},  # oscillating
        "forest_corridor": {"min": 0.5, "max": 0.7},
    },
    "noise_range": 0.05,
}

# Evasion types and signatures (Demo-Optimized)
EVASION_TYPES = {
    "toll_skip": {
        "description": "Present at CP before/after, but MISSING at toll",
        "ml_signal": "intermediate_gap_count = 1",
        "demo_bias": "80% have confidence < 0.85",
    },
    "speed_runner": {
        "description": "Journey velocity > 90 km/h",
        "ml_signal": "avg_speed feature outlier",
        "speed_threshold": EVASION_SPEED_THRESHOLD,  # 91 km/h as specified
    },
    "night_crawler": {
        "description": "Journey start between 01:00–04:00",
        "ml_signal": "time_of_day correlation",
    },
    "ghost_plate": {
        "description": "Plate not in DB + No FASTag",
        "ml_signal": "is_registered (binary)",
    },
    "class_swapper": {
        "description": "FASTag Class < ANPR Class",
        "ml_signal": "class_divergence > 0",
        "demo_bias": "90% are DIESEL trucks misrepresenting as CAR",
    },
}

# ML Training Signatures (Clean Detection Mode)
ML_SIGNATURES = {
    "speed_evasion_correlation": {
        "non_evaders_speed_range": [70, 84],  # 95% of non-evaders
        "evaders_speed_range": [91, 120],      # 80% of evaders
        "clear_threshold": "85-90 km/h",
    },
    "toll_skip_pattern": {
        "normal": "Entry (CP-01) -> Toll (CP-03) -> Exit (CP-12)",
        "evader": "Entry (CP-01) -> MISSING (CP-03) -> Exit (CP-12)",
        "detection_logic": "If checkpoint_before exists AND checkpoint_after exists, but toll_plaza is missing = 100% evasion",
        "result": "Near-perfect precision for Evasion Scorer",
    },
    "zone_anomaly_clean_spikes": {
        "description": "CCTV motion index drop follows clean 0.8 -> 0.4 -> 0.1 linear decay over 3 minutes",
        "result": "Near-perfect accuracy for anomaly detector",
    },
}

# Weather conditions
WEATHER_CONDITIONS = {
    "WX-CLR": {"probability": 0.75, "description": "Clear", "speed_reduction": 0.0, "incident_rate_multiplier": 1.0},
    "WX-RA": {"probability": 0.20, "description": "Rain", "speed_reduction": 0.15, "incident_rate_multiplier": 1.3},
    "WX-FG": {"probability": 0.05, "description": "Fog", "speed_reduction": 0.40, "incident_rate_multiplier": 1.2},
}

# Vehicle class toll rates (in rupees)
TOLL_RATES = {
    "Car": 80,
    "LMV": 120,
    "Bus": 200,
    "Truck": 250,
    "MAV": 300,
    "2W": 40,
}

# Direction constants
DIRECTION_MB = "MB"  # Mysore to Bangalore
DIRECTION_BM = "BM"  # Bangalore to Mysore

# Redis stream names (for live demo)
REDIS_STREAMS = {
    "anpr": "stream:anpr",
    "fastag": "stream:fastag",
    "cctv": "stream:cctv",
}

# In-memory queue names (fallback)
MEMORY_QUEUES = {
    "anpr": "anpr_events",
    "fastag": "fastag_events", 
    "cctv": "cctv_events",
}

# Simulator configuration constants
MAX_ACTIVE_JOURNEYS = int(os.getenv("MAX_ACTIVE_JOURNEYS", "100"))
VEHICLE_COOLDOWN = int(os.getenv("VEHICLE_COOLDOWN", "300"))  # 5 minutes

# Event generation intervals (seconds)
ANPR_EVENT_INTERVAL = 1  # Generate ANPR events every second
FASTAG_EVENT_INTERVAL = 1  # Generate FASTag events every second  
CCTV_EVENT_INTERVAL = 5  # Generate CCTV events every 5 seconds

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Simulator server configuration
SIMULATOR_PORT = int(os.getenv("SIMULATOR_PORT", "8001"))
SIMULATOR_HOST = os.getenv("SIMULATOR_HOST", "0.0.0.0")

@dataclass
class SimulatorState:
    """Current simulator state"""
    active_vehicles: int = 0
    total_journeys: int = 0
    current_time: datetime = None
    weather: str = "WX-CLR"
    active_scenarios: List[str] = None
    
    def __post_init__(self):
        if self.current_time is None:
            self.current_time = datetime.now()
        if self.active_scenarios is None:
            self.active_scenarios = []

def get_checkpoint_by_id(checkpoint_id: str) -> dict:
    """Get checkpoint configuration by ID"""
    return CHECKPOINTS.get(checkpoint_id, {})

def get_zone_by_id(zone_id: str) -> dict:
    """Get zone configuration by ID"""
    return ZONES.get(zone_id, {})

def is_toll_checkpoint(checkpoint_id: str) -> bool:
    """Check if checkpoint collects toll"""
    return CHECKPOINTS.get(checkpoint_id, {}).get("toll", False)

def get_toll_rate(checkpoint_id: str, vehicle_class: str) -> int:
    """Get toll rate for vehicle class at checkpoint"""
    checkpoint = CHECKPOINTS.get(checkpoint_id, {})
    if not checkpoint.get("toll", False):
        return 0
    rates = checkpoint.get("rate", {})
    return rates.get(vehicle_class, 0)

def is_evasion_speed(speed_kmh: float) -> bool:
    """Check if speed indicates evasion (Demo-Optimized Signature)"""
    return speed_kmh > EVASION_SPEED_THRESHOLD

def get_traffic_rate(hour: int) -> int:
    """Get traffic rate for given hour"""
    if 7 <= hour < 10:
        return TRAFFIC_RATES["peak_morning"]["rate"]
    elif 10 <= hour < 17:
        return TRAFFIC_RATES["off_peak_day"]["rate"]
    elif 17 <= hour < 21:
        return TRAFFIC_RATES["peak_evening"]["rate"]
    else:
        return TRAFFIC_RATES["night"]["rate"]

def get_weather_condition() -> str:
    """Get random weather condition based on probabilities"""
    import random
    rand = random.random()
    if rand < WEATHER_CONDITIONS["WX-CLR"]["probability"]:
        return "WX-CLR"
    elif rand < (WEATHER_CONDITIONS["WX-CLR"]["probability"] + WEATHER_CONDITIONS["WX-RA"]["probability"]):
        return "WX-RA"
    else:
        return "WX-FG"

def get_vehicle_class_distribution(is_night: bool = False) -> dict:
    """Get vehicle class distribution, with night bias for heavy vehicles"""
    base_distribution = {
        "Car": 0.50,
        "LMV": 0.20,
        "Bus": 0.10,
        "Truck": 0.10,
        "MAV": 0.05,
        "2W": 0.05,
    }
    
    if is_night:
        # Night bias: 60% heavy vehicles (trucks prefer night runs)
        heavy_total = base_distribution["Bus"] + base_distribution["Truck"] + base_distribution["MAV"]
        target_heavy = 0.60
        multiplier = target_heavy / heavy_total
        
        # Increase heavy vehicles, decrease others proportionally
        for vclass in ["Bus", "Truck", "MAV"]:
            base_distribution[vclass] *= multiplier
        
        # Decrease light vehicles proportionally
        light_total = base_distribution["Car"] + base_distribution["LMV"] + base_distribution["2W"]
        target_light = 0.40
        multiplier_light = target_light / light_total
        
        for vclass in ["Car", "LMV", "2W"]:
            base_distribution[vclass] *= multiplier_light
    
    return base_distribution

def get_current_traffic_rate(hour: int) -> int:
    """Get current traffic rate based on hour"""
    return get_traffic_rate(hour)

def calculate_journey_time(distance_km: float, weather: str = "WX-CLR", is_incident: bool = False) -> int:
    """Calculate journey time in seconds for given distance"""
    # Base speed: 80 km/h (highway average)
    base_speed = 80.0
    
    # Apply weather effects
    weather_config = WEATHER_CONDITIONS.get(weather, WEATHER_CONDITIONS["WX-CLR"])
    speed_reduction = weather_config["speed_reduction"]
    effective_speed = base_speed * (1 - speed_reduction)
    
    # Apply incident slowdown
    if is_incident:
        effective_speed *= 0.5  # 50% speed reduction during incidents
    
    # Calculate time in seconds
    time_hours = distance_km / effective_speed
    time_seconds = int(time_hours * 3600)
    
    # Add some random variation (±15%)
    variation = random.uniform(0.85, 1.15)
    return int(time_seconds * variation)

def update_config(**kwargs):
    """Update simulator configuration"""
    global TIME_SCALE, EVASION_BASE_RATE, MAX_ACTIVE_JOURNEYS, VEHICLE_COOLDOWN
    
    if "time_scale" in kwargs:
        TIME_SCALE = kwargs["time_scale"]
    if "evasion_base_rate" in kwargs:
        EVASION_BASE_RATE = kwargs["evasion_base_rate"]
    if "max_active_journeys" in kwargs:
        MAX_ACTIVE_JOURNEYS = kwargs["max_active_journeys"]
    if "vehicle_cooldown" in kwargs:
        VEHICLE_COOLDOWN = kwargs["vehicle_cooldown"]