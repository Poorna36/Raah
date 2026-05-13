"""
Hard Logic Rules Engine
Implements E1-E5 (evasion) and R1-R3 (risk) rules as specified in HARD_LOGIC_ENGINE.md
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RuleType(Enum):
    """Types of hard logic rules"""
    EVASION = "evasion"
    RISK = "risk"

class EvasionType(Enum):
    """Evasion rule types"""
    E1_NO_FASTAG = "E1"
    E2_CLASS_SWAP = "E2"
    E3_CLASS_MISMATCH = "E3"
    E4_UNREGISTERED = "E4"
    E5_SPEED_ANOMALY = "E5"

class RiskType(Enum):
    """Risk rule types"""
    R1_EXPIRED_DOCS = "R1"
    R2_BLACKLISTED_TAG = "R2"
    R3_MULTIPLE_FLAGS = "R3"

@dataclass
class RuleResult:
    """Result of applying a hard logic rule"""
    rule_id: str
    rule_type: RuleType
    triggered: bool
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: float  # 0.0 to 1.0
    description: str
    details: Dict[str, Any]
    legal_basis: str
    recommended_action: str

@dataclass
class VehicleContext:
    """Context information about a vehicle for rule evaluation"""
    plate_number: str
    registered_class: str
    registration_status: str
    owner_type: str
    fuel_type: str
    fitness_expiry: Optional[datetime]
    insurance_expiry: Optional[datetime]
    puc_upto: Optional[datetime]
    permit_status: str
    permit_expiry: Optional[datetime]
    is_exempt: bool
    exemption_type: Optional[str]

@dataclass
class JourneyContext:
    """Context information about a journey for rule evaluation"""
    journey_id: str
    direction: str
    entry_checkpoint: str
    exit_checkpoint: Optional[str]
    entry_time: datetime
    exit_time: Optional[datetime]
    checkpoints_visited: List[str]
    toll_plazas_visited: List[str]
    toll_plazas_expected: List[str]
    total_toll_paid: float
    avg_speed: float
    max_speed: float
    evasion_flags: List[str]
    evasion_score: float

@dataclass
class EventContext:
    """Context information about specific events for rule evaluation"""
    anpr_events: List[Dict[str, Any]]
    fastag_events: List[Dict[str, Any]]
    checkpoint_sequence: List[Dict[str, Any]]

class HardLogicRules:
    """Implements hard logic rules for evasion and risk detection"""
    
    def __init__(self):
        # Evasion thresholds
        self.evasion_speed_threshold = 91.0  # km/h (from simulator config)
        self.confidence_threshold = 0.85
        self.class_mismatch_severity_threshold = 2  # Number of class tiers difference
        
        # Risk thresholds
        self.document_expiry_warning_days = 30
        self.document_expiry_critical_days = 7
        
        # Rule weights for scoring
        self.evasion_rule_weights = {
            EvasionType.E1_NO_FASTAG: 0.8,
            EvasionType.E2_CLASS_SWAP: 0.9,
            EvasionType.E3_CLASS_MISMATCH: 0.7,
            EvasionType.E4_UNREGISTERED: 1.0,
            EvasionType.E5_SPEED_ANOMALY: 0.6
        }
        
        self.risk_rule_weights = {
            RiskType.R1_EXPIRED_DOCS: 0.5,
            RiskType.R2_BLACKLISTED_TAG: 0.9,
            RiskType.R3_MULTIPLE_FLAGS: 0.8
        }
        
        logger.info("🔧 Hard Logic Rules Engine initialized")
    
    def evaluate_evasion_rules(self, vehicle_context: VehicleContext, 
                              journey_context: JourneyContext,
                              event_context: EventContext) -> List[RuleResult]:
        """Evaluate all evasion rules (E1-E5)"""
        
        results = []
        
        # E1: No FASTag at toll plazas
        results.append(self._evaluate_e1_no_fastag(journey_context, event_context))
        
        # E2: Class swap (FASTag class < registered class)
        results.append(self._evaluate_e2_class_swap(journey_context, event_context))
        
        # E3: Class mismatch (ANPR detected class != registered class)
        results.append(self._evaluate_e3_class_mismatch(journey_context, event_context))
        
        # E4: Unregistered vehicle
        results.append(self._evaluate_e4_unregistered(vehicle_context))
        
        # E5: Speed anomaly
        results.append(self._evaluate_e5_speed_anomaly(journey_context))
        
        return [result for result in results if result is not None]
    
    def evaluate_risk_rules(self, vehicle_context: VehicleContext,
                          journey_context: JourneyContext) -> List[RuleResult]:
        """Evaluate all risk rules (R1-R3)"""
        
        results = []
        
        # R1: Expired documents
        results.append(self._evaluate_r1_expired_docs(vehicle_context))
        
        # R2: Blacklisted FASTag
        results.append(self._evaluate_r2_blacklisted_tag(journey_context))
        
        # R3: Multiple evasion flags
        results.append(self._evaluate_r3_multiple_flags(journey_context))
        
        return [result for result in results if result is not None]
    
    def _evaluate_e1_no_fastag(self, journey_context: JourneyContext,
                             event_context: EventContext) -> Optional[RuleResult]:
        """E1: No FASTag event at expected toll plazas"""
        
        # Get toll plazas where FASTag was expected but not received
        expected_toll_plazas = set(journey_context.toll_plazas_expected)
        visited_toll_plazas = set(journey_context.toll_plazas_visited)
        missing_toll_plazas = expected_toll_plazas - visited_toll_plazas
        
        if not missing_toll_plazas:
            return None
        
        # Check if ANPR events exist at missing toll plazas
        anpr_checkpoint_ids = {event['checkpoint_id'] for event in event_context.anpr_events}
        missing_with_anpr = missing_toll_plazas & anpr_checkpoint_ids
        
        if missing_with_anpr:
            severity = 'high' if len(missing_with_anpr) >= 2 else 'medium'
            confidence = min(0.95, 0.7 + (len(missing_with_anpr) * 0.1))
            
            return RuleResult(
                rule_id=EvasionType.E1_NO_FASTAG.value,
                rule_type=RuleType.EVASION,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description=f"No FASTag payment at {len(missing_with_anpr)} toll plazas where ANPR detected vehicle",
                details={
                    'missing_toll_plazas': list(missing_with_anpr),
                    'total_expected': len(expected_toll_plazas),
                    'total_visited': len(visited_toll_plazas)
                },
                legal_basis="Section 8 of NH Fee Rules - Mandatory FASTag usage",
                recommended_action="Issue penalty notice and investigate vehicle registration"
            )
        
        return None
    
    def _evaluate_e2_class_swap(self, journey_context: JourneyContext,
                              event_context: EventContext) -> Optional[RuleResult]:
        """E2: FASTag class lower than registered class (deliberate underpayment)"""
        
        # Look for FASTag events with class mismatch
        class_swap_events = []
        
        for fastag_event in event_context.fastag_events:
            tagged_class = fastag_event.get('vehicle_class_tagged')
            registered_class = fastag_event.get('vehicle_class_registered')
            
            if tagged_class and registered_class and tagged_class != registered_class:
                # Check if tagged class is lower (indicating underpayment)
                if self._is_lower_vehicle_class(tagged_class, registered_class):
                    class_swap_events.append({
                        'checkpoint_id': fastag_event['checkpoint_id'],
                        'tagged_class': tagged_class,
                        'registered_class': registered_class,
                        'amount_charged': fastag_event.get('amount_charged', 0)
                    })
        
        if class_swap_events:
            total_underpayment = sum(event['amount_charged'] for event in class_swap_events)
            severity = 'critical' if len(class_swap_events) >= 3 else 'high'
            confidence = min(0.98, 0.8 + (len(class_swap_events) * 0.05))
            
            return RuleResult(
                rule_id=EvasionType.E2_CLASS_SWAP.value,
                rule_type=RuleType.EVASION,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description=f"Deliberate underpayment through class swapping at {len(class_swap_events)} toll plazas",
                details={
                    'class_swap_events': class_swap_events,
                    'estimated_loss': total_underpayment,
                    'registered_class': class_swap_events[0]['registered_class'] if class_swap_events else None
                },
                legal_basis="Section 420 IPC - Cheating and dishonestly inducing delivery of property",
                recommended_action="File criminal case for cheating and recover dues"
            )
        
        return None
    
    def _evaluate_e3_class_mismatch(self, journey_context: JourneyContext,
                                  event_context: EventContext) -> Optional[RuleResult]:
        """E3: ANPR detected class different from registered class"""
        
        # Look for ANPR events with class mismatch
        class_mismatch_events = []
        
        for anpr_event in event_context.anpr_events:
            detected_class = anpr_event.get('detected_class')
            registered_class = anpr_event.get('registered_class')
            confidence = anpr_event.get('confidence', 0.0)
            
            if (detected_class and registered_class and detected_class != registered_class and 
                confidence >= self.confidence_threshold):
                
                # Calculate severity based on class difference
                class_diff_severity = self._calculate_class_difference_severity(detected_class, registered_class)
                
                class_mismatch_events.append({
                    'checkpoint_id': anpr_event['checkpoint_id'],
                    'detected_class': detected_class,
                    'registered_class': registered_class,
                    'confidence': confidence,
                    'severity': class_diff_severity
                })
        
        if class_mismatch_events:
            # Filter for significant mismatches
            significant_mismatches = [event for event in class_mismatch_events if event['severity'] >= self.class_mismatch_severity_threshold]
            
            if significant_mismatches:
                severity = 'high' if len(significant_mismatches) >= 2 else 'medium'
                confidence = min(0.9, 0.6 + (len(significant_mismatches) * 0.1))
                
                return RuleResult(
                    rule_id=EvasionType.E3_CLASS_MISMATCH.value,
                    rule_type=RuleType.EVASION,
                    triggered=True,
                    severity=severity,
                    confidence=confidence,
                    description=f"Significant vehicle class mismatch detected at {len(significant_mismatches)} checkpoints",
                    details={
                        'mismatch_events': significant_mismatches,
                        'total_events': len(class_mismatch_events),
                        'avg_confidence': sum(e['confidence'] for e in significant_mismatches) / len(significant_mismatches) if significant_mismatches else 0
                    },
                    legal_basis="Section 192 IPC - Fabricating false evidence",
                    recommended_action="Verify vehicle registration and investigate potential fraud"
                )
        
        return None
    
    def _evaluate_e4_unregistered(self, vehicle_context: VehicleContext) -> Optional[RuleResult]:
        """E4: Vehicle not found in registration database"""
        
        if vehicle_context.registration_status == 'unregistered' or not vehicle_context.plate_number:
            severity = 'critical'
            confidence = 0.95
            
            return RuleResult(
                rule_id=EvasionType.E4_UNREGISTERED.value,
                rule_type=RuleType.EVASION,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description="Vehicle not found in registration database - potential fake plate or unregistered vehicle",
                details={
                    'plate_number': vehicle_context.plate_number,
                    'registration_status': vehicle_context.registration_status
                },
                legal_basis="Section 39 of Motor Vehicles Act - Registration of motor vehicles",
                recommended_action="Immediate vehicle detention and thorough investigation"
            )
        
        return None
    
    def _evaluate_e5_speed_anomaly(self, journey_context: JourneyContext) -> Optional[RuleResult]:
        """E5: Speed anomaly indicating potential evasion"""
        
        # Check for speed-based evasion indicators
        speed_anomalies = []
        
        if journey_context.max_speed > self.evasion_speed_threshold:
            speed_anomalies.append({
                'type': 'max_speed_exceeded',
                'speed': journey_context.max_speed,
                'threshold': self.evasion_speed_threshold
            })
        
        # Check for journey time anomalies (too fast = potential bypass)
        if journey_context.exit_time and journey_context.entry_time:
            actual_duration = (journey_context.exit_time - journey_context.entry_time).total_seconds() / 3600  # hours
            expected_duration = len(journey_context.checkpoints_visited) * 0.17  # ~10 minutes per checkpoint
            
            if actual_duration > 0 and actual_duration < expected_duration * 0.7:  # 30% faster than expected
                speed_anomalies.append({
                    'type': 'journey_time_anomaly',
                    'actual_duration': actual_duration,
                    'expected_duration': expected_duration,
                    'speed_ratio': expected_duration / actual_duration if actual_duration > 0 else 0
                })
        
        if speed_anomalies:
            severity = 'high' if len(speed_anomalies) >= 2 else 'medium'
            confidence = min(0.85, 0.5 + (len(speed_anomalies) * 0.15))
            
            return RuleResult(
                rule_id=EvasionType.E5_SPEED_ANOMALY.value,
                rule_type=RuleType.EVASION,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description=f"Speed anomalies detected: {len(speed_anomalies)} indicators",
                details={
                    'anomalies': speed_anomalies,
                    'max_speed': journey_context.max_speed,
                    'avg_speed': journey_context.avg_speed
                },
                legal_basis="Section 184 of Motor Vehicles Act - Driving dangerously",
                recommended_action="Issue speeding ticket and investigate route taken"
            )
        
        return None
    
    def _evaluate_r1_expired_docs(self, vehicle_context: VehicleContext) -> Optional[RuleResult]:
        """R1: Expired vehicle documents"""
        
        expired_docs = []
        current_date = datetime.now().date()
        
        # Check fitness certificate
        if vehicle_context.fitness_expiry and vehicle_context.fitness_expiry < current_date:
            days_expired = (current_date - vehicle_context.fitness_expiry).days
            expired_docs.append({
                'document': 'fitness_certificate',
                'expiry_date': vehicle_context.fitness_expiry.isoformat(),
                'days_expired': days_expired,
                'severity': 'critical' if days_expired > 30 else 'high'
            })
        
        # Check insurance
        if vehicle_context.insurance_expiry and vehicle_context.insurance_expiry < current_date:
            days_expired = (current_date - vehicle_context.insurance_expiry).days
            expired_docs.append({
                'document': 'insurance',
                'expiry_date': vehicle_context.insurance_expiry.isoformat(),
                'days_expired': days_expired,
                'severity': 'critical' if days_expired > 7 else 'high'
            })
        
        # Check PUC
        if vehicle_context.puc_upto and vehicle_context.puc_upto < current_date:
            days_expired = (current_date - vehicle_context.puc_upto).days
            expired_docs.append({
                'document': 'puc_certificate',
                'expiry_date': vehicle_context.puc_upto.isoformat(),
                'days_expired': days_expired,
                'severity': 'medium'
            })
        
        # Check permit
        if (vehicle_context.permit_status == 'expired' or 
            (vehicle_context.permit_expiry and vehicle_context.permit_expiry < current_date)):
            days_expired = 0
            if vehicle_context.permit_expiry:
                days_expired = (current_date - vehicle_context.permit_expiry).days
            expired_docs.append({
                'document': 'permit',
                'expiry_date': vehicle_context.permit_expiry.isoformat() if vehicle_context.permit_expiry else None,
                'days_expired': days_expired,
                'severity': 'high'
            })
        
        if expired_docs:
            # Determine overall severity
            severities = [doc['severity'] for doc in expired_docs]
            if 'critical' in severities:
                overall_severity = 'critical'
            elif 'high' in severities:
                overall_severity = 'high'
            else:
                overall_severity = 'medium'
            
            confidence = min(0.95, 0.7 + (len(expired_docs) * 0.1))
            
            return RuleResult(
                rule_id=RiskType.R1_EXPIRED_DOCS.value,
                rule_type=RuleType.RISK,
                triggered=True,
                severity=overall_severity,
                confidence=confidence,
                description=f"Vehicle has {len(expired_docs)} expired documents",
                details={
                    'expired_documents': expired_docs,
                    'total_expired': len(expired_docs),
                    'most_severe': max(severities, key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
                },
                legal_basis="Section 130 of Motor Vehicles Act - Duty to produce documents",
                recommended_action="Issue compoundable offence notice and require document renewal"
            )
        
        return None
    
    def _evaluate_r2_blacklisted_tag(self, journey_context: JourneyContext) -> Optional[RuleResult]:
        """R2: Blacklisted FASTag"""
        
        # Look for blacklisted tag transactions
        blacklisted_events = []
        
        for fastag_event in journey_context.get('fastag_events', []):
            if fastag_event.get('transaction_status') == 'blacklisted':
                blacklisted_events.append({
                    'checkpoint_id': fastag_event['checkpoint_id'],
                    'timestamp': fastag_event['timestamp'],
                    'tag_id': fastag_event.get('tag_id')
                })
        
        if blacklisted_events:
            severity = 'critical'
            confidence = 0.98
            
            return RuleResult(
                rule_id=RiskType.R2_BLACKLISTED_TAG.value,
                rule_type=RuleType.RISK,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description=f"Blacklisted FASTag used at {len(blacklisted_events)} toll plazas",
                details={
                    'blacklisted_events': blacklisted_events,
                    'tag_id': blacklisted_events[0]['tag_id'] if blacklisted_events else None
                },
                legal_basis="Section 8 of NH Fee Rules - FASTag compliance",
                recommended_action="Immediate vehicle detention and confiscate FASTag device"
            )
        
        return None
    
    def _evaluate_r3_multiple_flags(self, journey_context: JourneyContext) -> Optional[RuleResult]:
        """R3: Multiple evasion flags indicating habitual offender"""
        
        evasion_flags = journey_context.evasion_flags
        
        if len(evasion_flags) >= 3:
            severity = 'high' if len(evasion_flags) >= 5 else 'medium'
            confidence = min(0.95, 0.6 + (len(evasion_flags) * 0.08))
            
            # Count different types of evasion
            evasion_types = {}
            for flag in evasion_flags:
                flag_type = flag.split(':')[0] if ':' in flag else flag
                evasion_types[flag_type] = evasion_types.get(flag_type, 0) + 1
            
            return RuleResult(
                rule_id=RiskType.R3_MULTIPLE_FLAGS.value,
                rule_type=RuleType.RISK,
                triggered=True,
                severity=severity,
                confidence=confidence,
                description=f"Vehicle shows {len(evasion_flags)} evasion indicators - potential habitual offender",
                details={
                    'total_flags': len(evasion_flags),
                    'flag_breakdown': evasion_types,
                    'evasion_score': journey_context.evasion_score
                },
                legal_basis="Section 75 of IPC - Enhanced punishment for habitual offenders",
                recommended_action="Enhanced surveillance and priority investigation"
            )
        
        return None
    
    def _is_lower_vehicle_class(self, tagged_class: str, registered_class: str) -> bool:
        """Check if tagged class is lower than registered class"""
        
        # Vehicle class hierarchy (lower index = lower class)
        class_hierarchy = ['2W', 'Car', 'LMV', 'Bus', 'Truck', 'MAV']
        
        try:
            tagged_index = class_hierarchy.index(tagged_class)
            registered_index = class_hierarchy.index(registered_class)
            return tagged_index < registered_index
        except ValueError:
            # Unknown class, assume not lower
            return False
    
    def _calculate_class_difference_severity(self, detected_class: str, registered_class: str) -> int:
        """Calculate severity of class difference"""
        
        class_hierarchy = ['2W', 'Car', 'LMV', 'Bus', 'Truck', 'MAV']
        
        try:
            detected_index = class_hierarchy.index(detected_class)
            registered_index = class_hierarchy.index(registered_class)
            return abs(detected_index - registered_index)
        except ValueError:
            # Unknown class, assume minimal difference
            return 1
    
    def get_rule_weights(self) -> Dict[str, float]:
        """Get rule weights for scoring calculations"""
        return {
            **{rule.value: weight for rule, weight in self.evasion_rule_weights.items()},
            **{rule.value: weight for rule, weight in self.risk_rule_weights.items()}
        }
    
    def get_rule_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all rules"""
        return {
            EvasionType.E1_NO_FASTAG.value: "No FASTag payment at toll plazas",
            EvasionType.E2_CLASS_SWAP.value: "Deliberate underpayment through class swapping",
            EvasionType.E3_CLASS_MISMATCH.value: "ANPR detected class different from registration",
            EvasionType.E4_UNREGISTERED.value: "Vehicle not found in registration database",
            EvasionType.E5_SPEED_ANOMALY.value: "Speed anomalies indicating potential evasion",
            RiskType.R1_EXPIRED_DOCS.value: "Expired vehicle documents",
            RiskType.R2_BLACKLISTED_TAG.value: "Blacklisted FASTag usage",
            RiskType.R3_MULTIPLE_FLAGS.value: "Multiple evasion indicators - habitual offender"
        }