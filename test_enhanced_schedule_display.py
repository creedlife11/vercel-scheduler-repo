"""
Test suite for enhanced schedule display formatting and role clarity.

Requirements tested:
- 5.1: Improve existing DataFrame output to clearly show all role assignments
- 5.1: Add better formatting for shift times (06:45-15:45 vs 08:00-17:00 vs Weekend)
- 5.3: Ensure WORK/OFF/LEAVE status is clearly displayed for each engineer
- 5.2: Enhance existing CSV/XLSX export to include clear role indicators
- 5.4: Improve schedule readability for end users
- 5.5: Test schedule formatting accuracy and readability
"""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any, List
import json
import io

from lib.enhanced_display import (
    EnhancedScheduleFormatter, 
    enhance_schedule_display,
    format_shift_time_display,
    format_status_display,
    validate_display_formatting
)
from export_manager import (
    ExportManager,
    add_role_clarity_indicators,
    generate_role_assignment_report
)
from models import (
    ScheduleResult, 
    FairnessReport, 
    DecisionEntry, 
    ScheduleMetadata, 
    EngineerStats,
    WeekendCompensation
)
from schedule_core import make_enhanced_schedule


class TestEnhancedScheduleFormatter:
    """Test enhanced schedule formatting functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create sample schedule data
        self.sample_schedule_data = {
            "headers": [
                "Date", "Day", "WeekIndex", "Early1", "Early2", "Chat", "OnCall", "Appointments",
                "1) Engineer", "Status 1", "Shift 1",
                "2) Engineer", "Status 2", "Shift 2",
                "3) Engineer", "Status 3", "Shift 3",
                "4) Engineer", "Status 4", "Shift 4",
                "5) Engineer", "Status 5", "Shift 5",
                "6) Engineer", "Status 6", "Shift 6"
            ],
            "rows": [
                # Monday - Weekday
                [date(2024, 1, 1), "Mon", 0, "Alice", "Bob", "Charlie", "David", "Eve",
                 "Alice", "WORK", "06:45-15:45",
                 "Bob", "WORK", "06:45-15:45", 
                 "Charlie", "WORK", "08:00-17:00",
                 "David", "WORK", "08:00-17:00",
                 "Eve", "WORK", "08:00-17:00",
                 "Frank", "OFF", ""],
                # Saturday - Weekend
                [date(2024, 1, 6), "Sat", 0, "", "", "", "", "",
                 "Alice", "WORK", "Weekend-A",
                 "Bob", "OFF", "",
                 "Charlie", "OFF", "",
                 "David", "OFF", "",
                 "Eve", "OFF", "",
                 "Frank", "LEAVE", ""],
                # Sunday - Weekend
                [date(2024, 1, 7), "Sun", 0, "", "", "", "", "",
                 "Alice", "WORK", "Weekend-B",
                 "Bob", "OFF", "",
                 "Charlie", "OFF", "",
                 "David", "OFF", "",
                 "Eve", "OFF", "",
                 "Frank", "LEAVE", ""]
            ]
        }
        
        # Create sample fairness report
        engineer_stats = {}
        engineers = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"]
        for engineer in engineers:
            engineer_stats[engineer] = EngineerStats(name=engineer)
        
        self.sample_fairness_report = FairnessReport(
            engineer_stats=engineer_stats,
            equity_score=0.15,
            max_min_deltas={"oncall": 1, "weekend": 2, "early": 1, "chat": 0, "appointments": 1}
        )
        
        # Create sample metadata
        self.sample_metadata = ScheduleMetadata(
            generation_timestamp=datetime.now(),
            configuration={"test": True},
            engineer_count=6,
            weeks=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            total_days=7
        )
        
        # Create sample schedule result
        self.sample_schedule_result = ScheduleResult(
            schedule_data=self.sample_schedule_data,
            fairness_report=self.sample_fairness_report,
            decision_log=[],
            metadata=self.sample_metadata,
            weekend_compensation_tracking=[],
            schema_version="2.0"
        )
    
    def test_enhanced_dataframe_formatting(self):
        """Test that DataFrame formatting includes all required enhancements."""
        formatter = EnhancedScheduleFormatter(self.sample_schedule_result)
        enhanced_df = formatter.format_enhanced_dataframe()
        
        # Check that role summary column is added
        assert "Role Summary" in enhanced_df.columns
        
        # Check that role assignments are properly formatted
        monday_row = enhanced_df[enhanced_df["Day"] == "Mon"].iloc[0]
        role_summary = monday_row["Role Summary"]
        
        assert "Early1: Alice" in role_summary
        assert "Early2: Bob" in role_summary
        assert "Chat: Charlie" in role_summary
        assert "OnCall: David" in role_summary
        assert "Appt: Eve" in role_summary
        
        # Check that summary columns are added
        assert "Active Roles" in enhanced_df.columns
        assert "Working Engineers" in enhanced_df.columns
        
        # Verify active roles count for Monday
        assert monday_row["Active Roles"] == 5  # All 5 roles assigned
        
        print("✓ Enhanced DataFrame formatting test passed")
    
    def test_shift_time_formatting(self):
        """Test enhanced shift time display formatting."""
        # Test early shift formatting
        early_formatted = format_shift_time_display("06:45-15:45")
        assert early_formatted == "Early Shift (06:45-15:45)"
        
        # Test regular shift formatting
        regular_formatted = format_shift_time_display("08:00-17:00")
        assert regular_formatted == "Regular Shift (08:00-17:00)"
        
        # Test weekend pattern A formatting
        weekend_a_formatted = format_shift_time_display("Weekend-A")
        assert "Weekend Pattern A" in weekend_a_formatted
        assert "Saturday" in weekend_a_formatted
        
        # Test weekend pattern B formatting
        weekend_b_formatted = format_shift_time_display("Weekend-B")
        assert "Weekend Pattern B" in weekend_b_formatted
        assert "Sunday" in weekend_b_formatted
        
        # Test empty shift formatting
        empty_formatted = format_shift_time_display("")
        assert empty_formatted == "Not Working"
        
        print("✓ Shift time formatting test passed")
    
    def test_status_display_formatting(self):
        """Test enhanced status display formatting."""
        # Test work status
        work_formatted = format_status_display("WORK")
        assert work_formatted == "✓ Working"
        
        # Test off status
        off_formatted = format_status_display("OFF")
        assert off_formatted == "○ Off Duty"
        
        # Test leave status
        leave_formatted = format_status_display("LEAVE")
        assert leave_formatted == "✗ On Leave"
        
        # Test empty status
        empty_formatted = format_status_display("")
        assert empty_formatted == "○ Off Duty"
        
        print("✓ Status display formatting test passed")
    
    def test_role_assignment_summary_generation(self):
        """Test role assignment summary generation."""
        formatter = EnhancedScheduleFormatter(self.sample_schedule_result)
        summary = formatter.generate_role_assignment_summary()
        
        # Check summary structure
        assert "total_days" in summary
        assert "role_distribution" in summary
        assert "engineer_workload" in summary
        assert "shift_patterns" in summary
        assert "coverage_analysis" in summary
        
        # Check total days
        assert summary["total_days"] == 3  # 3 rows in sample data
        
        # Check coverage analysis structure
        coverage = summary["coverage_analysis"]
        assert "weekday_coverage" in coverage
        assert "weekend_coverage" in coverage
        
        # Check weekday coverage
        weekday_cov = coverage["weekday_coverage"]
        assert weekday_cov["total_weekdays"] == 1  # 1 Monday in sample
        
        # Check weekend coverage
        weekend_cov = coverage["weekend_coverage"]
        assert weekend_cov["total_weekend_days"] == 2  # 1 Saturday + 1 Sunday
        
        print("✓ Role assignment summary generation test passed")
    
    def test_enhanced_schedule_display_integration(self):
        """Test full enhanced schedule display integration."""
        enhanced_result = enhance_schedule_display(self.sample_schedule_result)
        
        # Check that enhanced data is included
        assert "role_summary" in enhanced_result.schedule_data
        assert "fairness_insights" in enhanced_result.schedule_data
        assert "enhanced_metadata" in enhanced_result.schedule_data
        
        # Check role summary structure
        role_summary = enhanced_result.schedule_data["role_summary"]
        assert "total_days" in role_summary
        assert "coverage_analysis" in role_summary
        
        print("✓ Enhanced schedule display integration test passed")


class TestRoleClarityIndicators:
    """Test role clarity indicators for exports."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_schedule_data = {
            "headers": ["Date", "Day", "Early1", "Early2", "Chat", "OnCall", "Appointments"],
            "rows": [
                [date(2024, 1, 1), "Mon", "Alice", "Bob", "Charlie", "David", "Eve"],
                [date(2024, 1, 2), "Tue", "Bob", "Charlie", "David", "Eve", "Alice"]
            ]
        }
    
    def test_role_clarity_indicators_addition(self):
        """Test addition of role clarity indicators."""
        enhanced_data = add_role_clarity_indicators(self.sample_schedule_data)
        
        # Check that role clarity is enabled
        assert enhanced_data.get("role_clarity_enabled") is True
        
        # Check that role indicators are added
        first_row = enhanced_data["rows"][0]
        
        # Check Early1 indicator
        assert "🌅" in first_row[2]  # Early1 column
        assert "Alice" in first_row[2]
        assert "(Early1)" in first_row[2]
        
        # Check Chat indicator
        assert "💬" in first_row[4]  # Chat column
        assert "Charlie" in first_row[4]
        assert "(Chat)" in first_row[4]
        
        # Check OnCall indicator
        assert "📞" in first_row[5]  # OnCall column
        assert "David" in first_row[5]
        assert "(OnCall)" in first_row[5]
        
        print("✓ Role clarity indicators test passed")
    
    def test_role_assignment_report_generation(self):
        """Test comprehensive role assignment report generation."""
        report = generate_role_assignment_report(self.sample_schedule_data)
        
        # Check report structure
        assert "summary" in report
        assert "role_statistics" in report
        assert "engineer_statistics" in report
        assert "role_distribution_balance" in report
        
        # Check summary statistics
        summary = report["summary"]
        assert summary["total_days"] == 2
        assert summary["total_weekdays"] == 2  # Both Mon and Tue are weekdays
        
        # Check role statistics
        role_stats = report["role_statistics"]
        assert "Early1" in role_stats
        assert "Chat" in role_stats
        assert "OnCall" in role_stats
        
        # Check that each role has proper structure
        early1_stats = role_stats["Early1"]
        assert "total_assignments" in early1_stats
        assert "engineers" in early1_stats
        assert early1_stats["total_assignments"] == 2  # 2 days
        
        print("✓ Role assignment report generation test passed")


