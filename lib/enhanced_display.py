"""
Enhanced schedule display formatting with improved role visibility and shift time indicators.
Implements enhanced DataFrame formatting, role clarity, and export enhancements.
"""

import pandas as pd
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
import re

from models import ScheduleResult, FairnessReport, DecisionEntry, EngineerStats


class EnhancedScheduleFormatter:
    """Enhanced formatter for schedule display with improved role visibility."""
    
    def __init__(self, schedule_result: ScheduleResult):
        """Initialize with a complete schedule result."""
        self.result = schedule_result
        self.schedule_df = self._convert_schedule_data_to_dataframe()
    
    def _convert_schedule_data_to_dataframe(self) -> pd.DataFrame:
        """Convert schedule data back to DataFrame for processing."""
        schedule_data = self.result.schedule_data
        if "rows" in schedule_data and "headers" in schedule_data:
            return pd.DataFrame(schedule_data["rows"], columns=schedule_data["headers"])
        return pd.DataFrame()
    
    def format_enhanced_dataframe(self) -> pd.DataFrame:
        """
        Create enhanced DataFrame with improved role visibility and shift time formatting.
        
        Requirements addressed:
        - 5.1: Improve existing DataFrame output to clearly show all role assignments
        - 5.1: Add better formatting for shift times (06:45-15:45 vs 08:00-17:00 vs Weekend)
        - 5.3: Ensure WORK/OFF/LEAVE status is clearly displayed for each engineer
        """
        if self.schedule_df.empty:
            return pd.DataFrame()
        
        df = self.schedule_df.copy()
        
        # Enhance role assignment display
        df = self._enhance_role_assignments(df)
        
        # Improve shift time formatting
        df = self._enhance_shift_time_display(df)
        
        # Clarify status display
        df = self._enhance_status_display(df)
        
        # Add role summary columns
        df = self._add_role_summary_columns(df)
        
        return df
    
    def _enhance_role_assignments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance role assignment visibility with clear indicators."""
        # Create a comprehensive role assignment column
        role_assignments = []
        
        for _, row in df.iterrows():
            roles = []
            
            # Collect all role assignments for the day
            if row.get("Early1"):
                roles.append(f"Early1: {row['Early1']}")
            if row.get("Early2"):
                roles.append(f"Early2: {row['Early2']}")
            if row.get("Chat"):
                roles.append(f"Chat: {row['Chat']}")
            if row.get("OnCall"):
                roles.append(f"OnCall: {row['OnCall']}")
            if row.get("Appointments"):
                roles.append(f"Appt: {row['Appointments']}")
            
            role_assignments.append(" | ".join(roles) if roles else "No roles assigned")
        
        # Insert role summary after the basic columns
        insert_position = 8  # After Appointments column
        df.insert(insert_position, "Role Summary", role_assignments)
        
        return df
    
    def _enhance_shift_time_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """Improve shift time formatting with clear indicators."""
        # Find all shift columns (Shift 1, Shift 2, etc.)
        shift_columns = [col for col in df.columns if col.startswith("Shift ")]
        
        for shift_col in shift_columns:
            if shift_col in df.columns:
                # Enhance shift time formatting
                df[shift_col] = df[shift_col].apply(self._format_shift_time)
        
        return df
    
    def _format_shift_time(self, shift_value: str) -> str:
        """Format shift time with enhanced clarity."""
        if not shift_value or shift_value == "":
            return "Not Working"
        
        # Standardize early shift format
        if "06:45" in shift_value or shift_value == "06:45-15:45":
            return "Early (06:45-15:45)"
        
        # Standardize regular shift format
        if "08:00" in shift_value or shift_value == "08:00-17:00":
            return "Regular (08:00-17:00)"
        
        # Enhanced weekend formatting
        if "Weekend" in shift_value:
            if "Weekend-A" in shift_value:
                return "Weekend Pattern A (Sat: Mon-Thu+Sat)"
            elif "Weekend-B" in shift_value:
                return "Weekend Pattern B (Sun: Sun+Tue-Fri)"
            else:
                return "Weekend Shift"
        
        # Return original if no enhancement needed
        return shift_value
    
    def _enhance_status_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance status display with clear indicators."""
        # Find all status columns (Status 1, Status 2, etc.)
        status_columns = [col for col in df.columns if col.startswith("Status ")]
        
        for status_col in status_columns:
            if status_col in df.columns:
                # Enhance status formatting
                df[status_col] = df[status_col].apply(self._format_status)
        
        return df
    
    def _format_status(self, status_value: str) -> str:
        """Format status with enhanced clarity."""
        status_map = {
            "WORK": "✓ Working",
            "OFF": "○ Off Duty", 
            "LEAVE": "✗ On Leave",
            "": "○ Off Duty"
        }
        
        return status_map.get(status_value, status_value)
    
    def _add_role_summary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add summary columns for better role visibility."""
        # Add daily role count
        role_counts = []
        working_engineers = []
        
        for _, row in df.iterrows():
            # Count assigned roles
            roles = [row.get("Early1"), row.get("Early2"), row.get("Chat"), 
                    row.get("OnCall"), row.get("Appointments")]
            active_roles = [r for r in roles if r and r.strip()]
            role_counts.append(len(active_roles))
            
            # Count working engineers
            status_columns = [col for col in df.columns if col.startswith("Status ")]
            working_count = 0
            for status_col in status_columns:
                if row.get(status_col) == "WORK" or "Working" in str(row.get(status_col, "")):
                    working_count += 1
            working_engineers.append(working_count)
        
        # Insert summary columns
        df.insert(len(df.columns), "Active Roles", role_counts)
        df.insert(len(df.columns), "Working Engineers", working_engineers)
        
        return df
    
    def generate_role_assignment_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive role assignment summary for exports.
        
        Requirements addressed:
        - 5.2: Add role summary sections to exported schedules
        """
        if self.schedule_df.empty:
            return {}
        
        summary = {
            "total_days": len(self.schedule_df),
            "role_distribution": {},
            "engineer_workload": {},
            "shift_patterns": {},
            "coverage_analysis": {}
        }
        
        # Analyze role distribution
        roles = ["Early1", "Early2", "Chat", "OnCall", "Appointments"]
        for role in roles:
            if role in self.schedule_df.columns:
                role_assignments = self.schedule_df[role].value_counts()
                summary["role_distribution"][role] = role_assignments.to_dict()
        
        # Analyze engineer workload
        engineer_columns = [col for col in self.schedule_df.columns if ") Engineer" in col]
        status_columns = [col for col in self.schedule_df.columns if col.startswith("Status ")]
        
        for i, eng_col in enumerate(engineer_columns):
            if i < len(status_columns):
                status_col = status_columns[i]
                engineer_name = self.schedule_df[eng_col].iloc[0] if not self.schedule_df.empty else f"Engineer {i+1}"
                
                work_days = (self.schedule_df[status_col] == "WORK").sum()
                leave_days = (self.schedule_df[status_col] == "LEAVE").sum()
                off_days = (self.schedule_df[status_col] == "OFF").sum()
                
                summary["engineer_workload"][engineer_name] = {
                    "work_days": int(work_days),
                    "leave_days": int(leave_days),
                    "off_days": int(off_days),
                    "total_days": len(self.schedule_df)
                }
        
        # Analyze shift patterns
        shift_columns = [col for col in self.schedule_df.columns if col.startswith("Shift ")]
        shift_pattern_counts = {}
        
        for shift_col in shift_columns:
            patterns = self.schedule_df[shift_col].value_counts()
            shift_pattern_counts.update(patterns.to_dict())
        
        summary["shift_patterns"] = shift_pattern_counts
        
        # Coverage analysis
        weekdays = self.schedule_df[self.schedule_df["Day"].isin(["Mon", "Tue", "Wed", "Thu", "Fri"])]
        weekends = self.schedule_df[self.schedule_df["Day"].isin(["Sat", "Sun"])]
        
        summary["coverage_analysis"] = {
            "weekday_coverage": {
                "total_weekdays": len(weekdays),
                "avg_roles_per_day": weekdays[roles].notna().sum(axis=1).mean() if not weekdays.empty else 0,
                "min_roles_per_day": weekdays[roles].notna().sum(axis=1).min() if not weekdays.empty else 0,
                "max_roles_per_day": weekdays[roles].notna().sum(axis=1).max() if not weekdays.empty else 0
            },
            "weekend_coverage": {
                "total_weekend_days": len(weekends),
                "avg_roles_per_day": weekends[roles].notna().sum(axis=1).mean() if not weekends.empty else 0,
                "min_roles_per_day": weekends[roles].notna().sum(axis=1).min() if not weekends.empty else 0,
                "max_roles_per_day": weekends[roles].notna().sum(axis=1).max() if not weekends.empty else 0
            }
        }
        
        return summary
    
    def format_for_export(self, export_format: str = "csv") -> Dict[str, Any]:
        """
        Format schedule data for enhanced export with role clarity.
        
        Requirements addressed:
        - 5.2: Enhance existing CSV/XLSX export to include clear role indicators
        - 5.4: Improve schedule readability for end users
        """
        enhanced_df = self.format_enhanced_dataframe()
        role_summary = self.generate_role_assignment_summary()
        
        export_data = {
            "enhanced_schedule": {
                "headers": enhanced_df.columns.tolist(),
                "rows": enhanced_df.values.tolist()
            },
            "role_summary": role_summary,
            "fairness_insights": self._generate_fairness_insights_for_export(),
            "metadata": self._generate_enhanced_metadata()
        }
        
        return export_data
    
    def _generate_fairness_insights_for_export(self) -> Dict[str, Any]:
        """Generate fairness insights formatted for export."""
        fairness_report = self.result.fairness_report
        
        insights = {
            "equity_score": fairness_report.equity_score,
            "equity_interpretation": self._interpret_equity_score(fairness_report.equity_score),
            "role_balance": fairness_report.max_min_deltas,
            "engineer_statistics": {}
        }
        
        # Format engineer statistics for readability
        for name, stats in fairness_report.engineer_stats.items():
            insights["engineer_statistics"][name] = {
                "total_assignments": (stats.oncall_count + stats.weekend_count + 
                                    stats.early_count + stats.chat_count + stats.appointments_count),
                "oncall_assignments": stats.oncall_count,
                "weekend_assignments": stats.weekend_count,
                "early_shift_assignments": stats.early_count,
                "chat_assignments": stats.chat_count,
                "appointments_assignments": stats.appointments_count,
                "work_days": stats.total_work_days,
                "leave_days": stats.leave_days
            }
        
        return insights
    
    def _interpret_equity_score(self, equity_score: float) -> str:
        """Interpret equity score for human readability."""
        if equity_score < 0.1:
            return "Excellent - Very equitable distribution"
        elif equity_score < 0.2:
            return "Good - Reasonably fair distribution"
        elif equity_score < 0.3:
            return "Moderate - Some imbalances present"
        else:
            return "Attention needed - Significant imbalances detected"
    
    def _generate_enhanced_metadata(self) -> Dict[str, Any]:
        """Generate enhanced metadata for export."""
        metadata = asdict(self.result.metadata)
        
        # Add display enhancement information
        metadata["display_enhancements"] = {
            "role_summary_included": True,
            "enhanced_shift_formatting": True,
            "status_indicators": True,
            "coverage_analysis": True
        }
        
        # Add formatting version
        metadata["formatting_version"] = "2.0"
        
        return metadata


