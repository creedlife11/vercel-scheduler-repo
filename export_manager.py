"""
JSON-first export manager that generates all output formats from a single JSON source.
Implements CSV export with RFC 4180 formatting and UTF-8 BOM, and XLSX export with multiple sheets.
"""

import json
import csv
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from dataclasses import asdict

from models import ScheduleResult, FairnessReport, DecisionEntry, ScheduleMetadata, WeekendCompensation
from lib.invariant_checker import ScheduleInvariantChecker
from lib.logging_utils import logger


class ExportManager:
    """Manages all export formats from a single JSON source of truth."""
    
    def __init__(self, schedule_result: ScheduleResult):
        """Initialize with a complete schedule result."""
        self.result = schedule_result
        self._json_cache: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> Dict[str, Any]:
        """Generate the canonical JSON representation."""
        if self._json_cache is None:
            # Add role clarity indicators to schedule data
            enhanced_schedule_data = add_role_clarity_indicators(self.result.schedule_data)
            
            # Generate role assignment report
            role_report = generate_role_assignment_report(enhanced_schedule_data)
            
            self._json_cache = {
                "schemaVersion": self.result.schema_version,
                "metadata": self._serialize_metadata(self.result.metadata),
                "schedule": enhanced_schedule_data,
                "fairnessReport": self._serialize_fairness_report(self.result.fairness_report),
                "decisionLog": [self._serialize_decision_entry(entry) for entry in self.result.decision_log],
                "weekendCompensation": [self._serialize_weekend_compensation(comp) for comp in self.result.weekend_compensation_tracking],
                "roleAssignmentReport": role_report
            }
        return self._json_cache
    
    def to_json_string(self, indent: int = 2) -> str:
        """Generate formatted JSON string."""
        return json.dumps(self.to_json(), indent=indent, default=self._json_serializer)
    
    def to_csv(self) -> str:
        """Generate CSV from JSON with proper RFC 4180 formatting and UTF-8 BOM."""
        json_data = self.to_json()
        schedule_data = json_data["schedule"]
        
        # Create CSV with UTF-8 BOM
        output = io.StringIO()
        
        # Add UTF-8 BOM
        output.write('\ufeff')
        
        # Add header comments with metadata
        metadata = json_data["metadata"]
        output.write(f"# Schema Version: {json_data['schemaVersion']}\n")
        output.write(f"# Generated: {metadata['generationTimestamp']}\n")
        output.write(f"# Configuration: {metadata['engineerCount']} engineers, {metadata['weeks']} weeks\n")
        output.write(f"# Date Range: {metadata['startDate']} to {metadata['endDate']}\n")
        
        # Add role summary if available
        if "role_summary" in schedule_data:
            output.write(f"# Enhanced Display: Role summaries and formatting included\n")
            role_summary = schedule_data["role_summary"]
            if "coverage_analysis" in role_summary:
                coverage = role_summary["coverage_analysis"]
                output.write(f"# Weekday Coverage: {coverage.get('weekday_coverage', {}).get('total_weekdays', 0)} days\n")
                output.write(f"# Weekend Coverage: {coverage.get('weekend_coverage', {}).get('total_weekend_days', 0)} days\n")
        
        # Extract schedule rows
        if "rows" in schedule_data:
            rows = schedule_data["rows"]
            if not rows:
                return output.getvalue()
            
            # Create CSV writer with RFC 4180 compliance
            writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator='\n')
            
            # Write header
            headers = schedule_data.get("headers", [])
            if headers:
                writer.writerow(headers)
            
            # Write data rows
            for row in rows:
                # Ensure all values are strings and escape special characters
                escaped_row = []
                for value in row:
                    if value is None:
                        escaped_row.append("")
                    else:
                        str_value = str(value)
                        # Escape commas and parentheses in labels
                        if "(" in str_value or ")" in str_value or "," in str_value:
                            str_value = f'"{str_value}"'
                        escaped_row.append(str_value)
                writer.writerow(escaped_row)
        
        # Add role summary section if available
        if "role_summary" in schedule_data:
            output.write("\n# ROLE SUMMARY SECTION\n")
            role_summary = schedule_data["role_summary"]
            
            # Add role distribution summary
            if "role_distribution" in role_summary:
                output.write("# Role Distribution Summary:\n")
                for role, assignments in role_summary["role_distribution"].items():
                    output.write(f"# {role}: ")
                    role_assignments = [f"{eng}({count})" for eng, count in assignments.items() if eng]
                    output.write(", ".join(role_assignments) + "\n")
            
            # Add coverage analysis
            if "coverage_analysis" in role_summary:
                coverage = role_summary["coverage_analysis"]
                output.write("# Coverage Analysis:\n")
                weekday_cov = coverage.get("weekday_coverage", {})
                weekend_cov = coverage.get("weekend_coverage", {})
                output.write(f"# Weekdays: {weekday_cov.get('total_weekdays', 0)} days, ")
                output.write(f"avg {weekday_cov.get('avg_roles_per_day', 0):.1f} roles/day\n")
                output.write(f"# Weekends: {weekend_cov.get('total_weekend_days', 0)} days, ")
                output.write(f"avg {weekend_cov.get('avg_roles_per_day', 0):.1f} roles/day\n")
            
            output.write("\n")
        
        csv_content = output.getvalue()
        
        # Run invariant checks on the generated CSV
        self._validate_csv_invariants(csv_content)
        
        return csv_content
    
    def to_csv_bytes(self) -> bytes:
        """Generate CSV as bytes with UTF-8 encoding."""
        csv_string = self.to_csv()
        return csv_string.encode('utf-8')
    
    def to_xlsx(self) -> bytes:
        """Generate XLSX with multiple sheets for different data types."""
        json_data = self.to_json()
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Main schedule sheet with enhanced formatting
            schedule_data = json_data["schedule"]
            if "rows" in schedule_data and "headers" in schedule_data:
                df_schedule = pd.DataFrame(schedule_data["rows"], columns=schedule_data["headers"])
                df_schedule.to_excel(writer, sheet_name="Enhanced Schedule", index=False)
            
            # Role Summary Sheet
            if "role_summary" in schedule_data:
                role_summary = schedule_data["role_summary"]
                
                # Role Distribution Summary
                if "role_distribution" in role_summary:
                    role_dist_rows = []
                    for role, assignments in role_summary["role_distribution"].items():
                        for engineer, count in assignments.items():
                            if engineer:  # Skip empty assignments
                                role_dist_rows.append({
                                    "Role": role,
                                    "Engineer": engineer,
                                    "Assignment Count": count
                                })
                    
                    if role_dist_rows:
                        df_role_dist = pd.DataFrame(role_dist_rows)
                        df_role_dist.to_excel(writer, sheet_name="Role Distribution", index=False)
                
                # Engineer Workload Summary
                if "engineer_workload" in role_summary:
                    workload_rows = []
                    for engineer, workload in role_summary["engineer_workload"].items():
                        workload_rows.append({
                            "Engineer": engineer,
                            "Work Days": workload.get("work_days", 0),
                            "Leave Days": workload.get("leave_days", 0),
                            "Off Days": workload.get("off_days", 0),
                            "Total Days": workload.get("total_days", 0),
                            "Work Percentage": f"{(workload.get('work_days', 0) / max(workload.get('total_days', 1), 1) * 100):.1f}%"
                        })
                    
                    if workload_rows:
                        df_workload = pd.DataFrame(workload_rows)
                        df_workload.to_excel(writer, sheet_name="Engineer Workload", index=False)
                
                # Coverage Analysis Summary
                if "coverage_analysis" in role_summary:
                    coverage = role_summary["coverage_analysis"]
                    coverage_rows = [
                        ["Metric", "Weekdays", "Weekends"],
                        ["Total Days", 
                         coverage.get("weekday_coverage", {}).get("total_weekdays", 0),
                         coverage.get("weekend_coverage", {}).get("total_weekend_days", 0)],
                        ["Avg Roles per Day", 
                         f"{coverage.get('weekday_coverage', {}).get('avg_roles_per_day', 0):.1f}",
                         f"{coverage.get('weekend_coverage', {}).get('avg_roles_per_day', 0):.1f}"],
                        ["Min Roles per Day", 
                         coverage.get("weekday_coverage", {}).get("min_roles_per_day", 0),
                         coverage.get("weekend_coverage", {}).get("min_roles_per_day", 0)],
                        ["Max Roles per Day", 
                         coverage.get("weekday_coverage", {}).get("max_roles_per_day", 0),
                         coverage.get("weekend_coverage", {}).get("max_roles_per_day", 0)]
                    ]
                    
                    df_coverage = pd.DataFrame(coverage_rows[1:], columns=coverage_rows[0])
                    df_coverage.to_excel(writer, sheet_name="Coverage Analysis", index=False)
            
            # Fairness report sheet
            fairness_data = json_data["fairnessReport"]
            if "engineerStats" in fairness_data:
                fairness_rows = []
                for engineer, stats in fairness_data["engineerStats"].items():
                    row = {"Engineer": engineer}
                    row.update(stats)
                    fairness_rows.append(row)
                
                if fairness_rows:
                    df_fairness = pd.DataFrame(fairness_rows)
                    df_fairness.to_excel(writer, sheet_name="Fairness Report", index=False)
                
                # Add summary metrics
                summary_data = {
                    "Metric": ["Equity Score", "Max-Min Delta (OnCall)", "Max-Min Delta (Weekend)", 
                              "Max-Min Delta (Early)", "Max-Min Delta (Chat)", "Max-Min Delta (Appointments)"],
                    "Value": [
                        fairness_data.get("equityScore", 0),
                        fairness_data.get("maxMinDeltas", {}).get("oncall", 0),
                        fairness_data.get("maxMinDeltas", {}).get("weekend", 0),
                        fairness_data.get("maxMinDeltas", {}).get("early", 0),
                        fairness_data.get("maxMinDeltas", {}).get("chat", 0),
                        fairness_data.get("maxMinDeltas", {}).get("appointments", 0)
                    ]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name="Summary Metrics", index=False)
            
            # Weekend compensation sheet
            weekend_compensation = json_data.get("weekendCompensation", [])
            if weekend_compensation:
                comp_rows = []
                for comp in weekend_compensation:
                    comp_rows.append({
                        "Engineer": comp["engineer"],
                        "Weekend Date": comp["weekendDate"],
                        "Pattern Type": comp["patternType"],
                        "Compensation Dates": ', '.join(comp["compensationDates"])
                    })
                
                if comp_rows:
                    df_compensation = pd.DataFrame(comp_rows)
                    df_compensation.to_excel(writer, sheet_name="Weekend Compensation", index=False)
            
            # Decision log sheet
            decision_log = json_data["decisionLog"]
            if decision_log:
                df_decisions = pd.DataFrame(decision_log)
                # Convert lists to strings for Excel compatibility
                for col in df_decisions.columns:
                    if df_decisions[col].dtype == 'object':
                        df_decisions[col] = df_decisions[col].apply(
                            lambda x: ', '.join(x) if isinstance(x, list) else str(x)
                        )
                df_decisions.to_excel(writer, sheet_name="Decision Log", index=False)
            
            # Role Assignment Report sheet
            role_report = json_data.get("roleAssignmentReport", {})
            if role_report:
                # Summary statistics
                summary = role_report.get("summary", {})
                summary_rows = [
                    ["Metric", "Value"],
                    ["Total Days", summary.get("total_days", 0)],
                    ["Total Weekdays", summary.get("total_weekdays", 0)],
                    ["Total Weekends", summary.get("total_weekends", 0)],
                    ["Avg Roles per Weekday", f"{summary.get('avg_roles_per_weekday', 0):.1f}"],
                    ["Avg Roles per Weekend", f"{summary.get('avg_roles_per_weekend', 0):.1f}"]
                ]
                
                df_summary = pd.DataFrame(summary_rows[1:], columns=summary_rows[0])
                df_summary.to_excel(writer, sheet_name="Assignment Summary", index=False)
                
                # Role balance analysis
                balance = role_report.get("role_distribution_balance", {})
                if balance:
                    balance_rows = []
                    for role, stats in balance.items():
                        balance_rows.append({
                            "Role": role,
                            "Min Assignments": stats.get("min_assignments", 0),
                            "Max Assignments": stats.get("max_assignments", 0),
                            "Range": stats.get("range", 0),
                            "Engineers Assigned": stats.get("engineers_assigned", 0)
                        })
                    
                    if balance_rows:
                        df_balance = pd.DataFrame(balance_rows)
                        df_balance.to_excel(writer, sheet_name="Role Balance", index=False)
            
            # Metadata sheet
            metadata = json_data["metadata"]
            metadata_rows = [
                ["Schema Version", json_data["schemaVersion"]],
                ["Generation Timestamp", metadata["generationTimestamp"]],
                ["Engineer Count", metadata["engineerCount"]],
                ["Weeks", metadata["weeks"]],
                ["Start Date", metadata["startDate"]],
                ["End Date", metadata["endDate"]],
                ["Total Days", metadata["totalDays"]],
                ["Role Clarity Enabled", json_data["schedule"].get("role_clarity_enabled", False)]
            ]
            
            # Add configuration details
            config = metadata.get("configuration", {})
            for key, value in config.items():
                metadata_rows.append([f"Config: {key}", str(value)])
            
            df_metadata = pd.DataFrame(metadata_rows, columns=["Property", "Value"])
            df_metadata.to_excel(writer, sheet_name="Metadata", index=False)
        
        output.seek(0)
        return output.read()
    
    def _serialize_metadata(self, metadata: ScheduleMetadata) -> Dict[str, Any]:
        """Serialize metadata to JSON-compatible format."""
        return {
            "generationTimestamp": metadata.generation_timestamp.isoformat(),
            "configuration": metadata.configuration,
            "engineerCount": metadata.engineer_count,
            "weeks": metadata.weeks,
            "startDate": metadata.start_date.isoformat(),
            "endDate": metadata.end_date.isoformat(),
            "totalDays": metadata.total_days
        }
    
    def _serialize_fairness_report(self, fairness_report: FairnessReport) -> Dict[str, Any]:
        """Serialize fairness report to JSON-compatible format."""
        return {
            "engineerStats": {
                name: asdict(stats) for name, stats in fairness_report.engineer_stats.items()
            },
            "equityScore": fairness_report.equity_score,
            "maxMinDeltas": fairness_report.max_min_deltas,
            "generationTimestamp": fairness_report.generation_timestamp.isoformat()
        }
    
    def _serialize_decision_entry(self, entry: DecisionEntry) -> Dict[str, Any]:
        """Serialize decision entry to JSON-compatible format."""
        return {
            "date": entry.date,
            "decisionType": entry.decision_type,
            "affectedEngineers": entry.affected_engineers,
            "reason": entry.reason,
            "alternativesConsidered": entry.alternatives_considered,
            "timestamp": entry.timestamp.isoformat()
        }
    
    def _serialize_weekend_compensation(self, comp: WeekendCompensation) -> Dict[str, Any]:
        """Serialize weekend compensation to JSON-compatible format."""
        return {
            "engineer": comp.engineer,
            "weekendDate": comp.weekend_date.isoformat(),
            "compensationDates": [d.isoformat() for d in comp.compensation_dates],
            "patternType": comp.pattern_type
        }
    
    def _validate_csv_invariants(self, csv_content: str):
        """Validate CSV output against scheduling invariants."""
        try:
            # Extract engineer names from metadata
            engineers = []
            if hasattr(self.result.metadata, 'engineers'):
                engineers = self.result.metadata.engineers
            elif 'engineers' in self.result.schedule_data:
                engineers = self.result.schedule_data['engineers']
            else:
                # Try to extract from the schedule data
                schedule_data = self.result.schedule_data
                if 'rows' in schedule_data and schedule_data['rows']:
                    # This is a fallback - we should have engineer names in metadata
                    engineers = []  # Skip validation if we can't get engineer names
            
            if engineers:
                # Create invariant checker and validate CSV
                checker = ScheduleInvariantChecker(engineers)
                violations = checker.check_all_invariants(pd.DataFrame(), csv_content)
                
                if violations:
                    violation_summary = checker.get_violation_summary()
                    logger.log_invariant_violation(
                        request_id="csv_export",
                        violation_type="csv_format_violations", 
                        details=violation_summary
                    )
        except Exception as e:
            # Don't fail export on validation errors, just log them
            logger.log_error("csv_export", e, "CSV invariant validation failed")
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and date objects."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def add_role_clarity_indicators(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add clear role indicators to schedule data for enhanced readability.
    
    Requirements addressed:
    - 5.2: Enhance existing CSV/XLSX export to include clear role indicators
    """
    if "rows" not in schedule_data or "headers" not in schedule_data:
        return schedule_data
    
    headers = schedule_data["headers"]
    rows = schedule_data["rows"]
    
    # Find role columns
    role_columns = {}
    for i, header in enumerate(headers):
        if header in ["Early1", "Early2", "Chat", "OnCall", "Appointments"]:
            role_columns[header] = i
    
    # Add role clarity indicators to each row
    enhanced_rows = []
    for row in rows:
        enhanced_row = row.copy()
        
        # Add role indicators with symbols
        for role, col_idx in role_columns.items():
            if col_idx < len(enhanced_row) and enhanced_row[col_idx]:
                engineer = enhanced_row[col_idx]
                if role == "Early1":
                    enhanced_row[col_idx] = f"🌅 {engineer} (Early1)"
                elif role == "Early2":
                    enhanced_row[col_idx] = f"🌅 {engineer} (Early2)"
                elif role == "Chat":
                    enhanced_row[col_idx] = f"💬 {engineer} (Chat)"
                elif role == "OnCall":
                    enhanced_row[col_idx] = f"📞 {engineer} (OnCall)"
                elif role == "Appointments":
                    enhanced_row[col_idx] = f"📅 {engineer} (Appointments)"
        
        enhanced_rows.append(enhanced_row)
    
    # Create enhanced schedule data
    enhanced_schedule_data = schedule_data.copy()
    enhanced_schedule_data["rows"] = enhanced_rows
    enhanced_schedule_data["role_clarity_enabled"] = True
    
    return enhanced_schedule_data


def generate_role_assignment_report(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive role assignment report for exports.
    
    Requirements addressed:
    - 5.2: Add role summary sections to exported schedules
    - 5.4: Improve schedule readability for end users
    """
    if "rows" not in schedule_data or "headers" not in schedule_data:
        return {}
    
    headers = schedule_data["headers"]
    rows = schedule_data["rows"]
    
    # Find column indices
    role_columns = {}
    date_col = None
    day_col = None
    
    for i, header in enumerate(headers):
        if header in ["Early1", "Early2", "Chat", "OnCall", "Appointments"]:
            role_columns[header] = i
        elif header == "Date":
            date_col = i
        elif header == "Day":
            day_col = i
    
    # Analyze role assignments
    role_stats = {}
    daily_role_counts = []
    engineer_role_counts = {}
    
    for row in rows:
        day_roles = 0
        day_type = row[day_col] if day_col is not None else "Unknown"
        
        for role, col_idx in role_columns.items():
            if col_idx < len(row) and row[col_idx]:
                engineer = row[col_idx].strip()
                # Clean engineer name from role indicators
                if " (" in engineer:
                    engineer = engineer.split(" (")[0].replace("🌅 ", "").replace("💬 ", "").replace("📞 ", "").replace("📅 ", "")
                
                if engineer:
                    day_roles += 1
                    
                    # Track role statistics
                    if role not in role_stats:
                        role_stats[role] = {"total_assignments": 0, "engineers": {}}
                    
                    role_stats[role]["total_assignments"] += 1
                    
                    if engineer not in role_stats[role]["engineers"]:
                        role_stats[role]["engineers"][engineer] = 0
                    role_stats[role]["engineers"][engineer] += 1
                    
                    # Track engineer statistics
                    if engineer not in engineer_role_counts:
                        engineer_role_counts[engineer] = {"total_roles": 0, "roles": {}}
                    
                    engineer_role_counts[engineer]["total_roles"] += 1
                    
                    if role not in engineer_role_counts[engineer]["roles"]:
                        engineer_role_counts[engineer]["roles"][role] = 0
                    engineer_role_counts[engineer]["roles"][role] += 1
        
        daily_role_counts.append({"day_type": day_type, "role_count": day_roles})
    
    # Generate summary statistics
    total_days = len(rows)
    weekdays = [d for d in daily_role_counts if d["day_type"] in ["Mon", "Tue", "Wed", "Thu", "Fri"]]
    weekends = [d for d in daily_role_counts if d["day_type"] in ["Sat", "Sun"]]
    
    report = {
        "summary": {
            "total_days": total_days,
            "total_weekdays": len(weekdays),
            "total_weekends": len(weekends),
            "avg_roles_per_weekday": sum(d["role_count"] for d in weekdays) / len(weekdays) if weekdays else 0,
            "avg_roles_per_weekend": sum(d["role_count"] for d in weekends) / len(weekends) if weekends else 0
        },
        "role_statistics": role_stats,
        "engineer_statistics": engineer_role_counts,
        "role_distribution_balance": {}
    }
    
    # Calculate role distribution balance
    for role, stats in role_stats.items():
        engineers = stats["engineers"]
        if engineers:
            counts = list(engineers.values())
            report["role_distribution_balance"][role] = {
                "min_assignments": min(counts),
                "max_assignments": max(counts),
                "range": max(counts) - min(counts),
                "engineers_assigned": len(engineers)
            }
    
    return report


