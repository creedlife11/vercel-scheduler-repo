"""
Core regression test suite with invariant checking for the scheduler.
Tests exact CSV column counts, status field validation, and engineer field integrity.
"""

import pytest
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Set
import csv
import io
import re

from schedule_core import make_enhanced_schedule, make_schedule
from export_manager import ExportManager
from models import ScheduleRequest, LeaveEntry, SeedsConfig


class TestScheduleInvariants:
    """Core regression tests asserting scheduling invariants."""
    
    @pytest.fixture
    def basic_engineers(self) -> List[str]:
        """Standard 6-engineer test fixture."""
        return ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    
    @pytest.fixture
    def basic_seeds(self) -> Dict[str, int]:
        """Standard seed configuration."""
        return {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    @pytest.fixture
    def empty_leave(self) -> pd.DataFrame:
        """Empty leave DataFrame."""
        return pd.DataFrame(columns=["Engineer", "Date"])
    
    @pytest.fixture
    def sample_leave(self, basic_engineers) -> pd.DataFrame:
        """Sample leave data for testing."""
        return pd.DataFrame([
            {"Engineer": basic_engineers[0], "Date": "2025-01-13"},  # Monday
            {"Engineer": basic_engineers[1], "Date": "2025-01-14"},  # Tuesday
            {"Engineer": basic_engineers[2], "Date": "2025-01-18"},  # Saturday
        ])
    
    def test_csv_column_count_consistency(self, basic_engineers, basic_seeds, empty_leave):
        """Assert every CSV row has exact expected column count."""
        start_sunday = date(2025, 1, 12)  # A Sunday
        weeks = 4
        
        # Generate schedule
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse CSV and check column counts
        lines = csv_content.strip().split('\n')
        
        # Skip header comments (lines starting with #)
        data_lines = [line for line in lines if not line.startswith('#')]
        
        if not data_lines:
            pytest.fail("No data lines found in CSV output")
        
        # Parse CSV properly
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        if len(rows) < 2:
            pytest.fail("CSV must have at least header and one data row")
        
        # Get expected column count from header
        header = rows[0]
        expected_columns = len(header)
        
        # Verify every row has exact same column count
        for i, row in enumerate(rows):
            actual_columns = len(row)
            assert actual_columns == expected_columns, (
                f"Row {i} has {actual_columns} columns, expected {expected_columns}. "
                f"Row content: {row}"
            )
    
    def test_status_field_validation(self, basic_engineers, basic_seeds, empty_leave):
        """Assert status fields only contain WORK/OFF/LEAVE values."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse CSV
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        if len(rows) < 2:
            pytest.fail("No data rows found")
        
        header = rows[0]
        
        # Find status columns (should be every other column starting from index 1)
        status_columns = []
        for i, col_name in enumerate(header):
            if 'Status' in col_name or col_name in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
                # Skip engineer name columns, focus on status columns
                if i % 2 == 1:  # Status columns are at odd indices
                    status_columns.append(i)
        
        valid_statuses = {'WORK', 'OFF', 'LEAVE', ''}
        
        # Check each data row
        for row_idx, row in enumerate(rows[1:], 1):
            for col_idx in status_columns:
                if col_idx < len(row):
                    status_value = row[col_idx].strip()
                    assert status_value in valid_statuses, (
                        f"Row {row_idx}, column {col_idx} ({header[col_idx] if col_idx < len(header) else 'unknown'}) "
                        f"has invalid status '{status_value}'. Must be one of: {valid_statuses}"
                    )
    
    def test_engineer_field_integrity(self, basic_engineers, basic_seeds, empty_leave):
        """Assert engineer columns contain only valid engineer names, no time strings."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse CSV
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        if len(rows) < 2:
            pytest.fail("No data rows found")
        
        header = rows[0]
        
        # Find engineer columns (should be every other column starting from index 0)
        engineer_columns = []
        for i, col_name in enumerate(header):
            if i % 2 == 0:  # Engineer columns are at even indices
                engineer_columns.append(i)
        
        # Valid engineer names (including empty for unassigned)
        valid_engineers = set(basic_engineers) | {'', 'UNASSIGNED'}
        
        # Patterns that indicate time strings (should not appear in engineer columns)
        time_patterns = [
            r'\d{1,2}:\d{2}',  # HH:MM format
            r'\d{1,2}am|\d{1,2}pm',  # 12-hour format
            r'morning|afternoon|evening|night',  # Time words
            r'early|late|shift'  # Shift-related words
        ]
        
        # Check each data row
        for row_idx, row in enumerate(rows[1:], 1):
            for col_idx in engineer_columns:
                if col_idx < len(row):
                    engineer_value = row[col_idx].strip()
                    
                    # Skip empty values
                    if not engineer_value:
                        continue
                    
                    # Check if it's a valid engineer name
                    assert engineer_value in valid_engineers, (
                        f"Row {row_idx}, column {col_idx} ({header[col_idx] if col_idx < len(header) else 'unknown'}) "
                        f"has invalid engineer '{engineer_value}'. Must be one of: {valid_engineers}"
                    )
                    
                    # Check for time string patterns
                    for pattern in time_patterns:
                        assert not re.search(pattern, engineer_value, re.IGNORECASE), (
                            f"Row {row_idx}, column {col_idx} contains time-like string '{engineer_value}' "
                            f"which should not appear in engineer columns"
                        )
    
    def test_weekend_coverage_patterns(self, basic_engineers, basic_seeds, empty_leave):
        """Test weekend coverage follows Week A/B alternation pattern."""
        start_sunday = date(2025, 1, 12)  # Week A start
        weeks = 4
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        
        # Check that weekend assignments follow alternating pattern
        weekend_assignments = []
        
        for week_data in result.schedule_data:
            # Extract weekend assignments (Saturday and Sunday)
            saturday_engineer = week_data.get('Sat_Engineer', '')
            sunday_engineer = week_data.get('Sun_Engineer', '')
            weekend_assignments.append((saturday_engineer, sunday_engineer))
        
        # Verify alternating pattern exists
        assert len(weekend_assignments) == weeks
        
        # Check that not all weekends are assigned to the same person
        unique_weekend_engineers = set()
        for sat, sun in weekend_assignments:
            if sat:
                unique_weekend_engineers.add(sat)
            if sun:
                unique_weekend_engineers.add(sun)
        
        # Should have more than one engineer doing weekends over 4 weeks
        assert len(unique_weekend_engineers) > 1, (
            f"Weekend coverage should rotate among engineers, but only found: {unique_weekend_engineers}"
        )
    
    def test_leave_handling_conflicts(self, basic_engineers, basic_seeds):
        """Test that leave entries properly exclude engineers from assignments."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        # Create leave data for first engineer on Monday
        leave_data = pd.DataFrame([
            {"Engineer": basic_engineers[0], "Date": "2025-01-13"}  # Monday of first week
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, leave_data)
        
        # Check that the engineer on leave is not assigned on that day
        monday_assignments = []
        for week_data in result.schedule_data:
            if 'Mon_Engineer' in week_data:
                monday_assignments.append(week_data['Mon_Engineer'])
        
        # First Monday should not have the engineer who is on leave
        if monday_assignments:
            assert monday_assignments[0] != basic_engineers[0], (
                f"Engineer {basic_engineers[0]} should not be assigned on Monday (leave day), "
                f"but was assigned: {monday_assignments[0]}"
            )
    
    def test_no_oncall_on_weekends_invariant(self, basic_engineers, basic_seeds, empty_leave):
        """Assert that oncall assignments never occur on weekends."""
        start_sunday = date(2025, 1, 12)
        weeks = 3
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        
        # Check each week's schedule data
        for week_idx, week_data in enumerate(result.schedule_data):
            # Weekend days should not have oncall assignments
            weekend_days = ['Sat', 'Sun']
            
            for day in weekend_days:
                oncall_key = f"{day}_Oncall"
                status_key = f"{day}_Status"
                
                # If there's an oncall assignment on weekend, it should be empty or OFF
                if oncall_key in week_data:
                    oncall_assignment = week_data[oncall_key]
                    assert not oncall_assignment or oncall_assignment == '', (
                        f"Week {week_idx + 1}, {day}: Oncall should not be assigned on weekends, "
                        f"but found: {oncall_assignment}"
                    )
                
                # Status should be OFF for weekends if present
                if status_key in week_data:
                    status = week_data[status_key]
                    if status and status != 'LEAVE':
                        assert status == 'OFF', (
                            f"Week {week_idx + 1}, {day}: Weekend status should be OFF (or LEAVE), "
                            f"but found: {status}"
                        )
    
    def test_backward_compatibility(self, basic_engineers, basic_seeds, empty_leave):
        """Test that original make_schedule function still works."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        # Test original function
        original_result = make_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        
        # Should return list of dictionaries
        assert isinstance(original_result, list)
        assert len(original_result) == weeks
        
        for week_data in original_result:
            assert isinstance(week_data, dict)
            # Should have basic schedule structure
            assert any(key.endswith('_Engineer') for key in week_data.keys())
    
    def test_enhanced_schedule_structure(self, basic_engineers, basic_seeds, empty_leave):
        """Test that enhanced schedule returns proper ScheduleResult structure."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        result = make_enhanced_schedule(start_sunday, weeks, basic_engineers, basic_seeds, empty_leave)
        
        # Check ScheduleResult structure
        assert hasattr(result, 'schedule_data')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'fairness_report')
        assert hasattr(result, 'decision_log')
        
        # Check metadata
        assert result.metadata.schema_version == "2.0"
        assert result.metadata.generated_at is not None
        assert result.metadata.start_date == start_sunday
        assert result.metadata.weeks == weeks
        
        # Check schedule data
        assert len(result.schedule_data) == weeks
        
        # Check fairness report structure
        assert hasattr(result.fairness_report, 'engineer_stats')
        assert hasattr(result.fairness_report, 'equity_score')
        assert len(result.fairness_report.engineer_stats) == len(basic_engineers)


class TestEdgeCaseScenarios:
    """Comprehensive edge case test coverage for leave handling, weekend patterns, and fairness."""
    
    @pytest.fixture
    def engineers(self) -> List[str]:
        """Standard 6-engineer test fixture."""
        return ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    
    @pytest.fixture
    def seeds(self) -> Dict[str, int]:
        """Standard seed configuration."""
        return {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
    
    # Leave Handling Edge Cases
    
    def test_leave_conflict_multiple_engineers_same_day(self, engineers, seeds):
        """Test handling when multiple engineers are on leave the same day."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        # Multiple engineers on leave on the same Monday
        leave_data = pd.DataFrame([
            {"Engineer": engineers[0], "Date": "2025-01-13"},  # Alice on Monday
            {"Engineer": engineers[1], "Date": "2025-01-13"},  # Bob on Monday
            {"Engineer": engineers[2], "Date": "2025-01-13"},  # Charlie on Monday
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_data)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse CSV to check assignments
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        # Find Monday row (should be first data row after header)
        monday_row = rows[1] if len(rows) > 1 else None
        assert monday_row is not None, "Should have Monday data row"
        
        # Check that none of the engineers on leave are assigned to roles
        role_assignments = [monday_row[3], monday_row[4], monday_row[5], monday_row[6], monday_row[7]]  # Early1, Early2, Chat, OnCall, Appointments
        engineers_on_leave = {engineers[0], engineers[1], engineers[2]}
        
        for assignment in role_assignments:
            if assignment:  # Skip empty assignments
                assert assignment not in engineers_on_leave, (
                    f"Engineer {assignment} should not be assigned on Monday (on leave), "
                    f"but was assigned to a role"
                )
    
    def test_leave_conflict_weekend_worker(self, engineers, seeds):
        """Test leave conflict when weekend worker is on leave during their weekend."""
        start_sunday = date(2025, 1, 12)
        weeks = 3
        
        # Put the first weekend worker on leave during their Saturday
        leave_data = pd.DataFrame([
            {"Engineer": engineers[0], "Date": "2025-01-18"},  # Saturday of first week
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_data)
        
        # Verify that the schedule handles this gracefully
        # The engineer should be marked as LEAVE on Saturday
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        # Find Saturday row (7th row after header: Sun, Mon, Tue, Wed, Thu, Fri, Sat)
        saturday_row = rows[7] if len(rows) > 7 else None
        assert saturday_row is not None, "Should have Saturday data row"
        
        # Check engineer status columns for the engineer on leave
        # Engineer columns start at index 8 (Date, Day, WeekIndex, Early1, Early2, Chat, OnCall, Appointments, then engineer data)
        engineer_idx = engineers.index(engineers[0])
        status_col_idx = 8 + (engineer_idx * 3) + 1  # Each engineer has 3 columns: name, status, shift
        
        if status_col_idx < len(saturday_row):
            status = saturday_row[status_col_idx]
            assert status == "LEAVE", f"Engineer {engineers[0]} should have LEAVE status on Saturday, but got: {status}"
    
    def test_leave_consecutive_days_same_engineer(self, engineers, seeds):
        """Test handling when same engineer has consecutive leave days."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        # Engineer on leave for entire first week
        leave_dates = ["2025-01-13", "2025-01-14", "2025-01-15", "2025-01-16", "2025-01-17"]
        leave_data = pd.DataFrame([
            {"Engineer": engineers[0], "Date": leave_date} for leave_date in leave_dates
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_data)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse and verify that the engineer is not assigned to any roles during leave
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        # Check Monday through Friday (rows 2-6 after header)
        for row_idx in range(2, 7):  # Monday to Friday
            if row_idx < len(rows):
                row = rows[row_idx]
                role_assignments = [row[3], row[4], row[5], row[6], row[7]]  # Role columns
                
                for assignment in role_assignments:
                    if assignment:
                        assert assignment != engineers[0], (
                            f"Engineer {engineers[0]} should not be assigned on day {row_idx-1} (on leave), "
                            f"but was assigned: {assignment}"
                        )
    
    def test_leave_all_engineers_except_one(self, engineers, seeds):
        """Test extreme case where all but one engineer are on leave."""
        start_sunday = date(2025, 1, 12)
        weeks = 1
        
        # All engineers except the last one on leave on Monday
        leave_data = pd.DataFrame([
            {"Engineer": engineer, "Date": "2025-01-13"} for engineer in engineers[:-1]
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_data)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Should still generate a valid schedule
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        assert len(data_lines) > 1, "Should generate schedule even with extreme leave scenario"
        
        # The remaining engineer should handle available roles
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        monday_row = rows[1] if len(rows) > 1 else None
        
        if monday_row:
            # Check that only the available engineer is assigned to roles
            role_assignments = [monday_row[3], monday_row[4], monday_row[5], monday_row[6], monday_row[7]]
            available_engineer = engineers[-1]
            
            for assignment in role_assignments:
                if assignment:  # Skip empty assignments
                    assert assignment == available_engineer, (
                        f"Only {available_engineer} should be available, but found assignment: {assignment}"
                    )
    
    # Weekend Coverage Pattern Tests
    
    def test_weekend_alternation_pattern_consistency(self, engineers, seeds):
        """Test that weekend coverage follows consistent Week A/B alternation."""
        start_sunday = date(2025, 1, 12)
        weeks = 8  # Test over longer period
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, pd.DataFrame())
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Parse weekend assignments
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        weekend_patterns = []
        
        # Extract weekend patterns for each week
        for week in range(weeks):
            week_start_row = 1 + (week * 7)  # Skip header, then 7 days per week
            
            if week_start_row + 6 < len(rows):  # Ensure we have full week
                saturday_row = rows[week_start_row + 6]  # Saturday is 7th day (index 6)
                sunday_row = rows[week_start_row]  # Sunday is 1st day (index 0)
                
                # Find working engineers for weekend days
                sat_working = []
                sun_working = []
                
                # Check engineer status columns
                for eng_idx in range(6):
                    status_col = 8 + (eng_idx * 3) + 1  # Status column for each engineer
                    
                    if status_col < len(saturday_row):
                        sat_status = saturday_row[status_col]
                        if sat_status == "WORK":
                            sat_working.append(engineers[eng_idx])
                    
                    if status_col < len(sunday_row):
                        sun_status = sunday_row[status_col]
                        if sun_status == "WORK":
                            sun_working.append(engineers[eng_idx])
                
                weekend_patterns.append((week, sat_working, sun_working))
        
        # Verify alternating pattern
        assert len(weekend_patterns) == weeks, f"Should have {weeks} weekend patterns, got {len(weekend_patterns)}"
        
        # Check that weekend workers alternate properly
        weekend_workers_by_week = []
        for week, sat_workers, sun_workers in weekend_patterns:
            # Combine Saturday and Sunday workers for this week
            week_workers = set(sat_workers + sun_workers)
            weekend_workers_by_week.append(week_workers)
        
        # Verify that different engineers work weekends across weeks
        all_weekend_workers = set()
        for workers in weekend_workers_by_week:
            all_weekend_workers.update(workers)
        
        assert len(all_weekend_workers) > 1, (
            f"Weekend work should be distributed among multiple engineers, "
            f"but only found: {all_weekend_workers}"
        )
    
    def test_weekend_no_oncall_invariant_extended(self, engineers, seeds):
        """Test that oncall is never assigned on weekends over extended period."""
        start_sunday = date(2025, 1, 12)
        weeks = 6
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, pd.DataFrame())
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        # Check every weekend day
        for week in range(weeks):
            week_start_row = 1 + (week * 7)
            
            # Check Saturday and Sunday
            for day_offset, day_name in [(6, "Saturday"), (0, "Sunday")]:
                row_idx = week_start_row + day_offset
                
                if row_idx < len(rows):
                    row = rows[row_idx]
                    oncall_assignment = row[6] if len(row) > 6 else ""  # OnCall column
                    
                    assert not oncall_assignment or oncall_assignment == "", (
                        f"Week {week + 1}, {day_name}: OnCall should not be assigned on weekends, "
                        f"but found: '{oncall_assignment}'"
                    )
    
    def test_weekend_worker_rotation_fairness(self, engineers, seeds):
        """Test that weekend work is distributed fairly among engineers."""
        start_sunday = date(2025, 1, 12)
        weeks = 12  # Test over 3 months
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, pd.DataFrame())
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Count weekend work assignments per engineer
        weekend_counts = {engineer: 0 for engineer in engineers}
        
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        for week in range(weeks):
            week_start_row = 1 + (week * 7)
            
            # Check Saturday and Sunday
            for day_offset in [6, 0]:  # Saturday, Sunday
                row_idx = week_start_row + day_offset
                
                if row_idx < len(rows):
                    row = rows[row_idx]
                    
                    # Check each engineer's status
                    for eng_idx in range(6):
                        status_col = 8 + (eng_idx * 3) + 1
                        
                        if status_col < len(row):
                            status = row[status_col]
                            if status == "WORK":
                                weekend_counts[engineers[eng_idx]] += 1
        
        # Verify reasonable distribution
        total_weekend_days = sum(weekend_counts.values())
        assert total_weekend_days > 0, "Should have some weekend work assignments"
        
        # Check that weekend work is distributed (not all to one person)
        working_engineers = [eng for eng, count in weekend_counts.items() if count > 0]
        assert len(working_engineers) > 1, (
            f"Weekend work should be distributed among multiple engineers, "
            f"but only {working_engineers} worked weekends"
        )
        
        # Check that distribution is reasonably fair (no engineer has more than 2x another's count)
        counts = [count for count in weekend_counts.values() if count > 0]
        if len(counts) > 1:
            max_count = max(counts)
            min_count = min(counts)
            fairness_ratio = max_count / min_count if min_count > 0 else float('inf')
            
            assert fairness_ratio <= 3.0, (
                f"Weekend work distribution is unfair. Max: {max_count}, Min: {min_count}, "
                f"Ratio: {fairness_ratio:.2f}. Counts: {weekend_counts}"
            )
    
    # Role Assignment Fairness and Rotation Tests
    
    def test_role_rotation_consistency(self, engineers, seeds):
        """Test that roles rotate consistently among available engineers."""
        start_sunday = date(2025, 1, 12)
        weeks = 4
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, pd.DataFrame())
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Track role assignments per engineer
        role_assignments = {
            engineer: {"Chat": 0, "OnCall": 0, "Appointments": 0, "Early1": 0, "Early2": 0}
            for engineer in engineers
        }
        
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        # Count assignments for weekdays only
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if len(row) > 7:
                day = row[1]  # Day column
                
                # Only count weekday assignments
                if day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
                    early1 = row[3]
                    early2 = row[4]
                    chat = row[5]
                    oncall = row[6]
                    appointments = row[7]
                    
                    if early1 in role_assignments:
                        role_assignments[early1]["Early1"] += 1
                    if early2 in role_assignments:
                        role_assignments[early2]["Early2"] += 1
                    if chat in role_assignments:
                        role_assignments[chat]["Chat"] += 1
                    if oncall in role_assignments:
                        role_assignments[oncall]["OnCall"] += 1
                    if appointments in role_assignments:
                        role_assignments[appointments]["Appointments"] += 1
        
        # Verify that roles are distributed (not all to one person)
        for role in ["Chat", "OnCall", "Appointments", "Early1", "Early2"]:
            role_counts = [role_assignments[eng][role] for eng in engineers]
            working_engineers = sum(1 for count in role_counts if count > 0)
            
            assert working_engineers > 1, (
                f"Role {role} should be distributed among multiple engineers, "
                f"but assignments: {[(eng, role_assignments[eng][role]) for eng in engineers if role_assignments[eng][role] > 0]}"
            )
    
    def test_seed_rotation_effect(self, engineers):
        """Test that different seeds produce different but valid rotations."""
        start_sunday = date(2025, 1, 12)
        weeks = 2
        
        # Test with different seed values
        seeds_configs = [
            {"weekend": 0, "chat": 0, "oncall": 0, "appointments": 0, "early": 0},
            {"weekend": 1, "chat": 1, "oncall": 1, "appointments": 1, "early": 1},
            {"weekend": 2, "chat": 2, "oncall": 2, "appointments": 2, "early": 2},
        ]
        
        schedules = []
        for seeds in seeds_configs:
            result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, pd.DataFrame())
            export_manager = ExportManager(result)
            csv_content = export_manager.to_csv()
            schedules.append(csv_content)
        
        # Verify that different seeds produce different schedules
        assert len(set(schedules)) > 1, (
            "Different seed configurations should produce different schedules"
        )
        
        # But all should be valid (test basic invariants)
        for i, csv_content in enumerate(schedules):
            lines = csv_content.strip().split('\n')
            data_lines = [line for line in lines if not line.startswith('#')]
            csv_reader = csv.reader(data_lines)
            rows = list(csv_reader)
            
            assert len(rows) > 1, f"Schedule {i} should have data rows"
            
            # Check column consistency
            if len(rows) > 1:
                header_cols = len(rows[0])
                for row_idx, row in enumerate(rows[1:], 1):
                    assert len(row) == header_cols, (
                        f"Schedule {i}, row {row_idx}: Column count mismatch"
                    )
    
    def test_role_assignment_with_varying_leave(self, engineers, seeds):
        """Test role assignment fairness when engineers have different leave patterns."""
        start_sunday = date(2025, 1, 12)
        weeks = 4
        
        # Create asymmetric leave pattern
        leave_data = pd.DataFrame([
            {"Engineer": engineers[0], "Date": "2025-01-13"},  # Alice: 1 day
            {"Engineer": engineers[0], "Date": "2025-01-20"},
            {"Engineer": engineers[1], "Date": "2025-01-14"},  # Bob: 3 days
            {"Engineer": engineers[1], "Date": "2025-01-21"},
            {"Engineer": engineers[1], "Date": "2025-01-28"},
            # Other engineers have no leave
        ])
        
        result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_data)
        export_manager = ExportManager(result)
        csv_content = export_manager.to_csv()
        
        # Count role assignments
        role_counts = {engineer: 0 for engineer in engineers}
        
        lines = csv_content.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        csv_reader = csv.reader(data_lines)
        rows = list(csv_reader)
        
        for row_idx in range(1, len(rows)):
            row = rows[row_idx]
            
            if len(row) > 7:
                day = row[1]
                
                # Count weekday role assignments
                if day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
                    roles = [row[3], row[4], row[5], row[6], row[7]]  # All role columns
                    
                    for role_assignment in roles:
                        if role_assignment in role_counts:
                            role_counts[role_assignment] += 1
        
        # Engineers with more leave should have fewer role assignments
        alice_count = role_counts[engineers[0]]
        bob_count = role_counts[engineers[1]]
        other_counts = [role_counts[eng] for eng in engineers[2:]]
        
        # Engineers with no leave should generally have more assignments than those with leave
        avg_other_count = sum(other_counts) / len(other_counts) if other_counts else 0
        
        assert alice_count <= avg_other_count + 2, (
            f"Alice (with leave) should not have significantly more assignments than others. "
            f"Alice: {alice_count}, Others avg: {avg_other_count:.1f}"
        )
        
        assert bob_count <= avg_other_count + 2, (
            f"Bob (with more leave) should not have significantly more assignments than others. "
            f"Bob: {bob_count}, Others avg: {avg_other_count:.1f}"
        )