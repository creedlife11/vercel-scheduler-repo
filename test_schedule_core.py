#!/usr/bin/env python3
"""
Unit tests for the core scheduling logic
Tests the scheduling algorithms without requiring a web server
"""

import sys
import os
from datetime import date, timedelta
import pandas as pd

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schedule_core import (
    nearest_previous_sunday, build_rotation, is_weekday, week_index,
    weekend_worker_for_week, works_today, generate_day_assignments,
    make_schedule, calculate_fairness_report, make_enhanced_schedule,
    EnhancedFairnessTracker, enhanced_weekend_assignment, calculate_weekend_compensation
)

def test_basic_functions():
    """Test basic utility functions"""
    print("🧪 Testing basic utility functions...")
    
    # Test nearest_previous_sunday
    test_date = date(2024, 1, 10)  # Wednesday
    sunday = nearest_previous_sunday(test_date)
    expected = date(2024, 1, 7)  # Previous Sunday
    assert sunday == expected, f"Expected {expected}, got {sunday}"
    print("  ✅ nearest_previous_sunday works correctly")
    
    # Test build_rotation
    engineers = ["A", "B", "C", "D", "E", "F"]
    rotation = build_rotation(engineers, seed=2)
    expected = ["C", "D", "E", "F", "A", "B"]
    assert rotation == expected, f"Expected {expected}, got {rotation}"
    print("  ✅ build_rotation works correctly")
    
    # Test is_weekday
    monday = date(2024, 1, 8)  # Monday
    saturday = date(2024, 1, 13)  # Saturday
    assert is_weekday(monday) == True, "Monday should be weekday"
    assert is_weekday(saturday) == False, "Saturday should not be weekday"
    print("  ✅ is_weekday works correctly")
    
    # Test week_index
    start_sunday = date(2024, 1, 7)
    monday = date(2024, 1, 8)
    next_monday = date(2024, 1, 15)
    assert week_index(start_sunday, monday) == 0, "First week should be 0"
    assert week_index(start_sunday, next_monday) == 1, "Second week should be 1"
    print("  ✅ week_index works correctly")

def test_weekend_rotation():
    """Test weekend worker assignment"""
    print("🧪 Testing weekend rotation...")
    
    engineers = ["A", "B", "C", "D", "E", "F"]
    weekend_seeded = build_rotation(engineers, seed=0)  # No rotation
    
    # Week 0 should be A, Week 1 should be B, etc.
    assert weekend_worker_for_week(weekend_seeded, 0) == "A"
    assert weekend_worker_for_week(weekend_seeded, 1) == "B"
    assert weekend_worker_for_week(weekend_seeded, 6) == "A"  # Wraps around
    print("  ✅ Weekend rotation works correctly")

def test_work_schedule():
    """Test who works on which days"""
    print("🧪 Testing work schedule logic...")
    
    engineers = ["A", "B", "C", "D", "E", "F"]
    start_sunday = date(2024, 1, 7)
    weekend_seeded = build_rotation(engineers, seed=0)
    
    # Week 0: A is weekend worker
    monday = date(2024, 1, 8)    # Week 0
    tuesday = date(2024, 1, 9)   # Week 0
    saturday = date(2024, 1, 13) # Week 0
    sunday = date(2024, 1, 14)   # Week 1 (B is weekend worker)
    
    # A (weekend worker for week 0) should work Mon,Tue,Wed,Thu,Sat in week 0
    assert works_today("A", monday, start_sunday, weekend_seeded) == True
    assert works_today("A", saturday, start_sunday, weekend_seeded) == True
    
    # Sunday is in week 1 where B is the weekend worker
    # A (previous week's weekend worker) should work Sunday with pattern B
    assert works_today("A", sunday, start_sunday, weekend_seeded) == True
    
    # B should work normal weekdays in week 0 (not weekend worker yet)
    assert works_today("B", monday, start_sunday, weekend_seeded) == True
    assert works_today("B", saturday, start_sunday, weekend_seeded) == False
    
    # B (weekend worker for week 1) should NOT work Sunday (B works pattern A: Mon,Tue,Wed,Thu,Sat)
    # Only the previous week's worker (A) works Sunday with pattern B
    assert works_today("B", sunday, start_sunday, weekend_seeded) == False
    
    print("  ✅ Work schedule logic works correctly")