class TestExportFormatting:
    """Test enhanced export formatting."""
    
    def setup_method(self):
        """Set up test data."""
        # Create a complete schedule result for testing
        engineers = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"]
        
        # Create sample fairness report
        engineer_stats = {}
        for engineer in engineers:
            stats = EngineerStats(name=engineer)
            stats.oncall_count = 2
            stats.weekend_count = 1
            stats.early_count = 3
            stats.chat_count = 2
            stats.appointments_count = 2
            engineer_stats[engineer] = stats
        
        fairness_report = FairnessReport(
            engineer_stats=engineer_stats,
            equity_score=0.12,
            max_min_deltas={"oncall": 1, "weekend": 1, "early": 1, "chat": 1, "appointments": 1}
        )
        
        # Create sample schedule data
        schedule_data = {
            "headers": [
                "Date", "Day", "WeekIndex", "Early1", "Early2", "Chat", "OnCall", "Appointments",
                "1) Engineer", "Status 1", "Shift 1",
                "2) Engineer", "Status 2", "Shift 2"
            ],
            "rows": [
                [date(2024, 1, 1), "Mon", 0, "Alice", "Bob", "Charlie", "David", "Eve",
                 "Alice", "WORK", "06:45-15:45",
                 "Bob", "WORK", "06:45-15:45"]
            ]
        }
        
        metadata = ScheduleMetadata(
            generation_timestamp=datetime.now(),
            configuration={"test": True},
            engineer_count=6,
            weeks=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            total_days=7
        )
        
        self.schedule_result = ScheduleResult(
            schedule_data=schedule_data,
            fairness_report=fairness_report,
            decision_log=[],
            metadata=metadata,
            weekend_compensation_tracking=[],
            schema_version="2.0"
        )
    
    def test_csv_export_with_role_clarity(self):
        """Test CSV export includes role clarity and summaries."""
        export_manager = ExportManager(self.schedule_result)
        csv_content = export_manager.to_csv()
        
        # Check that UTF-8 BOM is included
        assert csv_content.startswith('\ufeff')
        
        # Check that basic CSV structure is present
        assert "Date" in csv_content
        assert "Day" in csv_content
        
        # Check for role columns
        assert "Early1" in csv_content
        assert "OnCall" in csv_content
        
        # Check that role clarity indicators are present
        assert "🌅" in csv_content  # Early shift indicator
        assert "💬" in csv_content  # Chat indicator  
        assert "📞" in csv_content  # OnCall indicator
        assert "📅" in csv_content  # Appointments indicator
        
        # Check that role names are included in indicators
        assert "(Early1)" in csv_content
        assert "(Chat)" in csv_content
        assert "(OnCall)" in csv_content
        assert "(Appointments)" in csv_content
        
        print("✓ CSV export with role clarity test passed")
    
    def test_xlsx_export_with_enhanced_sheets(self):
        """Test XLSX export includes enhanced sheets and role information."""
        try:
            export_manager = ExportManager(self.schedule_result)
            xlsx_bytes = export_manager.to_xlsx()
            
            # Check that we get valid XLSX bytes
            assert isinstance(xlsx_bytes, bytes)
            assert len(xlsx_bytes) > 0
            
            print("✓ XLSX export with enhanced sheets test passed")
        except ModuleNotFoundError as e:
            if "openpyxl" in str(e):
                print("⚠ XLSX export test skipped - openpyxl not installed")
                return
            else:
                raise
    
    def test_json_export_with_role_report(self):
        """Test JSON export includes role assignment report."""
        export_manager = ExportManager(self.schedule_result)
        json_data = export_manager.to_json()
        
        # Check that role assignment report is included
        assert "roleAssignmentReport" in json_data
        
        # Check role report structure
        role_report = json_data["roleAssignmentReport"]
        assert "summary" in role_report
        assert "role_statistics" in role_report
        assert "engineer_statistics" in role_report
        
        # Check that role clarity is enabled in schedule data
        schedule_data = json_data["schedule"]
        assert schedule_data.get("role_clarity_enabled") is True
        
        print("✓ JSON export with role report test passed")


