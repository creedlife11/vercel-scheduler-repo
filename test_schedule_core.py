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
    make_schedule, calculate_fairness_report, make_enhanced_schedule
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
    monday = date(2024, 1, 8)
    tuesday = date(2024, 1, 9)
    saturday = date(2024, 1, 13)
    sunday = date(2024, 1, 14)
    
    # A (weekend worker) should work Mon,Tue,Wed,Thu,Sat
    assert works_today("A", monday, start_sunday, weekend_seeded) == True
    assert works_today("A", saturday, start_sunday, weekend_seeded) == True
    assert works_today("A", sunday, start_sunday, weekend_seeded) == False
    
    # B (previous week's weekend worker, but week -1 wraps to F) should work normal weekdays
    assert works_today("B", monday, start_sunday, weekend_seeded) == True
    assert works_today("B", saturday, start_sunday, weekend_seeded) == False
    
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
    assert metadata.total_engineers == 6, "Should have 6 engineers"
    assert metadata.total_weeks == weeks, f"Should have {weeks} weeks"
    
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