def enhance_schedule_display(schedule_result: ScheduleResult) -> ScheduleResult:
    """
    Enhance schedule result with improved display formatting.
    
    Args:
        schedule_result: Original schedule result
    
    Returns:
        Enhanced schedule result with improved formatting
    """
    formatter = EnhancedScheduleFormatter(schedule_result)
    
    # Generate enhanced display data
    enhanced_export_data = formatter.format_for_export()
    
    # Update schedule data with enhanced formatting
    enhanced_schedule_result = ScheduleResult(
        schedule_data=enhanced_export_data["enhanced_schedule"],
        fairness_report=schedule_result.fairness_report,
        decision_log=schedule_result.decision_log,
        metadata=schedule_result.metadata,
        weekend_compensation_tracking=schedule_result.weekend_compensation_tracking,
        fairness_insights=getattr(schedule_result, 'fairness_insights', []),
        schema_version="2.0"
    )
    
    # Add enhanced metadata
    enhanced_schedule_result.schedule_data["role_summary"] = enhanced_export_data["role_summary"]
    enhanced_schedule_result.schedule_data["fairness_insights"] = enhanced_export_data["fairness_insights"]
    enhanced_schedule_result.schedule_data["enhanced_metadata"] = enhanced_export_data["metadata"]
    
    return enhanced_schedule_result