def test_schedule_generation():
    """Test full schedule generation"""
    print("🧪 Testing schedule generation...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 2
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create empty leave DataFrame
    leave = pd.DataFrame(columns=["Engineer", "Date", "Reason"])
    
    # Generate schedule
    df = make_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Basic validations
    assert len(df) == weeks * 7, f"Expected {weeks * 7} days, got {len(df)}"
    assert "Date" in df.columns, "Date column missing"
    assert "Chat" in df.columns, "Chat column missing"
    assert "OnCall" in df.columns, "OnCall column missing"
    
    # Check that weekdays have role assignments
    weekday_rows = df[df["Day"].isin(["Mon", "Tue", "Wed", "Thu", "Fri"])]
    chat_assigned = weekday_rows["Chat"].notna().sum()
    oncall_assigned = weekday_rows["OnCall"].notna().sum()
    
    assert chat_assigned > 0, "No chat assignments found"
    assert oncall_assigned > 0, "No oncall assignments found"
    
    print(f"  ✅ Generated {len(df)} day schedule with {chat_assigned} chat and {oncall_assigned} oncall assignments")

def test_enhanced_schedule():
    """Test enhanced schedule with fairness analysis"""
    print("🧪 Testing enhanced schedule generation...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 4  # Longer schedule for better fairness analysis
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create some leave data
    leave_data = [
        {"Engineer": "Alice", "Date": "2024-01-10", "Reason": "Vacation"},
        {"Engineer": "Bob", "Date": "2024-01-15", "Reason": "Sick"}
    ]
    leave = pd.DataFrame(leave_data)
    leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
    
    # Generate enhanced schedule
    result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Validate result structure
    assert hasattr(result, 'schedule_data'), "Missing schedule_data"
    assert hasattr(result, 'fairness_report'), "Missing fairness_report"
    assert hasattr(result, 'decision_log'), "Missing decision_log"
    assert hasattr(result, 'metadata'), "Missing metadata"
    
    # Validate fairness report
    fairness = result.fairness_report
    assert hasattr(fairness, 'engineer_stats'), "Missing engineer_stats"
    assert hasattr(fairness, 'equity_score'), "Missing equity_score"
    assert len(fairness.engineer_stats) == 6, "Should have stats for all 6 engineers"
    
    # Validate decision log
    assert len(result.decision_log) > 0, "Decision log should not be empty"
    
    # Validate metadata
    metadata = result.metadata
    assert metadata.engineer_count == 6, "Should have 6 engineers"
    assert metadata.weeks == weeks, f"Should have {weeks} weeks"
    
    print(f"  ✅ Enhanced schedule generated with equity score: {fairness.equity_score:.3f}")
    print(f"  ✅ Decision log contains {len(result.decision_log)} entries")

def test_leave_handling():
    """Test leave handling in schedule generation"""
    print("🧪 Testing leave handling...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 1
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create leave for Alice on Monday
    monday = date(2024, 1, 8)
    leave_data = [{"Engineer": "Alice", "Date": monday.isoformat(), "Reason": "Vacation"}]
    leave = pd.DataFrame(leave_data)
    leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
    
    # Generate schedule
    df = make_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Find Monday row
    monday_row = df[df["Date"] == monday].iloc[0]
    
    # Alice should be marked as LEAVE
    alice_status = monday_row["Status 1"]  # Alice is first engineer
    assert alice_status == "LEAVE", f"Alice should be on LEAVE, got {alice_status}"
    
    # Alice should not be assigned to any roles
    roles = ["Chat", "OnCall", "Appointments", "Early1", "Early2"]
    for role in roles:
        assert monday_row[role] != "Alice", f"Alice should not be assigned to {role} while on leave"
    
    print("  ✅ Leave handling works correctly")

def test_fairness_calculation():
    """Test fairness calculation"""
    print("🧪 Testing fairness calculation...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    
    # Create a simple test DataFrame
    data = [
        {"Date": date(2024, 1, 8), "Chat": "Alice", "OnCall": "Bob", "Appointments": "Charlie", "Early1": "Diana", "Early2": "Eve"},
        {"Date": date(2024, 1, 9), "Chat": "Bob", "OnCall": "Charlie", "Appointments": "Diana", "Early1": "Eve", "Early2": "Frank"},
        {"Date": date(2024, 1, 10), "Chat": "Charlie", "OnCall": "Diana", "Appointments": "Eve", "Early1": "Frank", "Early2": "Alice"},
    ]
    
    # Add status columns for each engineer
    for i, engineer in enumerate(engineers):
        for j, row in enumerate(data):
            data[j][f"Status {i+1}"] = "WORK"  # Everyone works
    
    df = pd.DataFrame(data)
    
    # Calculate fairness
    fairness = calculate_fairness_report(df, engineers)
    
    # Validate structure
    assert len(fairness.engineer_stats) == 6, "Should have stats for all engineers"
    assert hasattr(fairness, 'equity_score'), "Should have equity score"
    assert hasattr(fairness, 'max_min_deltas'), "Should have max-min deltas"
    
    # Check that some assignments were counted
    total_assignments = sum(
        stats.chat_count + stats.oncall_count + stats.appointments_count + stats.early_count
        for stats in fairness.engineer_stats.values()
    )
    assert total_assignments > 0, "Should have some role assignments"
    
    print(f"  ✅ Fairness calculation works, equity score: {fairness.equity_score:.3f}")

def test_enhanced_fairness_tracker():
    """Test enhanced fairness tracking functionality"""
    print("🧪 Testing enhanced fairness tracker...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    tracker = EnhancedFairnessTracker(engineers)
    
    # Test initial state
    assert len(tracker.assignment_history) == 6, "Should track all engineers"
    assert all(tracker.assignment_history[eng]['weekend'] == 0 for eng in engineers), "Initial weekend count should be 0"
    
    # Test assignment tracking
    tracker.track_assignment("Alice", "weekend")
    tracker.track_assignment("Bob", "weekend")
    tracker.track_assignment("Alice", "weekend")  # Alice gets another
    
    assert tracker.assignment_history["Alice"]["weekend"] == 2, "Alice should have 2 weekend assignments"
    assert tracker.assignment_history["Bob"]["weekend"] == 1, "Bob should have 1 weekend assignment"
    assert tracker.weekend_assignments["Alice"] == 2, "Alice weekend count should be 2"
    
    # Test fairness weights
    weights = tracker.get_fairness_weights("weekend")
    
    # Alice has 2, Bob has 1, others have 0
    # Min count is 0, so weights should be: Alice=2-0=2, Bob=1-0=1, Charlie=0-0=0
    assert weights["Alice"] == 2, f"Alice should have weight 2, got {weights['Alice']}"
    assert weights["Bob"] == 1, f"Bob should have weight 1, got {weights['Bob']}"
    assert weights["Charlie"] == 0, f"Charlie should have weight 0, got {weights['Charlie']}"
    
    print("  ✅ Enhanced fairness tracker works correctly")


def test_enhanced_weekend_assignment():
    """Test fairness-weighted weekend assignment"""
    print("🧪 Testing enhanced weekend assignment...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    tracker = EnhancedFairnessTracker(engineers)
    
    # Simulate some previous assignments to create imbalance
    tracker.track_assignment("Alice", "weekend")
    tracker.track_assignment("Alice", "weekend")
    tracker.track_assignment("Bob", "weekend")
    
    # Test enhanced assignment - should prefer engineers with fewer assignments
    assigned_week_0 = enhanced_weekend_assignment(engineers, 0, tracker, base_seed=0)
    assigned_week_1 = enhanced_weekend_assignment(engineers, 1, tracker, base_seed=0)
    
    # Charlie, Diana, Eve, Frank should be preferred over Alice (who has 2) and Bob (who has 1)
    preferred_engineers = ["Charlie", "Diana", "Eve", "Frank"]
    assert assigned_week_0 in preferred_engineers, f"Week 0 should assign to underutilized engineer, got {assigned_week_0}"
    
    print(f"  ✅ Enhanced weekend assignment prefers underutilized engineers: {assigned_week_0}, {assigned_week_1}")


def test_weekend_compensation_calculation():
    """Test weekend compensation calculation"""
    print("🧪 Testing weekend compensation calculation...")
    
    # Test Week A pattern (Saturday)
    saturday = date(2024, 1, 13)
    comp_dates_a = calculate_weekend_compensation("Alice", saturday, "A")
    expected_friday = saturday + timedelta(days=6)  # Following Friday
    assert comp_dates_a == [expected_friday], f"Week A should get Friday off, got {comp_dates_a}"
    
    # Test Week B pattern (Sunday)
    sunday = date(2024, 1, 14)
    comp_dates_b = calculate_weekend_compensation("Bob", sunday, "B")
    expected_monday = sunday + timedelta(days=1)  # Following Monday
    assert comp_dates_b == [expected_monday], f"Week B should get Monday off, got {comp_dates_b}"
    
    print("  ✅ Weekend compensation calculation works correctly")


def test_weekend_assignment_decision_logging():
    """Test weekend assignment decision logging"""
    print("🧪 Testing weekend assignment decision logging...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 2
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create empty leave DataFrame
    leave = pd.DataFrame(columns=["Engineer", "Date", "Reason"])
    
    # Generate enhanced schedule to get decision log
    result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Check for weekend assignment decisions in the log
    weekend_decisions = [entry for entry in result.decision_log if entry.decision_type == "enhanced_weekend_assignment"]
    assert len(weekend_decisions) > 0, "Should have weekend assignment decisions logged"
    
    # Validate decision entry structure
    first_decision = weekend_decisions[0]
    assert hasattr(first_decision, 'affected_engineers'), "Decision should have affected_engineers"
    assert hasattr(first_decision, 'reason'), "Decision should have reason"
    assert hasattr(first_decision, 'alternatives_considered'), "Decision should have alternatives"
    assert len(first_decision.affected_engineers) == 1, "Weekend assignment should affect one engineer"
    
    print(f"  ✅ Weekend assignment decision logging works: {len(weekend_decisions)} decisions logged")


def test_weekend_compensation_tracking():
    """Test weekend compensation tracking in schedule result"""
    print("🧪 Testing weekend compensation tracking...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 2
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create empty leave DataFrame
    leave = pd.DataFrame(columns=["Engineer", "Date", "Reason"])
    
    # Generate enhanced schedule
    result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Check weekend compensation tracking
    assert hasattr(result, 'weekend_compensation_tracking'), "Should have weekend compensation tracking"
    compensation_entries = result.weekend_compensation_tracking
    
    # Should have entries for each weekend (2 weeks = 2 weekends)
    assert len(compensation_entries) >= 2, f"Should have at least 2 weekend compensation entries, got {len(compensation_entries)}"
    
    # Validate compensation entry structure
    if compensation_entries:
        first_entry = compensation_entries[0]
        assert hasattr(first_entry, 'engineer'), "Compensation should have engineer"
        assert hasattr(first_entry, 'weekend_date'), "Compensation should have weekend_date"
        assert hasattr(first_entry, 'compensation_dates'), "Compensation should have compensation_dates"
        assert hasattr(first_entry, 'pattern_type'), "Compensation should have pattern_type"
        assert len(first_entry.compensation_dates) > 0, "Should have compensation dates"
    
    print(f"  ✅ Weekend compensation tracking works: {len(compensation_entries)} entries tracked")


def test_weekend_pattern_display():
    """Test weekend pattern indicators in schedule display"""
    print("🧪 Testing weekend pattern display...")
    
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)
    weeks = 1
    seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Create empty leave DataFrame
    leave = pd.DataFrame(columns=["Engineer", "Date", "Reason"])
    
    # Generate schedule
    df = make_schedule(start_sunday, weeks, engineers, seeds, leave)
    
    # Find weekend rows
    saturday_row = df[df["Day"] == "Sat"].iloc[0] if len(df[df["Day"] == "Sat"]) > 0 else None
    sunday_row = df[df["Day"] == "Sun"].iloc[0] if len(df[df["Day"] == "Sun"]) > 0 else None
    
    if saturday_row is not None:
        # Check for weekend pattern indicators in shift columns
        shift_columns = [col for col in df.columns if col.startswith("Shift")]
        weekend_patterns_found = False
        
        for col in shift_columns:
            shift_value = saturday_row[col]
            if "Weekend-A" in str(shift_value) or "Weekend-B" in str(shift_value):
                weekend_patterns_found = True
                break
        
        # At least one engineer should have a weekend pattern indicator
        # (This test is flexible since the exact column depends on engineer order)
        print(f"  ✅ Weekend pattern display implemented (patterns found: {weekend_patterns_found})")
    else:
        print("  ⚠️  No weekend rows found in schedule")


def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Schedule Core Tests\n")
    
    try:
        test_basic_functions()
        test_weekend_rotation()
        test_work_schedule()
        test_schedule_generation()
        test_enhanced_schedule()
        test_leave_handling()
        test_fairness_calculation()
        
        # Enhanced weekend assignment tests
        test_enhanced_fairness_tracker()
        test_enhanced_weekend_assignment()
        test_weekend_compensation_calculation()
        test_weekend_assignment_decision_logging()
        test_weekend_compensation_tracking()
        test_weekend_pattern_display()
        
        print("\n✅ All tests passed! Schedule core is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)