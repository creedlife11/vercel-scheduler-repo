"""
Integration test to verify enhanced on-call assignment works with full schedule generation.
"""

from datetime import date, timedelta
import pandas as pd
from schedule_core import make_schedule_with_decisions, build_rotation, weekend_worker_for_week, week_index


def test_oncall_integration():
    """Test that enhanced on-call logic integrates properly with full schedule generation."""
    
    # Test setup
    engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    start_sunday = date(2024, 1, 7)  # A Sunday
    weeks = 2
    seeds = {"weekend": 0, "oncall": 1, "chat": 0, "appointments": 2, "early": 0}
    leave_df = pd.DataFrame()  # No leave for this test
    
    # Generate schedule with decision logging
    df, decision_log, weekend_compensation = make_schedule_with_decisions(
        start_sunday, weeks, engineers, seeds, leave_df, assign_early_on_weekends=False
    )
    
    # Verify weekend rotation
    weekend_seeded = build_rotation(engineers, seeds["weekend"])
    print(f"Weekend rotation: {weekend_seeded}")
    
    # Check on-call assignments for weekdays
    weekday_oncall_decisions = [d for d in decision_log if d.decision_type in ["oncall_assignment", "enhanced_oncall_assignment"]]
    
    print(f"\nFound {len(weekday_oncall_decisions)} on-call assignment decisions")
    
    # Analyze on-call assignments vs weekend workers
    weekend_worker_avoided_count = 0
    total_weekday_oncall = 0
    
    for _, row in df.iterrows():
        if row["Day"] in ["Mon", "Tue", "Wed", "Thu", "Fri"]:  # Weekdays only
            oncall_engineer = row["OnCall"]
            if oncall_engineer:  # If someone is assigned on-call
                total_weekday_oncall += 1
                current_week = week_index(start_sunday, row["Date"])
                weekend_worker = weekend_worker_for_week(weekend_seeded, current_week)
                
                # Check if we avoided the weekend worker
                if oncall_engineer != weekend_worker:
                    weekend_worker_avoided_count += 1
                
                print(f"{row['Date']} ({row['Day']}): OnCall={oncall_engineer}, WeekendWorker={weekend_worker}, Avoided={oncall_engineer != weekend_worker}")
    
    # Calculate avoidance rate
    avoidance_rate = weekend_worker_avoided_count / total_weekday_oncall if total_weekday_oncall > 0 else 0
    print(f"\nWeekend worker avoidance rate: {avoidance_rate:.2%} ({weekend_worker_avoided_count}/{total_weekday_oncall})")
    
    # Verify decision logging
    print(f"\nDecision log entries: {len(decision_log)}")
    oncall_decisions = [d for d in decision_log if "oncall" in d.decision_type.lower()]
    print(f"On-call related decisions: {len(oncall_decisions)}")
    
    # Print some sample decision entries
    for i, decision in enumerate(oncall_decisions[:3]):
        print(f"\nDecision {i+1}:")
        print(f"  Date: {decision.date}")
        print(f"  Type: {decision.decision_type}")
        print(f"  Engineer: {decision.affected_engineers}")
        print(f"  Reason: {decision.reason}")
        print(f"  Alternatives: {decision.alternatives_considered}")
    
    # Assertions
    assert total_weekday_oncall > 0, "Should have on-call assignments on weekdays"
    assert len(oncall_decisions) > 0, "Should have on-call decision log entries"
    assert avoidance_rate >= 0.5, f"Should avoid weekend workers at least 50% of the time, got {avoidance_rate:.2%}"
    
    print(f"\n✅ Integration test passed! Enhanced on-call logic is working correctly.")


if __name__ == "__main__":
    test_oncall_integration()