def format_shift_time_display(shift_value: str) -> str:
    """
    Standalone function to format shift times with enhanced clarity.
    
    Requirements addressed:
    - 5.1: Add better formatting for shift times (06:45-15:45 vs 08:00-17:00 vs Weekend)
    """
    if not shift_value or shift_value == "":
        return "Not Working"
    
    # Standardize early shift format
    if "06:45" in shift_value or shift_value == "06:45-15:45":
        return "Early Shift (06:45-15:45)"
    
    # Standardize regular shift format  
    if "08:00" in shift_value or shift_value == "08:00-17:00":
        return "Regular Shift (08:00-17:00)"
    
    # Enhanced weekend formatting
    if "Weekend" in shift_value:
        if "Weekend-A" in shift_value:
            return "Weekend Pattern A (Saturday: Works Mon-Thu+Sat)"
        elif "Weekend-B" in shift_value:
            return "Weekend Pattern B (Sunday: Works Sun+Tue-Fri)"
        else:
            return "Weekend Shift"
    
    # Return original if no enhancement needed
    return shift_value


def format_status_display(status_value: str) -> str:
    """
    Standalone function to format status with enhanced clarity.
    
    Requirements addressed:
    - 5.3: Ensure WORK/OFF/LEAVE status is clearly displayed for each engineer
    """
    status_map = {
        "WORK": "✓ Working",
        "OFF": "○ Off Duty",
        "LEAVE": "✗ On Leave", 
        "": "○ Off Duty"
    }
    
    return status_map.get(status_value, status_value)


