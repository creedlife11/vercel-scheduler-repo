"""
Test suite for enhanced fairness analysis and insights functionality.
Tests fairness weighting, distribution analysis, and actionable recommendations.
"""

import pytest
from datetime import date, timedelta
import pandas as pd
from typing import List, Dict

from schedule_core import (
    EnhancedFairnessTracker, 
    calculate_enhanced_fairness_report,
    generate_fairness_insights,
    calculate_fairness_weighted_selection,
    apply_fairness_impact_tracking,
    get_fairness_weighted_rotation_order,
    make_enhanced_schedule,
    calculate_gini_coefficient
)
from models import ScheduleResult, FairnessReport, EngineerStats, DecisionEntry


class TestEnhancedFairnessTracker:
    """Test the EnhancedFairnessTracker class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.tracker = EnhancedFairnessTracker(self.engineers)
    
    def test_initialization(self):
        """Test proper initialization of fairness tracker."""
        assert len(self.tracker.engineers) == 6
        assert all(eng in self.tracker.assignment_history for eng in self.engineers)
        
        # Check initial assignment counts are zero
        for engineer in self.engineers:
            for role in ['weekend', 'oncall', 'early', 'chat', 'appointments']:
                assert self.tracker.assignment_history[engineer][role] == 0
    
    def test_track_assignment_with_weight(self):
        """Test assignment tracking with configurable weights."""
        # Track some assignments
        self.tracker.track_assignment_with_weight("Alice", "weekend", "2024-01-01", 2.0)
        self.tracker.track_assignment_with_weight("Bob", "oncall", "2024-01-02", 1.5)
        self.tracker.track_assignment_with_weight("Charlie", "early", "2024-01-03", 1.2)
        
        # Verify tracking
        assert self.tracker.assignment_history["Alice"]["weekend"] == 2.0
        assert self.tracker.assignment_history["Bob"]["oncall"] == 1.5
        assert self.tracker.assignment_history["Charlie"]["early"] == 1.2
        
        # Verify weekend-specific tracking
        assert self.tracker.weekend_assignments["Alice"] == 1
        assert self.tracker.weekend_assignments["Bob"] == 0
    
    def test_get_fairness_weights(self):
        """Test fairness weight calculation for role assignment."""
        # Create imbalanced assignments
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Bob", "oncall")
        
        weights = self.tracker.get_fairness_weights("oncall")
        
        # Alice should have higher weight (less preferred) due to more assignments
        assert weights["Alice"] > weights["Bob"]
        assert weights["Charlie"] == 0.0  # Charlie has minimum assignments (0)
        assert weights["Bob"] == 1.0  # Bob has 1 more than minimum
    
    def test_calculate_overall_fairness_score(self):
        """Test overall fairness score calculation using Gini coefficient."""
        # Create perfectly balanced assignments
        for engineer in self.engineers:
            self.tracker.track_assignment(engineer, "oncall")
            self.tracker.track_assignment(engineer, "chat")
        
        score = self.tracker.calculate_overall_fairness_score()
        assert score == 0.0  # Perfect equality
        
        # Create imbalanced assignments
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Alice", "oncall")
        
        score = self.tracker.calculate_overall_fairness_score()
        assert score > 0.0  # Some inequality
    
    def test_get_engineer_workload_analysis(self):
        """Test detailed workload analysis for engineers."""
        # Create varied workloads
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Alice", "weekend")
        self.tracker.track_assignment("Bob", "chat")
        
        analysis = self.tracker.get_engineer_workload_analysis()
        
        assert "Alice" in analysis
        assert "Bob" in analysis
        assert analysis["Alice"]["total_assignments"] == 2
        assert analysis["Bob"]["total_assignments"] == 1
        assert analysis["Charlie"]["total_assignments"] == 0
        
        # Check fairness ranks
        assert analysis["Alice"]["fairness_rank"] == 6  # Most assignments
        assert analysis["Charlie"]["fairness_rank"] == 1  # Least assignments
    
    def test_get_role_specific_gini_coefficients(self):
        """Test Gini coefficient calculation for individual roles."""
        # Create imbalanced oncall assignments
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Bob", "oncall")
        
        # Create balanced chat assignments
        for engineer in self.engineers:
            self.tracker.track_assignment(engineer, "chat")
        
        role_gini = self.tracker.get_role_specific_gini_coefficients()
        
        assert role_gini["oncall"] > 0.0  # Imbalanced
        assert role_gini["chat"] == 0.0   # Perfectly balanced
    
    def test_identify_fairness_outliers(self):
        """Test identification of engineers with extreme assignment counts."""
        # Create outliers
        for _ in range(5):
            self.tracker.track_assignment("Alice", "oncall")  # Overloaded
        
        # Leave Charlie with no assignments (underutilized)
        
        outliers = self.tracker.identify_fairness_outliers(threshold=0.5)  # Lower threshold to catch the difference
        
        assert "Alice" in outliers["overloaded"]
        # Charlie should be underutilized since Alice has 5 assignments and Charlie has 0
        # Average is 5/6 ≈ 0.83, so Charlie's deviation is -0.83 which is > 0.5
        assert "Charlie" in outliers["underutilized"]
    
    def test_generate_rebalancing_recommendations(self):
        """Test generation of specific rebalancing recommendations."""
        # Create significant imbalances - need more extreme imbalance
        for _ in range(5):
            self.tracker.track_assignment("Alice", "oncall")
        
        recommendations = self.tracker.generate_rebalancing_recommendations()
        
        assert len(recommendations) > 0
        # Check that recommendations contain relevant information
        recommendations_text = " ".join(recommendations)
        assert "oncall" in recommendations_text.lower()
        # The function should identify the problematic role and provide guidance
        assert "gini" in recommendations_text.lower() or "rebalancing" in recommendations_text.lower()
    
    def test_get_weighted_workload(self):
        """Test weighted workload calculation with role difficulty weights."""
        # Assign different roles with different weights
        self.tracker.track_assignment("Alice", "weekend")  # Weight 2.0
        self.tracker.track_assignment("Alice", "oncall")   # Weight 1.5
        self.tracker.track_assignment("Bob", "chat")       # Weight 1.0
        self.tracker.track_assignment("Bob", "chat")       # Weight 1.0
        
        alice_weighted = self.tracker.get_weighted_workload("Alice")
        bob_weighted = self.tracker.get_weighted_workload("Bob")
        
        # Alice: 1*2.0 + 1*1.5 = 3.5
        # Bob: 2*1.0 = 2.0
        assert alice_weighted == 3.5
        assert bob_weighted == 2.0


class TestFairnessWeightedSelection:
    """Test fairness-weighted selection functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        self.tracker = EnhancedFairnessTracker(self.engineers)
    
    def test_calculate_fairness_weighted_selection(self):
        """Test fairness-weighted selection ordering."""
        # Create imbalanced assignments
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Alice", "oncall")
        self.tracker.track_assignment("Bob", "oncall")
        
        candidates = ["Alice", "Bob", "Charlie"]
        ordered = calculate_fairness_weighted_selection(
            candidates, "oncall", self.tracker, candidates
        )
        
        # Charlie should be first (no assignments), then Bob, then Alice
        assert ordered[0] == "Charlie"
        assert ordered[1] == "Bob"
        assert ordered[2] == "Alice"
    
    def test_get_fairness_weighted_rotation_order(self):
        """Test fairness-weighted rotation order generation."""
        # Create some assignments to create fairness weights
        self.tracker.track_assignment("Alice", "chat")
        self.tracker.track_assignment("Alice", "chat")
        
        available = ["Alice", "Bob", "Charlie"]
        ordered = get_fairness_weighted_rotation_order(
            self.engineers, "chat", 0, available, self.tracker
        )
        
        # Bob and Charlie should be preferred over Alice
        assert ordered.index("Alice") > ordered.index("Bob")
        assert ordered.index("Alice") > ordered.index("Charlie")
    
    def test_apply_fairness_impact_tracking(self):
        """Test fairness impact tracking for assignments."""
        decision_log = []
        
        # Add a decision entry first
        decision_log.append(DecisionEntry(
            date="2024-01-01",
            decision_type="test_assignment",
            affected_engineers=["Alice"],
            reason="Test assignment",
            alternatives_considered=[]
        ))
        
        apply_fairness_impact_tracking(
            "Alice", "oncall", "2024-01-01", self.tracker, decision_log, 1.5
        )
        
        # Check that assignment was tracked
        assert self.tracker.assignment_history["Alice"]["oncall"] == 1.5
        
        # Check that decision log was enhanced
        assert "fairness weight" in decision_log[0].reason


