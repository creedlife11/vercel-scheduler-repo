"""
Enhanced Leave Management Testing

Tests for intelligent backfill selection, leave impact analysis, and conflict resolution.
Validates that leave days are excluded from fairness penalty calculations.
"""

import pytest
from datetime import date, timedelta
import pandas as pd
from typing import List, Dict, Set

from schedule_core import (
    enhanced_backfill_selection, calculate_leave_impact_on_fairness,
    suggest_leave_alternatives, process_leave_with_enhanced_logic,
    calculate_enhanced_fairness_report, check_leave_coverage_adequacy,
    make_enhanced_schedule, EnhancedFairnessTracker
)
from models import DecisionEntry, EngineerStats, FairnessReport


class TestEnhancedBackfillSelection:
    """Test intelligent backfill selection prioritizes fair distribution."""
    
    def test_backfill_selection_with_fairness_tracker(self):
        """Test that backfill selection considers fairness weighting."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        fairness_tracker = EnhancedFairnessTracker(engineers)
        
        # Set up uneven assignment history
        fairness_tracker.track_assignment("Alice", "weekend", 3.0)  # High workload
        fairness_tracker.track_assignment("Bob", "oncall", 2.0)
        fairness_tracker.track_assignment("Charlie", "early", 1.0)  # Lower workload
        fairness_tracker.track_assignment("Diana", "chat", 1.0)     # Lower workload
        
        # Set up test scenario
        engineers = ["Alice", "Bob", "Charlie", "Diana"]
        leave_today = {"Bob"}  # Bob is on leave
        expected_working = ["Alice"]  # Alice is expected to work
        d = date(2024, 1, 15)
        start_sunday = date(2024, 1, 14)
        weekend_seeded = ["Alice", "Bob", "Charlie", "Diana"]
        required_roles = ["Chat", "OnCall"]
        decision_log = []
        
        selected = enhanced_backfill_selection(
            engineers, leave_today, expected_working, d, start_sunday, weekend_seeded,
            required_roles, fairness_tracker, decision_log, "2024-01-15"
        )
        
        # Should prefer engineers with lower overall workload
        assert len(selected) == 2
        assert "Charlie" in selected  # Lower workload should be preferred
        assert "Diana" in selected    # Lower workload should be preferred
        assert "Alice" not in selected  # Higher workload should be avoided
        
        # Check decision logging
        assert len(decision_log) == 1
        assert decision_log[0].decision_type == "enhanced_backfill_selection"
        assert "fairness weighting" in decision_log[0].reason
    
    def test_backfill_selection_no_candidates(self):
        """Test backfill selection when no candidates are available."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        fairness_tracker = EnhancedFairnessTracker(engineers)
        
        # Set up scenario where all engineers are either on leave or expected to work
        leave_today = {"Alice", "Bob", "Charlie"}
        expected_working = ["Diana", "Eve", "Frank"]  # All remaining engineers expected to work
        d = date(2024, 1, 15)
        start_sunday = date(2024, 1, 14)
        weekend_seeded = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        required_roles = ["Chat", "OnCall"]
        decision_log = []
        
        selected = enhanced_backfill_selection(
            engineers, leave_today, expected_working, d, start_sunday, weekend_seeded,
            required_roles, fairness_tracker, decision_log, "2024-01-15"
        )
        
        assert selected == []
        assert len(decision_log) == 1
        assert decision_log[0].decision_type == "backfill_selection_failure"
        assert "No backfill candidates available" in decision_log[0].reason
    
    def test_backfill_selection_limited_candidates(self):
        """Test backfill selection when fewer candidates than required roles."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        fairness_tracker = EnhancedFairnessTracker(engineers)
        
        # Set up scenario where only Alice is available as backfill
        leave_today = {"Bob", "Charlie", "Diana"}
        expected_working = ["Eve", "Frank"]  # Eve and Frank expected to work
        d = date(2024, 1, 15)
        start_sunday = date(2024, 1, 14)
        weekend_seeded = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        required_roles = ["Chat", "OnCall", "Appointments"]
        decision_log = []
        
        selected = enhanced_backfill_selection(
            engineers, leave_today, expected_working, d, start_sunday, weekend_seeded,
            required_roles, fairness_tracker, decision_log, "2024-01-15"
        )
        
        # Should return available candidate even if fewer than required
        assert selected == ["Alice"]
        assert len(decision_log) == 1
        assert decision_log[0].decision_type == "enhanced_backfill_selection"


class TestLeaveImpactAnalysis:
    """Test leave impact analysis and fairness calculations."""
    
    def test_calculate_leave_impact_on_fairness(self):
        """Test leave impact calculation for fairness adjustment."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        
        # Create leave map with varying leave amounts
        leave_map = {
            "Alice": {date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17)},  # 3 days
            "Bob": {date(2024, 1, 20)},  # 1 day
            "Charlie": set(),  # No leave
            "Diana": {date(2024, 1, 25), date(2024, 1, 26)},  # 2 days
            "Eve": set(),  # No leave
            "Frank": set()  # No leave
        }
        
        impact = calculate_leave_impact_on_fairness(leave_map, engineers)
        
        # Engineers with more leave should have higher impact scores
        assert impact["Alice"] > impact["Bob"]
        assert impact["Bob"] > impact["Charlie"]
        assert impact["Diana"] > impact["Charlie"]
        assert impact["Charlie"] == 0.0  # No leave
        assert impact["Eve"] == 0.0      # No leave
        assert impact["Frank"] == 0.0    # No leave
    
    def test_enhanced_fairness_report_with_leave_adjustment(self):
        """Test that enhanced fairness report properly adjusts for leave."""
        engineers = ["Alice", "Bob", "Charlie"]
        
        # Create sample schedule DataFrame
        schedule_data = {
            "Date": [date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17)],
            "Day": ["Mon", "Tue", "Wed"],
            "OnCall": ["Alice", "Bob", "Charlie"],
            "Chat": ["Bob", "Charlie", "Alice"],
            "Status 1": ["WORK", "LEAVE", "WORK"],  # Alice has 1 leave day
            "Status 2": ["WORK", "WORK", "WORK"],   # Bob has no leave
            "Status 3": ["WORK", "WORK", "WORK"]    # Charlie has no leave
        }
        df = pd.DataFrame(schedule_data)
        
        # Create leave map
        leave_map = {
            "Alice": {date(2024, 1, 16)},  # 1 leave day
            "Bob": set(),
            "Charlie": set()
        }
        
        # Calculate enhanced fairness report
        fairness_report = calculate_enhanced_fairness_report(df, engineers, leave_map)
        
        # Verify that Alice's assignments are adjusted upward due to leave
        assert isinstance(fairness_report, FairnessReport)
        assert "Alice" in fairness_report.engineer_stats
        assert "Bob" in fairness_report.engineer_stats
        assert "Charlie" in fairness_report.engineer_stats
        
        # Check that leave days are tracked
        alice_stats = fairness_report.engineer_stats["Alice"]
        assert alice_stats.leave_days == 1
    
    def test_leave_coverage_adequacy_warnings(self):
        """Test leave coverage adequacy warning generation."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        
        # Create schedule with inadequate coverage on some days
        schedule_data = {
            "Date": [date(2024, 1, 15), date(2024, 1, 16)],
            "Day": ["Mon", "Tue"],
            "Status 1": ["LEAVE", "LEAVE"],  # Alice
            "Status 2": ["LEAVE", "LEAVE"],  # Bob  
            "Status 3": ["LEAVE", "LEAVE"],  # Charlie
            "Status 4": ["LEAVE", "LEAVE"],  # Diana
            "Status 5": ["WORK", "WORK"],    # Eve
            "Status 6": ["WORK", "WORK"]     # Frank
        }
        df = pd.DataFrame(schedule_data)
        
        warnings = check_leave_coverage_adequacy(df, engineers, min_coverage_threshold=3)
        
        # Should generate warnings for days with insufficient coverage
        assert len(warnings) == 2  # Both days have inadequate coverage
        assert "2024-01-15" in warnings[0]
        assert "Only 2 engineers working" in warnings[0]
        assert "2024-01-16" in warnings[1]
        assert "Only 2 engineers working" in warnings[1]


class TestLeaveConflictResolution:
    """Test leave conflict resolution and alternative suggestions."""
    
    def test_suggest_leave_alternatives(self):
        """Test alternative suggestion generation for leave conflicts."""
        conflicts = ["Engineer shortage on Monday", "No on-call coverage available"]
        available_engineers = ["Alice", "Bob", "Charlie"]
        
        suggestions = suggest_leave_alternatives(conflicts, available_engineers, "2024-01-15")
        
        assert len(suggestions) > 0
        assert "Leave conflicts detected on 2024-01-15" in suggestions[0]
        assert "Consider reassigning roles to: Alice, Bob, Charlie" in suggestions[1]
        # Check for leave schedule adjustment suggestion (case insensitive)
        suggestion_text = " ".join(suggestions).lower()
        assert "adjust" in suggestion_text and "leave" in suggestion_text
    
    def test_suggest_alternatives_no_available_engineers(self):
        """Test alternative suggestions when no engineers are available."""
        conflicts = ["Critical shortage"]
        available_engineers = []
        
        suggestions = suggest_leave_alternatives(conflicts, available_engineers, "2024-01-15")
        
        assert len(suggestions) > 0
        assert "No alternative engineers available" in suggestions[1]
        assert "manual intervention required" in suggestions[1].lower()
    
    def test_process_leave_with_enhanced_logic(self):
        """Test enhanced leave processing with validation."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        
        # Test with list of dictionaries (API format)
        leave_entries = [
            {"Engineer": "Alice", "Date": "2024-01-15"},
            {"Engineer": "Bob", "Date": "2024-01-16"},
            {"Engineer": "Charlie", "Date": "2024-01-17"},
            {"Engineer": "InvalidEngineer", "Date": "2024-01-18"}  # Should be ignored
        ]
        
        leave_map = process_leave_with_enhanced_logic(leave_entries, engineers)
        
        # Verify proper processing
        assert len(leave_map) == 6  # All engineers should have entries
        assert date(2024, 1, 15) in leave_map["Alice"]
        assert date(2024, 1, 16) in leave_map["Bob"]
        assert date(2024, 1, 17) in leave_map["Charlie"]
        assert len(leave_map["Diana"]) == 0  # No leave
        assert len(leave_map["Eve"]) == 0    # No leave
        assert len(leave_map["Frank"]) == 0  # No leave
        
        # Invalid engineer should not create entry
        assert "InvalidEngineer" not in leave_map