def generate_filename(format_type: str, metadata: ScheduleMetadata, config_name: str = "default") -> str:
    """Generate descriptive filename with date and configuration info."""
    start_date = metadata.start_date.strftime("%Y%m%d")
    end_date = metadata.end_date.strftime("%Y%m%d")
    timestamp = metadata.generation_timestamp.strftime("%Y%m%d_%H%M%S")
    
    base_name = f"schedule_{config_name}_{metadata.engineer_count}eng_{metadata.weeks}wk_{start_date}-{end_date}_{timestamp}"
    
    extensions = {
        'csv': '.csv',
        'xlsx': '.xlsx',
        'json': '.json'
    }
    
    return base_name + extensions.get(format_type, '.txt')


# Utility functions for converting existing data structures

def convert_dataframe_to_schedule_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Convert pandas DataFrame to schedule data format."""
    return {
        "headers": df.columns.tolist(),
        "rows": df.values.tolist()
    }


def create_basic_fairness_report(engineers: List[str]) -> FairnessReport:
    """Create a basic fairness report structure."""
    from models import EngineerStats
    
    engineer_stats = {}
    for engineer in engineers:
        engineer_stats[engineer] = EngineerStats(name=engineer)
    
    return FairnessReport(
        engineer_stats=engineer_stats,
        equity_score=0.0,
        max_min_deltas={"oncall": 0, "weekend": 0, "early": 0, "chat": 0, "appointments": 0}
    )


def create_basic_metadata(engineers: List[str], weeks: int, start_date: date, 
                         config: Dict[str, Any]) -> ScheduleMetadata:
    """Create basic metadata structure."""
    end_date = start_date + timedelta(days=weeks * 7 - 1)
    
    return ScheduleMetadata(
        generation_timestamp=datetime.now(),
        configuration=config,
        engineer_count=len(engineers),
        weeks=weeks,
        start_date=start_date,
        end_date=end_date,
        total_days=weeks * 7
    )