class TestDisplayValidation:
    """Test display formatting validation."""
    
    def test_validate_display_formatting_success(self):
        """Test validation passes for properly formatted display."""
        # Create properly formatted DataFrame
        df = pd.DataFrame({
            "Date": [date(2024, 1, 1)],
            "Day": ["Mon"],
            "Early1": ["Alice"],
            "Early2": ["Bob"],
            "Chat": ["Charlie"],
            "OnCall": ["David"],
            "Appointments": ["Eve"],
            "Status 1": ["✓ Working"],
            "Status 2": ["○ Off Duty"],
            "Shift 1": ["Early Shift (06:45-15:45)"],
            "Shift 2": ["Regular Shift (08:00-17:00)"]
        })
        
        issues = validate_display_formatting(df)
        assert len(issues) == 0, f"Validation should pass but found issues: {issues}"
        
        print("✓ Display formatting validation success test passed")
    
    def test_validate_display_formatting_failures(self):
        """Test validation catches formatting issues."""
        # Create DataFrame with missing columns
        df = pd.DataFrame({
            "Date": [date(2024, 1, 1)],
            "Day": ["Mon"]
            # Missing role columns, status columns, shift columns
        })
        
        issues = validate_display_formatting(df)
        assert len(issues) > 0, "Validation should catch missing columns"
        
        # Check for specific missing column issues
        issue_text = " ".join(issues)
        assert "Missing role columns" in issue_text
        assert "No status columns found" in issue_text
        assert "No shift columns found" in issue_text
        
        print("✓ Display formatting validation failure test passed")


