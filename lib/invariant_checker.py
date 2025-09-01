"""
Scheduling invariant validation and monitoring.
Checks for violations of scheduling rules and logs them for debugging.
"""

import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class InvariantType(Enum):
    """Types of scheduling invariants that can be violated."""
    NO_ONCALL_WEEKENDS = "no_oncall_weekends"
    STATUS_FIELD_INTEGRITY = "status_field_integrity"
    ENGINEER_FIELD_INTEGRITY = "engineer_field_integrity"
    CSV_COLUMN_COUNT = "csv_column_count"
    WEEKEND_COVERAGE_PATTERN = "weekend_coverage_pattern"
    FAIRNESS_DISTRIBUTION = "fairness_distribution"


@dataclass
class InvariantViolation:
    """Represents a scheduling invariant violation."""
    violation_type: InvariantType
    severity: str  # "error", "warning", "info"
    message: str
    details: Dict[str, Any]
    affected_dates: List[str] = None
    affected_engineers: List[str] = None


class ScheduleInvariantChecker:
    """
    Validates scheduling invariants and tracks violations.
    Used for monitoring schedule quality and debugging issues.
    """
    
    def __init__(self, engineers: List[str]):
        self.engineers = engineers
        self.violations: List[InvariantViolation] = []
    
    def check_all_invariants(self, schedule_df: pd.DataFrame, csv_content: str = None) -> List[InvariantViolation]:
        """
        Run all invariant checks on a schedule.
        Returns list of violations found.
        """
        self.violations = []
        
        # Check core scheduling invariants
        self._check_no_oncall_weekends(schedule_df)
        self._check_status_field_integrity(schedule_df)
        self._check_engineer_field_integrity(schedule_df)
        self._check_weekend_coverage_pattern(schedule_df)
        
        # Check CSV format if provided
        if csv_content:
            self._check_csv_column_count(csv_content)
        
        return self.violations
    
    def check_fairness_distribution(self, fairness_report: Dict[str, Any]) -> List[InvariantViolation]:
        """
        Check fairness distribution for equity violations.
        """
        violations = []
        
        if "engineer_stats" not in fairness_report:
            return violations
        
        engineer_stats = fairness_report["engineer_stats"]
        
        # Check for extreme imbalances in role assignments
        role_counts = {}
        for engineer, stats in engineer_stats.items():
            for role, count in stats.items():
                if role not in role_counts:
                    role_counts[role] = []
                role_counts[role].append(count)
        
        # Check each role for fairness
        for role, counts in role_counts.items():
            if len(counts) < 2:
                continue
                
            min_count = min(counts)
            max_count = max(counts)
            delta = max_count - min_count
            
            # Flag if delta is too large (more than 2 assignments difference)
            if delta > 2:
                violation = InvariantViolation(
                    violation_type=InvariantType.FAIRNESS_DISTRIBUTION,
                    severity="warning",
                    message=f"Unfair distribution in {role} assignments",
                    details={
                        "role": role,
                        "min_assignments": min_count,
                        "max_assignments": max_count,
                        "delta": delta,
                        "threshold": 2
                    }
                )
                violations.append(violation)
        
        return violations
    
    def _check_no_oncall_weekends(self, schedule_df: pd.DataFrame):
        """Check that no oncall assignments occur on weekends."""
        weekend_oncalls = []
        
        for _, row in schedule_df.iterrows():
            # Check if it's a weekend (Saturday or Sunday)
            if row.get('Day') in ['Saturday', 'Sunday']:
                oncall_engineer = row.get('OnCall', '').strip()
                if oncall_engineer and oncall_engineer != '':
                    weekend_oncalls.append({
                        'date': str(row.get('Date', '')),
                        'day': row.get('Day', ''),
                        'engineer': oncall_engineer
                    })
        
        if weekend_oncalls:
            violation = InvariantViolation(
                violation_type=InvariantType.NO_ONCALL_WEEKENDS,
                severity="error",
                message=f"Found {len(weekend_oncalls)} oncall assignments on weekends",
                details={"weekend_oncalls": weekend_oncalls},
                affected_dates=[item['date'] for item in weekend_oncalls],
                affected_engineers=[item['engineer'] for item in weekend_oncalls]
            )
            self.violations.append(violation)
    
    def _check_status_field_integrity(self, schedule_df: pd.DataFrame):
        """Check that Status fields only contain valid values."""
        valid_statuses = {'WORK', 'OFF', 'LEAVE', ''}
        invalid_statuses = []
        
        # Check all status columns (Status 1, Status 2, etc.)
        status_columns = [col for col in schedule_df.columns if col.startswith('Status')]
        
        for _, row in schedule_df.iterrows():
            for status_col in status_columns:
                status_value = str(row.get(status_col, '')).strip()
                
                # Check if status value is actually an engineer name
                if status_value in self.engineers:
                    invalid_statuses.append({
                        'date': str(row.get('Date', '')),
                        'column': status_col,
                        'value': status_value,
                        'issue': 'engineer_name_in_status'
                    })
                # Check if status value is invalid
                elif status_value not in valid_statuses:
                    invalid_statuses.append({
                        'date': str(row.get('Date', '')),
                        'column': status_col,
                        'value': status_value,
                        'issue': 'invalid_status_value'
                    })
        
        if invalid_statuses:
            violation = InvariantViolation(
                violation_type=InvariantType.STATUS_FIELD_INTEGRITY,
                severity="error",
                message=f"Found {len(invalid_statuses)} invalid status field values",
                details={"invalid_statuses": invalid_statuses},
                affected_dates=[item['date'] for item in invalid_statuses]
            )
            self.violations.append(violation)
    
    def _check_engineer_field_integrity(self, schedule_df: pd.DataFrame):
        """Check that Engineer columns only contain known engineer names."""
        invalid_engineers = []
        
        # Check engineer columns (typically columns 2-6 in the CSV)
        engineer_columns = [col for col in schedule_df.columns if col.startswith(('1)', '2)', '3)', '4)', '5)', '6)'))]
        
        for _, row in schedule_df.iterrows():
            for eng_col in engineer_columns:
                engineer_value = str(row.get(eng_col, '')).strip()
                
                # Skip empty values
                if not engineer_value:
                    continue
                
                # Check if engineer value looks like a time string
                if ':' in engineer_value or engineer_value.isdigit():
                    invalid_engineers.append({
                        'date': str(row.get('Date', '')),
                        'column': eng_col,
                        'value': engineer_value,
                        'issue': 'time_string_in_engineer_field'
                    })
                # Check if engineer value is not in known engineers list
                elif engineer_value not in self.engineers:
                    invalid_engineers.append({
                        'date': str(row.get('Date', '')),
                        'column': eng_col,
                        'value': engineer_value,
                        'issue': 'unknown_engineer_name'
                    })
        
        if invalid_engineers:
            violation = InvariantViolation(
                violation_type=InvariantType.ENGINEER_FIELD_INTEGRITY,
                severity="error",
                message=f"Found {len(invalid_engineers)} invalid engineer field values",
                details={"invalid_engineers": invalid_engineers},
                affected_dates=[item['date'] for item in invalid_engineers]
            )
            self.violations.append(violation)
    
    def _check_weekend_coverage_pattern(self, schedule_df: pd.DataFrame):
        """Check weekend coverage follows Week A/B alternation pattern."""
        weekend_violations = []
        
        # Group by week and check weekend patterns
        if 'WeekIndex' in schedule_df.columns:
            for week_idx in schedule_df['WeekIndex'].unique():
                week_data = schedule_df[schedule_df['WeekIndex'] == week_idx]
                weekend_data = week_data[week_data['Day'].isin(['Saturday', 'Sunday'])]
                
                if len(weekend_data) == 2:  # Should have both Saturday and Sunday
                    saturday_engineers = self._get_weekend_engineers(weekend_data[weekend_data['Day'] == 'Saturday'].iloc[0])
                    sunday_engineers = self._get_weekend_engineers(weekend_data[weekend_data['Day'] == 'Sunday'].iloc[0])
                    
                    # Check if weekend engineers are consistent within the week
                    if saturday_engineers != sunday_engineers:
                        weekend_violations.append({
                            'week': week_idx,
                            'issue': 'inconsistent_weekend_engineers',
                            'saturday_engineers': saturday_engineers,
                            'sunday_engineers': sunday_engineers
                        })
        
        if weekend_violations:
            violation = InvariantViolation(
                violation_type=InvariantType.WEEKEND_COVERAGE_PATTERN,
                severity="warning",
                message=f"Found {len(weekend_violations)} weekend coverage pattern violations",
                details={"weekend_violations": weekend_violations}
            )
            self.violations.append(violation)
    
    def _check_csv_column_count(self, csv_content: str):
        """Check that all CSV rows have consistent column counts."""
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return
        
        # Get expected column count from header
        header_cols = len(lines[0].split(','))
        inconsistent_rows = []
        
        for i, line in enumerate(lines[1:], start=2):  # Skip header, start line numbers at 2
            if line.strip():  # Skip empty lines
                row_cols = len(line.split(','))
                if row_cols != header_cols:
                    inconsistent_rows.append({
                        'line_number': i,
                        'expected_columns': header_cols,
                        'actual_columns': row_cols,
                        'content': line[:100] + '...' if len(line) > 100 else line
                    })
        
        if inconsistent_rows:
            violation = InvariantViolation(
                violation_type=InvariantType.CSV_COLUMN_COUNT,
                severity="error",
                message=f"Found {len(inconsistent_rows)} CSV rows with incorrect column count",
                details={"inconsistent_rows": inconsistent_rows}
            )
            self.violations.append(violation)
    
    def _get_weekend_engineers(self, weekend_row) -> List[str]:
        """Extract engineers assigned to weekend coverage from a row."""
        engineers = []
        
        # Check typical weekend assignment columns
        weekend_columns = ['Early1', 'Early2', 'Chat']
        for col in weekend_columns:
            engineer = str(weekend_row.get(col, '')).strip()
            if engineer and engineer in self.engineers:
                engineers.append(engineer)
        
        return sorted(engineers)
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Get a summary of all violations found."""
        summary = {
            'total_violations': len(self.violations),
            'by_severity': {},
            'by_type': {},
            'critical_issues': []
        }
        
        for violation in self.violations:
            # Count by severity
            severity = violation.severity
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by type
            vtype = violation.violation_type.value
            summary['by_type'][vtype] = summary['by_type'].get(vtype, 0) + 1
            
            # Collect critical issues
            if violation.severity == 'error':
                summary['critical_issues'].append({
                    'type': vtype,
                    'message': violation.message
                })
        
        return summary