def validate_display_formatting(df: pd.DataFrame) -> List[str]:
    """
    Validate that display formatting meets requirements.
    
    Returns:
        List of validation issues found
    """
    issues = []
    
    # Check for role assignment columns
    required_role_columns = ["Early1", "Early2", "Chat", "OnCall", "Appointments"]
    missing_roles = [col for col in required_role_columns if col not in df.columns]
    if missing_roles:
        issues.append(f"Missing role columns: {', '.join(missing_roles)}")
    
    # Check for status columns
    status_columns = [col for col in df.columns if col.startswith("Status ")]
    if not status_columns:
        issues.append("No status columns found")
    
    # Check for shift columns
    shift_columns = [col for col in df.columns if col.startswith("Shift ")]
    if not shift_columns:
        issues.append("No shift columns found")
    
    # Validate shift time formatting
    for shift_col in shift_columns:
        if shift_col in df.columns:
            invalid_shifts = df[shift_col].apply(lambda x: x not in [
                "Early Shift (06:45-15:45)", "Regular Shift (08:00-17:00)", 
                "Weekend Shift", "Weekend Pattern A (Saturday: Works Mon-Thu+Sat)",
                "Weekend Pattern B (Sunday: Works Sun+Tue-Fri)", "Not Working", ""
            ] and x is not None).sum()
            
            if invalid_shifts > 0:
                issues.append(f"Found {invalid_shifts} invalid shift time formats in {shift_col}")
    
    # Validate status formatting
    for status_col in status_columns:
        if status_col in df.columns:
            invalid_statuses = df[status_col].apply(lambda x: x not in [
                "✓ Working", "○ Off Duty", "✗ On Leave", ""
            ] and x is not None).sum()
            
            if invalid_statuses > 0:
                issues.append(f"Found {invalid_statuses} invalid status formats in {status_col}")
    
    return issues