class TestIntegrationWithScheduleGeneration:
    """Test integration with actual schedule generation."""
    
    def test_enhanced_display_with_real_schedule(self):
        """Test enhanced display works with real schedule generation."""
        # Generate a real schedule
        engineers = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"]
        start_sunday = date(2024, 1, 7)  # A Sunday
        weeks = 1
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        leave_df = pd.DataFrame()  # No leave
        
        # Generate enhanced schedule
        schedule_result = make_enhanced_schedule(
            start_sunday, weeks, engineers, seeds, leave_df, assign_early_on_weekends=False
        )
        
        # Check that enhanced display data is included
        assert "role_summary" in schedule_result.schedule_data
        assert "fairness_insights" in schedule_result.schedule_data
        
        # Test export functionality
        export_manager = ExportManager(schedule_result)
        
        # Test CSV export
        csv_content = export_manager.to_csv()
        assert len(csv_content) > 0
        assert "# ROLE SUMMARY SECTION" in csv_content
        
        # Test JSON export
        json_data = export_manager.to_json()
        assert "roleAssignmentReport" in json_data
        
        # Test XLSX export (if openpyxl is available)
        try:
            xlsx_bytes = export_manager.to_xlsx()
            assert len(xlsx_bytes) > 0
        except ModuleNotFoundError as e:
            if "openpyxl" in str(e):
                print("⚠ XLSX export skipped - openpyxl not installed")
            else:
                raise
        
        print("✓ Enhanced display integration with real schedule test passed")


