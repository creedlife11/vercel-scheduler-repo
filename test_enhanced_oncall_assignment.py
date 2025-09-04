"""
Test suite for enhanced on-call assignment logic.
Tests weekend worker avoidance, fallback behavior, and decision logging accuracy.
"""

import pytest
from datetime import date, timedelta
from schedule_core import (
    should_avoid_weekend_worker, 
    enhanced_oncall_selection,
    build_rotation,
    week_index,
    weekend_worker_for_week
)
from models import DecisionEntry


class TestWeekendWorkerAvoidance:
    """Test the should_avoid_weekend_worker helper function."""
    
    def setup_method(self):
        """Set up test data."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.start_sunday = date(2024, 1, 7)  # A Sunday
        self.weekend_seeded = build_rotation(self.engineers, 0)  # No seed offset
    
    def test_avoids_current_weekend_worker(self):
        """Test that current week's weekend worker is avoided."""
        # Week 0 (Jan 7-13): Alice works weekend
        monday = self.start_sunday + timedelta(days=1)  # Jan 8
        
        # Alice should be avoided on Monday since she works weekend this week
        assert should_avoid_weekend_worker("Alice", monday, self.start_sunday, self.weekend_seeded) == True
        
        # Other engineers should not be avoided
        assert should_avoid_weekend_worker("Bob", monday, self.start_sunday, self.weekend_seeded) == False
        assert should_avoid_weekend_worker("Charlie", monday, self.start_sunday, self.weekend_seeded) == False
    
    def test_avoids_next_weekend_worker_on_friday(self):
        """Test that next week's weekend worker is avoided on Friday."""
        # Week 0: Alice works weekend, Week 1: Bob works weekend
        friday = self.start_sunday + timedelta(days=5)  # Jan 12 (Friday)
        
        # Both Alice (current) and Bob (next) should be avoided on Friday
        assert should_avoid_weekend_worker("Alice", friday, self.start_sunday, self.weekend_seeded) == True
        assert should_avoid_weekend_worker("Bob", friday, self.start_sunday, self.weekend_seeded) == True
        
        # Other engineers should not be avoided
        assert should_avoid_weekend_worker("Charlie", friday, self.start_sunday, self.weekend_seeded) == False
    
    def test_does_not_avoid_next_weekend_worker_on_other_days(self):
        """Test that next week's weekend worker is only avoided on Friday."""
        # Week 0: Alice works weekend, Week 1: Bob works weekend
        tuesday = self.start_sunday + timedelta(days=2)  # Jan 9 (Tuesday)
        
        # Only Alice (current weekend worker) should be avoided on Tuesday
        assert should_avoid_weekend_worker("Alice", tuesday, self.start_sunday, self.weekend_seeded) == True
        assert should_avoid_weekend_worker("Bob", tuesday, self.start_sunday, self.weekend_seeded) == False
    
    def test_weekend_rotation_progression(self):
        """Test avoidance logic across multiple weeks."""
        # Week 0: Alice, Week 1: Bob, Week 2: Charlie
        week1_monday = self.start_sunday + timedelta(days=8)  # Jan 15
        week2_monday = self.start_sunday + timedelta(days=15)  # Jan 22
        
        # Week 1: Bob should be avoided, Alice should not
        assert should_avoid_weekend_worker("Bob", week1_monday, self.start_sunday, self.weekend_seeded) == True
        assert should_avoid_weekend_worker("Alice", week1_monday, self.start_sunday, self.weekend_seeded) == False
        
        # Week 2: Charlie should be avoided, Bob should not
        assert should_avoid_weekend_worker("Charlie", week2_monday, self.start_sunday, self.weekend_seeded) == True
        assert should_avoid_weekend_worker("Bob", week2_monday, self.start_sunday, self.weekend_seeded) == False


