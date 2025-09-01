"""
JSON-first export manager that generates all output formats from a single JSON source.
Implements CSV export with RFC 4180 formatting and UTF-8 BOM, and XLSX export with multiple sheets.
"""

import json
import csv
import io
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import pandas as pd
from dataclasses import asdict

from models import ScheduleResult, FairnessReport, DecisionEntry, ScheduleMetadata
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
            self._json_cache = {
                "schemaVersion": self.result.schema_version,
                "metadata": self._serialize_metadata(self.result.metadata),
                "schedule": self.result.schedule_data,
                "fairnessReport": self._serialize_fairness_report(self.result.fairness_report),
                "decisionLog": [self._serialize_decision_entry(entry) for entry in self.result.decision_log]
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
            # Main schedule sheet
            schedule_data = json_data["schedule"]
            if "rows" in schedule_data and "headers" in schedule_data:
                df_schedule = pd.DataFrame(schedule_data["rows"], columns=schedule_data["headers"])
                df_schedule.to_excel(writer, sheet_name="Schedule", index=False)
            
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
            
            # Metadata sheet
            metadata = json_data["metadata"]
            metadata_rows = [
                ["Schema Version", json_data["schemaVersion"]],
                ["Generation Timestamp", metadata["generationTimestamp"]],
                ["Engineer Count", metadata["engineerCount"]],
                ["Weeks", metadata["weeks"]],
                ["Start Date", metadata["startDate"]],
                ["End Date", metadata["endDate"]],
                ["Total Days", metadata["totalDays"]]
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
    end_date = start_date + pd.Timedelta(days=weeks * 7 - 1)
    
    return ScheduleMetadata(
        generation_timestamp=datetime.now(),
        configuration=config,
        engineer_count=len(engineers),
        weeks=weeks,
        start_date=start_date,
        end_date=end_date.date(),
        total_days=weeks * 7
    )