class TestEnhancedFairnessReporting:
    """Test enhanced fairness reporting and insights."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        
        # Create a sample schedule DataFrame
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(14)]  # 2 weeks
        
        rows = []
        for i, d in enumerate(dates):
            dow = d.strftime("%a")
            week_idx = i // 7
            
            # Rotate assignments to create some imbalance
            early1 = self.engineers[i % 6]
            early2 = self.engineers[(i + 1) % 6]
            chat = self.engineers[(i + 2) % 6]
            oncall = self.engineers[(i + 3) % 6]
            appointments = self.engineers[(i + 4) % 6]
            
            # Create engineer status columns
            eng_data = []
            for j, eng in enumerate(self.engineers):
                eng_data.extend([eng, "WORK", "08:00-17:00"])
            
            row = [d, dow, week_idx, early1, early2, chat, oncall, appointments] + eng_data
            rows.append(row)
        
        columns = ["Date", "Day", "WeekIndex", "Early1", "Early2", "Chat", "OnCall", "Appointments"]
        for i in range(6):
            columns.extend([f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"])
        
        self.df = pd.DataFrame(rows, columns=columns)
    
    def test_calculate_enhanced_fairness_report(self):
        """Test enhanced fairness report calculation."""
        # Test with leave_map to ensure enhanced functionality works
        leave_map = {"Alice": {date(2024, 1, 1)}}  # Alice has one leave day
        
        report = calculate_enhanced_fairness_report(self.df, self.engineers, leave_map)
        
        assert isinstance(report, FairnessReport)
        assert len(report.engineer_stats) == 6
        assert report.equity_score >= 0.0
        
        # Test without leave_map to ensure base functionality still works
        report_no_leave = calculate_enhanced_fairness_report(self.df, self.engineers)
        
        assert isinstance(report_no_leave, FairnessReport)
        assert len(report_no_leave.engineer_stats) == 6
        assert report_no_leave.equity_score >= 0.0
        
        # Both reports should have the same basic structure
        alice_stats = report.engineer_stats["Alice"]
        alice_stats_no_leave = report_no_leave.engineer_stats["Alice"]
        
        # Basic stats should be the same
        assert alice_stats.name == alice_stats_no_leave.name
        assert alice_stats.oncall_count == alice_stats_no_leave.oncall_count
    
    def test_generate_fairness_insights_comprehensive(self):
        """Test comprehensive fairness insights generation."""
        # Create an imbalanced fairness report
        engineer_stats = {}
        for i, engineer in enumerate(self.engineers):
            stats = EngineerStats(name=engineer)
            stats.oncall_count = i  # Create imbalance: Alice=0, Bob=1, ..., Frank=5
            stats.weekend_count = 1
            stats.early_count = 2
            stats.chat_count = 2
            stats.appointments_count = 2
            engineer_stats[engineer] = stats
        
        # Calculate Gini coefficient for this imbalanced distribution
        total_counts = [sum([stats.oncall_count, stats.weekend_count, stats.early_count, 
                           stats.chat_count, stats.appointments_count]) 
                       for stats in engineer_stats.values()]
        equity_score = calculate_gini_coefficient(total_counts)
        
        max_min_deltas = {
            "oncall": 5,  # Frank has 5, Alice has 0
            "weekend": 0,
            "early": 0,
            "chat": 0,
            "appointments": 0
        }
        
        report = FairnessReport(
            engineer_stats=engineer_stats,
            equity_score=equity_score,
            max_min_deltas=max_min_deltas
        )
        
        insights = generate_fairness_insights(report)
        
        assert len(insights) > 0
        assert any("oncall" in insight for insight in insights)
        assert any("Frank" in insight for insight in insights)  # Should identify Frank as overloaded
        assert any("Alice" in insight for insight in insights)  # Should identify Alice as underutilized
    
    def test_fairness_insights_quality_levels(self):
        """Test different quality levels of fairness insights."""
        # Test excellent fairness (low Gini coefficient)
        excellent_stats = {}
        for engineer in self.engineers:
            stats = EngineerStats(name=engineer)
            stats.oncall_count = 2
            stats.weekend_count = 2
            stats.early_count = 2
            stats.chat_count = 2
            stats.appointments_count = 2
            excellent_stats[engineer] = stats
        
        excellent_report = FairnessReport(
            engineer_stats=excellent_stats,
            equity_score=0.0,  # Perfect equality
            max_min_deltas={"oncall": 0, "weekend": 0, "early": 0, "chat": 0, "appointments": 0}
        )
        
        insights = generate_fairness_insights(excellent_report)
        assert any("Excellent" in insight or "🟢" in insight for insight in insights)
        
        # Test critical fairness (high Gini coefficient)
        critical_stats = {}
        for i, engineer in enumerate(self.engineers):
            stats = EngineerStats(name=engineer)
            stats.oncall_count = i * 3  # Highly imbalanced
            critical_stats[engineer] = stats
        
        critical_report = FairnessReport(
            engineer_stats=critical_stats,
            equity_score=0.5,  # High inequality
            max_min_deltas={"oncall": 15, "weekend": 0, "early": 0, "chat": 0, "appointments": 0}
        )
        
        insights = generate_fairness_insights(critical_report)
        assert any("Critical" in insight or "🔴" in insight for insight in insights)


class TestFairnessIntegration:
    """Test integration of fairness features with schedule generation."""
    
    def test_enhanced_schedule_includes_fairness_insights(self):
        """Test that enhanced schedule generation includes fairness insights."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        start_sunday = date(2024, 1, 7)  # A Sunday
        weeks = 2
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        leave_df = pd.DataFrame()  # No leave
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
        
        assert isinstance(result, ScheduleResult)
        assert hasattr(result, 'fairness_insights')
        assert len(result.fairness_insights) > 0
        
        # Check that insights contain meaningful information
        insights_text = " ".join(result.fairness_insights)
        assert any(keyword in insights_text.lower() for keyword in 
                  ["fairness", "equity", "gini", "distribution", "balance"])
    
    def test_fairness_weighting_improves_distribution(self):
        """Test that fairness weighting improves distribution over multiple generations."""
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        start_sunday = date(2024, 1, 7)
        weeks = 4  # Longer schedule to see fairness effects
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        leave_df = pd.DataFrame()
        
        # Generate schedule with fairness weighting
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
        
        # Check that fairness score is reasonable
        fairness_score = result.fairness_report.equity_score
        assert 0.0 <= fairness_score <= 1.0
        
        # Check that max-min deltas are not excessive
        max_deltas = result.fairness_report.max_min_deltas
        for role, delta in max_deltas.items():
            assert delta <= 4, f"Role {role} has excessive imbalance: {delta}"
        
        # Check that fairness insights provide actionable recommendations
        insights = result.fairness_insights
        assert len(insights) >= 3  # Should have multiple insights
        
        # Should include equity score information
        assert any("equity" in insight.lower() or "gini" in insight.lower() 
                  for insight in insights)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])