class TestEnhancedOnCallSelection:
    """Test the enhanced_oncall_selection function."""
    
    def setup_method(self):
        """Set up test data."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.start_sunday = date(2024, 1, 7)  # A Sunday
        self.weekend_seeded = build_rotation(self.engineers, 0)
        self.seeds = {"oncall": 1, "chat": 0, "appointments": 2, "early": 0, "weekend": 0}
        self.decision_log = []
    
    def test_prefers_non_weekend_workers(self):
        """Test that non-weekend workers are preferred for on-call assignment."""
        monday = self.start_sunday + timedelta(days=1)  # Jan 8
        available = ["Alice", "Bob", "Charlie", "Diana"]  # Alice works weekend this week
        
        selected = enhanced_oncall_selection(
            available, monday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should select a non-weekend worker (not Alice)
        assert selected != "Alice"
        assert selected in ["Bob", "Charlie", "Diana"]
        
        # Check decision logging
        assert len(self.decision_log) == 1
        decision = self.decision_log[0]
        assert decision.decision_type == "enhanced_oncall_assignment"
        assert decision.affected_engineers == [selected]
        assert "avoided weekend workers: Alice" in decision.reason
    
    def test_fallback_when_all_available_are_weekend_workers(self):
        """Test fallback behavior when all available engineers work weekends."""
        monday = self.start_sunday + timedelta(days=1)  # Jan 8
        available = ["Alice"]  # Only Alice available, and she works weekend
        
        selected = enhanced_oncall_selection(
            available, monday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should fallback to Alice since no other options
        assert selected == "Alice"
        
        # Check decision logging indicates fallback
        assert len(self.decision_log) == 1
        decision = self.decision_log[0]
        assert decision.decision_type == "enhanced_oncall_assignment"
        assert "fallback used" in decision.reason
        assert "no non-weekend options available" in decision.reason
    
    def test_friday_avoids_both_current_and_next_weekend_workers(self):
        """Test that Friday avoids both current and next week's weekend workers."""
        friday = self.start_sunday + timedelta(days=5)  # Jan 12 (Friday)
        available = ["Alice", "Bob", "Charlie", "Diana"]  # Alice (current), Bob (next)
        
        selected = enhanced_oncall_selection(
            available, friday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should avoid both Alice and Bob
        assert selected not in ["Alice", "Bob"]
        assert selected in ["Charlie", "Diana"]
        
        # Check decision logging mentions both avoided engineers
        decision = self.decision_log[0]
        assert "Alice" in decision.reason and "Bob" in decision.reason
    
    def test_rotation_order_respected_among_non_weekend_workers(self):
        """Test that rotation order is respected among non-weekend workers."""
        tuesday = self.start_sunday + timedelta(days=2)  # Jan 9
        available = ["Bob", "Charlie", "Diana", "Eve"]  # Alice excluded, no weekend workers
        
        # Clear decision log for clean test
        self.decision_log.clear()
        
        selected = enhanced_oncall_selection(
            available, tuesday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should follow rotation order (seed=1, day_offset=2)
        # Expected order based on rotation calculation
        day_idx = 2
        expected_order = sorted(available, key=lambda name: ((self.engineers.index(name) + 1 + day_idx) % len(self.engineers)))
        
        assert selected == expected_order[0]
    
    def test_empty_available_list(self):
        """Test behavior with empty available engineers list."""
        monday = self.start_sunday + timedelta(days=1)
        available = []
        
        selected = enhanced_oncall_selection(
            available, monday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should return empty string
        assert selected == ""
    
    def test_decision_logging_accuracy(self):
        """Test that decision logging captures all required information."""
        wednesday = self.start_sunday + timedelta(days=3)  # Jan 10
        available = ["Alice", "Charlie", "Diana"]  # Alice works weekend
        
        self.decision_log.clear()
        
        selected = enhanced_oncall_selection(
            available, wednesday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Verify decision log structure
        assert len(self.decision_log) == 1
        decision = self.decision_log[0]
        
        # Check all required fields
        assert decision.date == wednesday.isoformat()
        assert decision.decision_type == "enhanced_oncall_assignment"
        assert decision.affected_engineers == [selected]
        assert isinstance(decision.reason, str) and len(decision.reason) > 0
        assert isinstance(decision.alternatives_considered, list)
        assert decision.timestamp is not None
        
        # Check that alternatives are provided
        assert len(decision.alternatives_considered) > 0


class TestIntegrationWithWeekendRotation:
    """Integration tests with weekend rotation logic."""
    
    def setup_method(self):
        """Set up test data."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.start_sunday = date(2024, 1, 7)
        self.seeds = {"oncall": 0, "weekend": 2}  # Different seeds
        self.weekend_seeded = build_rotation(self.engineers, self.seeds["weekend"])
        self.decision_log = []
    
    def test_weekend_rotation_with_different_seed(self):
        """Test weekend worker avoidance with different rotation seed."""
        # With weekend seed=2, rotation starts with Charlie
        monday = self.start_sunday + timedelta(days=1)
        available = ["Alice", "Bob", "Charlie", "Diana"]
        
        # Charlie should be the weekend worker for week 0
        weekend_worker = weekend_worker_for_week(self.weekend_seeded, 0)
        assert weekend_worker == "Charlie"
        
        selected = enhanced_oncall_selection(
            available, monday, self.start_sunday, self.weekend_seeded, 
            self.engineers, self.seeds, self.decision_log
        )
        
        # Should avoid Charlie
        assert selected != "Charlie"
        assert selected in ["Alice", "Bob", "Diana"]
    
    def test_multiple_weeks_progression(self):
        """Test on-call assignment across multiple weeks."""
        results = []
        
        for week in range(3):
            monday = self.start_sunday + timedelta(days=week*7 + 1)
            available = self.engineers.copy()  # All available
            
            self.decision_log.clear()
            selected = enhanced_oncall_selection(
                available, monday, self.start_sunday, self.weekend_seeded, 
                self.engineers, self.seeds, self.decision_log
            )
            
            weekend_worker = weekend_worker_for_week(self.weekend_seeded, week)
            results.append({
                'week': week,
                'selected': selected,
                'weekend_worker': weekend_worker,
                'avoided_weekend_worker': selected != weekend_worker
            })
        
        # Verify weekend workers were avoided in each week
        for result in results:
            assert result['avoided_weekend_worker'], f"Week {result['week']}: Failed to avoid weekend worker {result['weekend_worker']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])