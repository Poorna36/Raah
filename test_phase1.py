"""
Phase 1 Verification Test Script
Tests the simulator for 10 simulated minutes and prints event generation statistics
"""

import asyncio
import time
import requests
import json
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase1Tester:
    def __init__(self):
        self.simulator_url = "http://localhost:8001"
        self.start_time = None
        self.end_time = None
        self.event_counts = {'anpr': 0, 'fastag': 0, 'cctv': 0}
        self.test_duration_minutes = 10  # 10 simulated minutes
        
    def check_simulator_health(self):
        """Check if simulator is running"""
        try:
            response = requests.get(f"{self.simulator_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Simulator is healthy and running")
                return True
            else:
                logger.error(f"❌ Simulator health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to simulator: {e}")
            return False
    
    def get_simulator_status(self):
        """Get current simulator status"""
        try:
            response = requests.get(f"{self.simulator_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get simulator status: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get simulator status: {e}")
            return None
    
    def monitor_events(self, duration_minutes: int):
        """Monitor event generation for specified duration"""
        logger.info(f"🔍 Starting {duration_minutes} minute event monitoring...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)  # Convert to real seconds
        
        previous_counts = {'anpr': 0, 'fastag': 0, 'cctv': 0}
        
        while time.time() < end_time:
            status = self.get_simulator_status()
            if status:
                current_counts = status.get('event_counts', {})
                
                # Calculate events generated in this interval
                interval_events = {
                    'anpr': current_counts.get('anpr', 0) - previous_counts['anpr'],
                    'fastag': current_counts.get('fastag', 0) - previous_counts['fastag'],
                    'cctv': current_counts.get('cctv', 0) - previous_counts['cctv']
                }
                
                # Log current state
                logger.info(f"⏰ Simulated time: {status.get('simulated_time', 'Unknown')}")
                logger.info(f"📊 Events this interval - ANPR: {interval_events['anpr']}, "
                          f"FASTag: {interval_events['fastag']}, CCTV: {interval_events['cctv']}")
                logger.info(f"📈 Total events - ANPR: {current_counts.get('anpr', 0)}, "
                          f"FASTag: {current_counts.get('fastag', 0)}, CCTV: {current_counts.get('cctv', 0)}")
                logger.info(f"🚗 Active journeys: {status.get('active_journeys', 0)}")
                
                # Update totals
                previous_counts = current_counts.copy()
                self.event_counts = current_counts
            
            # Wait 30 seconds before next check
            time.sleep(30)
        
        self.end_time = time.time()
        logger.info("✅ Event monitoring completed")
    
    def test_scenario_injection(self):
        """Test scenario injection functionality"""
        logger.info("🧪 Testing scenario injection...")
        
        scenarios_to_test = [
            {"scenario": "evasion", "params": {}},
            {"scenario": "incident", "params": {"zone_id": "ZONE-06", "duration_minutes": 2}},
            {"scenario": "wildlife", "params": {"zone_id": "ZONE-04"}},
            {"scenario": "ghost_vehicle", "params": {}},
            {"scenario": "high_risk_hour", "params": {"duration_minutes": 2}}
        ]
        
        for scenario_config in scenarios_to_test:
            try:
                response = requests.post(
                    f"{self.simulator_url}/scenario",
                    json=scenario_config,
                    timeout=5
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Scenario {scenario_config['scenario']} injected: {result.get('message')}")
                else:
                    logger.error(f"❌ Failed to inject scenario {scenario_config['scenario']}: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Failed to inject scenario {scenario_config['scenario']}: {e}")
            
            # Wait a bit between scenarios
            time.sleep(5)
    
    def generate_report(self):
        """Generate test report"""
        logger.info("\n" + "="*60)
        logger.info("📋 PHASE 1 VERIFICATION REPORT")
        logger.info("="*60)
        
        # Calculate statistics
        test_duration_real = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        logger.info(f"⏱️  Real test duration: {test_duration_real:.1f} seconds")
        logger.info(f"📊 Total ANPR events generated: {self.event_counts.get('anpr', 0)}")
        logger.info(f"📊 Total FASTag events generated: {self.event_counts.get('fastag', 0)}")
        logger.info(f"📊 Total CCTV events generated: {self.event_counts.get('cctv', 0)}")
        
        total_events = sum(self.event_counts.values())
        logger.info(f"📊 Total events generated: {total_events}")
        
        if total_events > 0:
            logger.info(f"📊 Event distribution:")
            logger.info(f"   - ANPR: {(self.event_counts.get('anpr', 0) / total_events * 100):.1f}%")
            logger.info(f"   - FASTag: {(self.event_counts.get('fastag', 0) / total_events * 100):.1f}%")
            logger.info(f"   - CCTV: {(self.event_counts.get('cctv', 0) / total_events * 100):.1f}%")
        
        # Check if we have reasonable event generation
        anpr_events = self.event_counts.get('anpr', 0)
        fastag_events = self.event_counts.get('fastag', 0)
        cctv_events = self.event_counts.get('cctv', 0)
        
        logger.info("\n🔍 VALIDATION RESULTS:")
        
        # Basic validation criteria
        success = True
        
        if anpr_events < 50:
            logger.warning(f"⚠️  Low ANPR event count: {anpr_events} (expected > 50 for 10 minutes)")
            success = False
        else:
            logger.info(f"✅ ANPR events: {anpr_events} (sufficient)")
        
        if fastag_events < 20:
            logger.warning(f"⚠️  Low FASTag event count: {fastag_events} (expected > 20 for 10 minutes)")
            success = False
        else:
            logger.info(f"✅ FASTag events: {fastag_events} (sufficient)")
        
        if cctv_events < 100:
            logger.warning(f"⚠️  Low CCTV event count: {cctv_events} (expected > 100 for 10 minutes)")
            success = False
        else:
            logger.info(f"✅ CCTV events: {cctv_events} (sufficient)")
        
        if success:
            logger.info("\n🎉 PHASE 1 VERIFICATION: PASSED")
            logger.info("✅ All event types are generating at expected rates")
            logger.info("✅ Simulator is functioning correctly")
        else:
            logger.error("\n❌ PHASE 1 VERIFICATION: FAILED")
            logger.error("⚠️  Some event types are not generating sufficient events")
            logger.error("⚠️  Please check simulator configuration and logs")
        
        return success
    
    def run_test(self):
        """Run the complete Phase 1 test"""
        logger.info("🚀 Starting Phase 1 Verification Test")
        logger.info("="*60)
        
        # Check if simulator is running
        if not self.check_simulator_health():
            logger.error("❌ Simulator is not running. Please start the simulator first.")
            logger.error("Run: python -m simulator.main")
            return False
        
        self.start_time = time.time()
        
        # Get initial status
        initial_status = self.get_simulator_status()
        if initial_status:
            logger.info(f"📝 Initial simulator state:")
            logger.info(f"   Active: {initial_status.get('active', False)}")
            logger.info(f"   Simulated time: {initial_status.get('simulated_time', 'Unknown')}")
            logger.info(f"   Active journeys: {initial_status.get('active_journeys', 0)}")
        
        # Monitor events for specified duration
        self.monitor_events(self.test_duration_minutes)
        
        # Test scenario injection (brief test)
        logger.info("\n🧪 Testing scenario injection (brief test)...")
        self.test_scenario_injection()
        
        # Generate final report
        return self.generate_report()

def main():
    """Main test function"""
    tester = Phase1Tester()
    
    try:
        success = tester.run_test()
        
        if success:
            logger.info("\n🎉 Phase 1 verification completed successfully!")
            logger.info("You can now proceed to Phase 2.")
        else:
            logger.error("\n❌ Phase 1 verification failed!")
            logger.error("Please check the simulator configuration and logs.")
            exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
    except Exception as e:
        logger.error(f"\n💥 Test failed with error: {e}")
        exit(1)

if __name__ == "__main__":
    main()