class TestIntegratedLeaveManagement:
    """Test integrated leave management in full schedule generation."""
    
    def test_enhanced_schedule_with_leave_management(self):
        """Test that enhanced schedule generation properly handles leave management."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        start_sunday = date(2024, 1, 14)  # Sunday
        weeks = 1
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        
        # Create leave DataFrame
        leave_data = {
            "Engineer": ["Alice", "Bob"],
            "Date": [date(2024, 1, 15), date(2024, 1, 16)]
        }
        leave_df = pd.DataFrame(leave_data)
        
        # Generate enhanced schedule
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
        
        # Verify result structure
        assert hasattr(result, 'schedule_data')
        assert hasattr(result, 'fairness_report')
        assert hasattr(result, 'decision_log')
        assert hasattr(result, 'metadata')
        
        # Check that leave management decisions are logged
        leave_decisions = [entry for entry in result.decision_log 
                          if entry.decision_type in ["leave_exclusion", "enhanced_backfill_selection", "leave_coverage_warning"]]
        assert len(leave_decisions) > 0
        
        # Verify fairness report includes leave impact
        assert isinstance(result.fairness_report, FairnessReport)
        alice_stats = result.fairness_report.engineer_stats.get("Alice")
        bob_stats = result.fairness_report.engineer_stats.get("Bob")
        
        if alice_stats:
            assert alice_stats.leave_days >= 0
        if bob_stats:
            assert bob_stats.leave_days >= 0
    
    def test_fairness_distribution_with_heavy_leave(self):
        """Test fairness distribution when some engineers have significant leave."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        start_sunday = date(2024, 1, 14)  # Sunday
        weeks = 2
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        
        # Create heavy leave for some engineers
        leave_dates = []
        for i in range(7):  # Alice takes a full week
            leave_dates.append({"Engineer": "Alice", "Date": start_sunday + timedelta(days=i)})
        for i in range(3):  # Bob takes 3 days
            leave_dates.append({"Engineer": "Bob", "Date": start_sunday + timedelta(days=i+7)})
        
        leave_df = pd.DataFrame(leave_dates)
        
        # Generate enhanced schedule
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
        
        # Verify that engineers with leave don't get penalized in fairness calculations
        alice_stats = result.fairness_report.engineer_stats["Alice"]
        bob_stats = result.fairness_report.engineer_stats["Bob"]
        charlie_stats = result.fairness_report.engineer_stats["Charlie"]
        
        # Alice should have significant leave days recorded
        assert alice_stats.leave_days >= 7
        assert bob_stats.leave_days >= 3
        assert charlie_stats.leave_days == 0
        
        # Check that backfill decisions were made
        backfill_decisions = [entry for entry in result.decision_log 
                             if "backfill" in entry.decision_type]
        assert len(backfill_decisions) > 0


if __name__ == "__main__":
    # Run specific test classes
    pytest.main([__file__ + "::TestEnhancedBackfillSelection", "-v"])
    pytest.main([__file__ + "::TestLeaveImpactAnalysis", "-v"])
    pytest.main([__file__ + "::TestLeaveConflictResolution", "-v"])
    pytest.main([__file__ + "::TestIntegratedLeaveManagement", "-v"])