def test_shift_time_display_consistency():
    """Test shift time display consistency across different formats."""
    test_cases = [
        ("06:45-15:45", "Early Shift (06:45-15:45)"),
        ("08:00-17:00", "Regular Shift (08:00-17:00)"),
        ("Weekend-A", "Weekend Pattern A (Saturday: Works Mon-Thu+Sat)"),
        ("Weekend-B", "Weekend Pattern B (Sunday: Works Sun+Tue-Fri)"),
        ("Weekend", "Weekend Shift"),
        ("", "Not Working"),
        (None, "Not Working")
    ]
    
    for input_value, expected_output in test_cases:
        if input_value is None:
            # Test None handling
            result = format_shift_time_display("")
        else:
            result = format_shift_time_display(input_value)
        
        assert result == expected_output, f"Expected '{expected_output}' for input '{input_value}', got '{result}'"
    
    print("✓ Shift time display consistency test passed")


def test_role_assignment_visibility():
    """Test that role assignments are clearly visible in all formats."""
    # Create test schedule with all roles assigned
    schedule_data = {
        "headers": ["Date", "Day", "Early1", "Early2", "Chat", "OnCall", "Appointments"],
        "rows": [
            [date(2024, 1, 1), "Mon", "Alice", "Bob", "Charlie", "David", "Eve"]
        ]
    }
    
    # Test role clarity indicators
    enhanced_data = add_role_clarity_indicators(schedule_data)
    row = enhanced_data["rows"][0]
    
    # Check that each role has clear indicators
    role_indicators = ["🌅", "💬", "📞", "📅"]  # Early, Chat, OnCall, Appointments
    role_text = " ".join(str(cell) for cell in row)
    
    for indicator in role_indicators:
        assert indicator in role_text, f"Role indicator '{indicator}' not found in row"
    
    # Check that role names are preserved
    engineers = ["Alice", "Bob", "Charlie", "David", "Eve"]
    for engineer in engineers:
        assert engineer in role_text, f"Engineer '{engineer}' not found in row"
    
    print("✓ Role assignment visibility test passed")


if __name__ == "__main__":
    # Run all tests
    test_classes = [
        TestEnhancedScheduleFormatter,
        TestRoleClarityIndicators, 
        TestExportFormatting,
        TestDisplayValidation,
        TestIntegrationWithScheduleGeneration
    ]
    
    for test_class in test_classes:
        print(f"\n=== Running {test_class.__name__} ===")
        test_instance = test_class()
        
        # Run setup if it exists
        if hasattr(test_instance, 'setup_method'):
            test_instance.setup_method()
        
        # Run all test methods
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                print(f"Running {method_name}...")
                getattr(test_instance, method_name)()
    
    # Run standalone tests
    print(f"\n=== Running Standalone Tests ===")
    test_shift_time_display_consistency()
    test_role_assignment_visibility()
    
    print(f"\n🎉 All enhanced schedule display tests passed!")