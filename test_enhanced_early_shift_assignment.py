#!/usr/bin/env python3
"""
Enhanced Early Shift Assignment Tests

Tests for the enhanced early shift assignment logic that ensures:
1. On-call engineer is always assigned as Early1 during weekdays
2. Fair selection of second early shift engineer
3. Comprehensive decision logging for early shift assignments
"""

import sys
import os
from datetime import date, timedelta
import pandas as pd

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schedule_core import (
    make_schedule_with_decisions, generate_day_assignments, 
    select_second_early_engineer, EnhancedFairnessTracker,
    build_rotation, nearest_previous_sunday, is_weekday
)
from models import DecisionEntry


def test_oncall_engineer_always_early1_weekdays():
    """Test that on-call engineer is always assigned as Early1 during weekdays."""
    print("🧪 Testing on-call engineer is always Early1 during weekdays...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)  # Sunday
    weeks = 2
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    leave = pd.DataFrame()  # No leave
    
    # Generate schedule with decision logging
    df, decision_log, weekend_compensation = make_schedule_with_decisions(
        start_sunday, weeks, engineers, seeds, leave
    )
    
    # Check each weekday to ensure on-call engineer is Early1
    weekday_violations = []
    for _, row in df.iterrows():
        if is_weekday(row['Date']):
            oncall_engineer = row['OnCall']
            early1_engineer = row['Early1']
            
            if oncall_engineer and early1_engineer and oncall_engineer != early1_engineer:
                weekday_violations.append({
                    'date': row['Date'],
                    'day': row['Day'],
                    'oncall': oncall_engineer,
                    'early1': early1_engineer
                })
    
    assert len(weekday_violations) == 0, f"On-call engineer not assigned as Early1 on weekdays: {weekday_violations}"
    print("  ✅ On-call engineer is always assigned as Early1 during weekdays")
    
    # Verify decision logging includes enhanced early shift assignments
    enhanced_early_decisions = [
        entry for entry in decision_log 
        if entry.decision_type == "enhanced_early_shift_assignment"
    ]
    
    # Should have enhanced early shift decisions for weekdays
    weekdays_count = sum(1 for _, row in df.iterrows() if is_weekday(row['Date']))
    assert len(enhanced_early_decisions) > 0, "No enhanced early shift assignment decisions found"
    print(f"  ✅ Found {len(enhanced_early_decisions)} enhanced early shift assignment decisions for {weekdays_count} weekdays")


def test_fair_selection_second_early_engineer():
    """Test fair selection of second early shift engineer using fairness tracker."""
    print("🧪 Testing fair selection of second early shift engineer...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    fairness_tracker = EnhancedFairnessTracker(engineers)
    
    # Simulate some existing assignments to create fairness imbalance
    fairness_tracker.track_assignment("Alice", "early", 3.0)  # Alice has more early shifts
    fairness_tracker.track_assignment("Bob", "early", 1.0)
    fairness_tracker.track_assignment("Charlie", "early", 0.0)  # Charlie has fewer
    
    # Test second early engineer selection
    available_engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    oncall_engineer = "Frank"  # Frank is on-call, so excluded from Early2
    seeds = {"early": 0}
    day_idx = 0
    
    selected_engineer = select_second_early_engineer(
        available_engineers, oncall_engineer, engineers, seeds, day_idx, fairness_tracker
    )
    
    # Charlie should be preferred due to lower early shift count
    fairness_weights = fairness_tracker.get_fairness_weights('early')
    print(f"  Fairness weights: {fairness_weights}")
    print(f"  Selected engineer: {selected_engineer}")
    
    # Verify selection considers fairness (Charlie should be preferred)
    assert selected_engineer in available_engineers, f"Selected engineer {selected_engineer} not in available list"
    assert selected_engineer != oncall_engineer, f"Selected engineer {selected_engineer} should not be the on-call engineer"
    
    # Charlie should be selected due to lowest fairness weight
    expected_engineer = "Charlie"
    assert selected_engineer == expected_engineer, f"Expected {expected_engineer} (lowest early count), got {selected_engineer}"
    print(f"  ✅ Fair selection working: {selected_engineer} selected (lowest early shift count)")


def test_early_shift_decision_logging_completeness():
    """Test that early shift assignment decision logging is comprehensive."""
    print("🧪 Testing early shift assignment decision logging completeness...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)  # Sunday
    leave_map = {}
    for e in engineers:
        leave_map[e] = set()
    
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    decision_log = []
    fairness_tracker = EnhancedFairnessTracker(engineers)
    
    # Test a specific weekday
    test_date = date(2024, 1, 8)  # Monday
    weekend_seeded = build_rotation(engineers, seeds.get("weekend", 0))
    
    working, leave_today, roles = generate_day_assignments(
        test_date, engineers, start_sunday, weekend_seeded, leave_map, seeds,
        False, decision_log, fairness_tracker
    )
    
    # Find early shift assignment decisions
    early_decisions = [
        entry for entry in decision_log 
        if "early_shift" in entry.decision_type
    ]
    
    assert len(early_decisions) > 0, "No early shift assignment decisions found"
    
    # Verify decision entry completeness
    for decision in early_decisions:
        assert decision.date, "Decision entry missing date"
        assert decision.decision_type, "Decision entry missing decision_type"
        assert decision.affected_engineers, "Decision entry missing affected_engineers"
        assert decision.reason, "Decision entry missing reason"
        assert isinstance(decision.alternatives_considered, list), "Decision entry alternatives_considered should be a list"
        
        print(f"  Decision: {decision.decision_type}")
        print(f"    Date: {decision.date}")
        print(f"    Engineers: {decision.affected_engineers}")
        print(f"    Reason: {decision.reason}")
        print(f"    Alternatives: {decision.alternatives_considered}")
    
    print(f"  ✅ Found {len(early_decisions)} comprehensive early shift decision entries")


def test_early_shift_weekend_vs_weekday_logic():
    """Test that early shift logic differs appropriately between weekends and weekdays."""
    print("🧪 Testing early shift weekend vs weekday logic...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)  # Sunday
    leave_map = {}
    for e in engineers:
        leave_map[e] = set()
    
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    weekend_seeded = build_rotation(engineers, seeds.get("weekend", 0))
    fairness_tracker = EnhancedFairnessTracker(engineers)
    
    # Test weekday (Monday)
    weekday_decision_log = []
    monday = date(2024, 1, 8)  # Monday
    working_mon, _, roles_mon = generate_day_assignments(
        monday, engineers, start_sunday, weekend_seeded, leave_map, seeds,
        False, weekday_decision_log, fairness_tracker
    )
    
    # Test weekend (Saturday) with early shifts enabled
    weekend_decision_log = []
    saturday = date(2024, 1, 13)  # Saturday
    working_sat, _, roles_sat = generate_day_assignments(
        saturday, engineers, start_sunday, weekend_seeded, leave_map, seeds,
        True, weekend_decision_log, fairness_tracker  # assign_early_on_weekends=True
    )
    
    # Check decision types
    weekday_early_decisions = [d for d in weekday_decision_log if "early_shift" in d.decision_type]
    weekend_early_decisions = [d for d in weekend_decision_log if "early_shift" in d.decision_type]
    
    print(f"  Weekday early decisions: {[d.decision_type for d in weekday_early_decisions]}")
    print(f"  Weekend early decisions: {[d.decision_type for d in weekend_early_decisions]}")
    
    # Weekday should use enhanced logic
    enhanced_weekday = any("enhanced" in d.decision_type for d in weekday_early_decisions)
    assert enhanced_weekday, "Weekday should use enhanced early shift assignment logic"
    
    # Weekend should use standard logic
    weekend_standard = any("weekend_early_shift" in d.decision_type for d in weekend_early_decisions)
    assert weekend_standard, "Weekend should use standard early shift assignment logic"
    
    print("  ✅ Weekday uses enhanced logic, weekend uses standard logic")


def test_early_shift_with_limited_engineers():
    """Test early shift assignment when only one engineer is available."""
    print("🧪 Testing early shift assignment with limited engineers...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)  # Sunday
    
    # Create leave scenario where most engineers are on leave
    leave_map = {
        "Alice": {date(2024, 1, 8)},  # Monday
        "Bob": {date(2024, 1, 8)},
        "Charlie": {date(2024, 1, 8)},
        "Diana": {date(2024, 1, 8)},
        "Eve": set(),  # Available
        "Frank": set()  # Available
    }
    
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    weekend_seeded = build_rotation(engineers, seeds.get("weekend", 0))
    fairness_tracker = EnhancedFairnessTracker(engineers)
    decision_log = []
    
    # Test Monday with limited engineers
    monday = date(2024, 1, 8)  # Monday
    working, leave_today, roles = generate_day_assignments(
        monday, engineers, start_sunday, weekend_seeded, leave_map, seeds,
        False, decision_log, fairness_tracker
    )
    
    print(f"  Working engineers: {working}")
    print(f"  Engineers on leave: {leave_today}")
    print(f"  Early1: {roles['Early1']}")
    print(f"  Early2: {roles['Early2']}")
    print(f"  OnCall: {roles['OnCall']}")
    
    # Should handle limited engineers gracefully
    assert roles['Early1'], "Early1 should be assigned even with limited engineers"
    
    # Check decision logging for limited engineer scenario
    early_decisions = [d for d in decision_log if "early_shift" in d.decision_type]
    assert len(early_decisions) > 0, "Should have early shift decisions even with limited engineers"
    
    print("  ✅ Early shift assignment handles limited engineers gracefully")


def run_all_tests():
    """Run all enhanced early shift assignment tests."""
    print("🚀 Running Enhanced Early Shift Assignment Tests\n")
    
    try:
        test_oncall_engineer_always_early1_weekdays()
        print()
        
        test_fair_selection_second_early_engineer()
        print()
        
        test_early_shift_decision_logging_completeness()
        print()
        
        test_early_shift_weekend_vs_weekday_logic()
        print()
        
        test_early_shift_with_limited_engineers()
        print()
        
        print("✅ All Enhanced Early Shift Assignment Tests Passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)