"""
Test suite for enhanced daily role assignment functionality.
Tests fairness weighting, conflict handling, and decision logging accuracy.
"""

import pytest
from datetime import date, timedelta
from typing import List, Dict
import pandas as pd

from schedule_core import (
    generate_day_assignments, 
    enhanced_role_assignment,
    get_role_rotation_order,
    handle_engineer_unavailability,
    get_alternative_selection_candidates,
    EnhancedFairnessTracker,
    build_rotation,
    is_weekday
)
from models import DecisionEntry


class TestEnhancedDailyRoleAssignment:
    """Test enhanced daily role assignment functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.start_sunday = date(2024, 1, 7)  # A Sunday
        self.seeds = {"chat": 0, "oncall": 1, "appointments": 2, "early": 0, "weekend": 0}
        self.weekend_seeded = build_rotation(self.engineers, self.seeds["weekend"])
        self.fairness_tracker = EnhancedFairnessTracker(self.engineers)
        
    def test_fairness_weighting_in_daily_role_selection(self):
        """Test that fairness weighting affects daily role selection."""
        # Pre-load fairness tracker with some assignments to create imbalance
        self.fairness_tracker.track_assignment("Alice", "chat", 3)  # Alice has more chat assignments
        self.fairness_tracker.track_assignment("Bob", "chat", 1)    # Bob has fewer
        
        available_engineers = ["Alice", "Bob", "Charlie"]
        decision_log = []
        
        # Test chat assignment with fairness weighting
        selected = enhanced_role_assignment(
            available_engineers, "chat", self.engineers, self.seeds, 0, "2024-01-08",
            decision_log, self.fairness_tracker
        )
        
        # Bob should be preferred due to lower assignment count
        fairness_weights = self.fairness_tracker.get_fairness_weights("chat")
        assert fairness_weights["Bob"] < fairness_weights["Alice"], "Bob should have lower fairness weight"
        
        # Verify decision logging includes fairness information
        assert len(decision_log) == 1
        assert "fairness weighting" in decision_log[0].reason
        assert selected in decision_log[0].affected_engineers
        
    def test_role_rotation_order_with_fairness(self):
        """Test get_role_rotation_order function with fairness consideration."""
        # Create imbalanced assignment history
        self.fairness_tracker.track_assignment("Alice", "appointments", 2)
        self.fairness_tracker.track_assignment("Bob", "appointments", 0)
        self.fairness_tracker.track_assignment("Charlie", "appointments", 1)
        
        available = ["Alice", "Bob", "Charlie"]
        
        # Test without fairness tracker (should use standard rotation)
        standard_order = get_role_rotation_order(
            self.engineers, "appointments", 2, 0, available, None
        )
        
        # Test with fairness tracker (should prioritize Bob who has 0 assignments)
        fairness_order = get_role_rotation_order(
            self.engineers, "appointments", 2, 0, available, self.fairness_tracker
        )
        
        # Bob should be first in fairness order due to 0 assignments
        assert fairness_order[0] == "Bob", f"Expected Bob first, got {fairness_order[0]}"
        
        # Orders should be different when fairness is considered
        assert standard_order != fairness_order, "Fairness should change rotation order"
        
    def test_engineer_unavailability_handling(self):
        """Test improved conflict handling for unavailable engineers."""
        expected_engineers = ["Alice", "Bob", "Charlie", "Diana"]
        unavailable_engineers = ["Alice", "Charlie"]  # On leave
        decision_log = []
        
        available = handle_engineer_unavailability(
            expected_engineers, unavailable_engineers, "chat", "2024-01-08", decision_log
        )
        
        # Should return only available engineers
        assert available == ["Bob", "Diana"]
        
        # Should log the unavailability
        assert len(decision_log) == 1
        assert decision_log[0].decision_type == "chat_unavailability_handling"
        assert set(decision_log[0].affected_engineers) == set(unavailable_engineers)
        assert "Bob" in decision_log[0].alternatives_considered[0] or "Diana" in decision_log[0].alternatives_considered[0]
        
    def test_alternative_selection_candidates(self):
        """Test generation of alternative candidates for role assignments."""
        rotation_order = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
        selected_engineer = "Bob"
        
        alternatives = get_alternative_selection_candidates(rotation_order, selected_engineer, 3)
        
        # Should return next 3 engineers in rotation order
        expected = ["Charlie", "Diana", "Eve"]
        assert alternatives == expected
        
        # Test wrap-around when selected is near end
        selected_engineer = "Eve"
        alternatives = get_alternative_selection_candidates(rotation_order, selected_engineer, 3)
        expected = ["Alice", "Bob", "Charlie"]  # Wraps around to beginning
        assert alternatives == expected
        
    def test_daily_role_assignment_decision_logging_accuracy(self):
        """Test that daily role assignment decision logging is accurate and complete."""
        monday = self.start_sunday + timedelta(days=1)  # Monday
        leave_map = {"Alice": set()}  # No one on leave
        for eng in self.engineers:
            leave_map.setdefault(eng, set())
        
        decision_log = []
        
        working, leave_today, roles = generate_day_assignments(
            monday, self.engineers, self.start_sunday, self.weekend_seeded,
            leave_map, self.seeds, False, decision_log, self.fairness_tracker
        )
        
        # Should have decision entries for each role assignment
        role_assignments = [entry for entry in decision_log if "assignment" in entry.decision_type]
        
        # Should have entries for chat, oncall, appointments, and early shift assignments
        decision_types = [entry.decision_type for entry in role_assignments]
        
        assert any("chat" in dt for dt in decision_types), "Should have chat assignment decision"
        assert any("oncall" in dt for dt in decision_types), "Should have oncall assignment decision"
        assert any("appointments" in dt for dt in decision_types), "Should have appointments assignment decision"
        assert any("early" in dt for dt in decision_types), "Should have early shift assignment decision"
        
        # Each decision should have proper structure
        for entry in role_assignments:
            assert entry.date == monday.isoformat()
            assert len(entry.affected_engineers) > 0
            assert entry.reason != ""
            assert isinstance(entry.alternatives_considered, list)
            
    def test_fairness_tracker_role_distribution_summary(self):
        """Test fairness tracker's role distribution summary functionality."""
        # Create some assignments
        self.fairness_tracker.track_assignment("Alice", "chat", 1)
        self.fairness_tracker.track_assignment("Bob", "chat", 2)
        self.fairness_tracker.track_assignment("Charlie", "chat", 1)
        
        self.fairness_tracker.track_assignment("Alice", "oncall", 1)
        self.fairness_tracker.track_assignment("Diana", "oncall", 3)
        
        summary = self.fairness_tracker.get_role_distribution_summary()
        
        # Check chat role summary
        assert summary["chat"]["total_assignments"] == 4
        assert summary["chat"]["min_assignments"] == 0  # Some engineers have 0
        assert summary["chat"]["max_assignments"] == 2  # Bob has 2
        assert summary["chat"]["range"] == 2
        
        # Check oncall role summary
        assert summary["oncall"]["total_assignments"] == 4
        assert summary["oncall"]["max_assignments"] == 3  # Diana has 3
        
    def test_fairness_improvement_suggestions(self):
        """Test generation of fairness improvement suggestions."""
        # Create significant imbalance
        self.fairness_tracker.track_assignment("Alice", "chat", 5)  # High
        self.fairness_tracker.track_assignment("Bob", "chat", 1)    # Low
        self.fairness_tracker.track_assignment("Charlie", "chat", 1) # Low
        
        suggestions = self.fairness_tracker.suggest_fairness_improvements()
        
        # Should suggest rebalancing
        assert len(suggestions) > 0
        suggestion_text = " ".join(suggestions)
        assert "Alice" in suggestion_text  # Should mention high-assignment engineer
        assert "chat" in suggestion_text   # Should mention the imbalanced role
        
    def test_enhanced_role_assignment_with_no_available_engineers(self):
        """Test enhanced role assignment when no engineers are available."""
        available_engineers = []
        decision_log = []
        
        selected = enhanced_role_assignment(
            available_engineers, "chat", self.engineers, self.seeds, 0, "2024-01-08",
            decision_log, self.fairness_tracker
        )
        
        # Should return empty string
        assert selected == ""
        
        # Should log the failure
        assert len(decision_log) == 1
        assert decision_log[0].decision_type == "chat_assignment_failure"
        assert "No engineers available" in decision_log[0].reason
        assert "Manual assignment required" in decision_log[0].alternatives_considered
        
    def test_weekend_vs_weekday_role_assignment_differences(self):
        """Test that role assignments differ appropriately between weekends and weekdays."""
        monday = self.start_sunday + timedelta(days=1)  # Monday (weekday)
        saturday = self.start_sunday + timedelta(days=6)  # Saturday (weekend)
        
        leave_map = {eng: set() for eng in self.engineers}
        decision_log_weekday = []
        decision_log_weekend = []
        
        # Generate assignments for weekday
        working_wd, _, roles_wd = generate_day_assignments(
            monday, self.engineers, self.start_sunday, self.weekend_seeded,
            leave_map, self.seeds, False, decision_log_weekday, self.fairness_tracker
        )
        
        # Generate assignments for weekend
        working_we, _, roles_we = generate_day_assignments(
            saturday, self.engineers, self.start_sunday, self.weekend_seeded,
            leave_map, self.seeds, False, decision_log_weekend, self.fairness_tracker
        )
        
        # Weekday should have chat, oncall, appointments assignments
        assert roles_wd["Chat"] != ""
        assert roles_wd["OnCall"] != ""
        assert roles_wd["Appointments"] != ""
        
        # Weekend should not have these roles (or they should be empty)
        assert roles_we["Chat"] == ""
        assert roles_we["OnCall"] == ""
        assert roles_we["Appointments"] == ""
        
        # Decision logs should reflect different assignment types
        weekday_types = [entry.decision_type for entry in decision_log_weekday]
        weekend_types = [entry.decision_type for entry in decision_log_weekend]
        
        assert any("chat" in dt for dt in weekday_types)
        assert not any("chat" in dt for dt in weekend_types)
        
    def test_fairness_weights_calculation_accuracy(self):
        """Test that fairness weights are calculated correctly."""
        # Set up specific assignment counts
        self.fairness_tracker.assignment_history["Alice"]["chat"] = 3
        self.fairness_tracker.assignment_history["Bob"]["chat"] = 1
        self.fairness_tracker.assignment_history["Charlie"]["chat"] = 2
        self.fairness_tracker.assignment_history["Diana"]["chat"] = 1
        self.fairness_tracker.assignment_history["Eve"]["chat"] = 0
        self.fairness_tracker.assignment_history["Frank"]["chat"] = 1
        
        weights = self.fairness_tracker.get_fairness_weights("chat")
        
        # Weights should be relative to minimum (Eve has 0, so min = 0)
        assert weights["Eve"] == 0      # Minimum assignments
        assert weights["Bob"] == 1      # 1 - 0 = 1
        assert weights["Charlie"] == 2  # 2 - 0 = 2
        assert weights["Alice"] == 3    # 3 - 0 = 3 (highest weight, lowest preference)
        
        # Engineers with same count should have same weight
        assert weights["Bob"] == weights["Diana"] == weights["Frank"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])