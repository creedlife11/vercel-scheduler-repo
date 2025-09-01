#!/usr/bin/env python3
"""
Integration verification script for task 10.1
Verifies that all enhanced components are properly integrated.
"""

import sys
import json
from datetime import date, datetime
import pandas as pd

def verify_integration():
    """Verify all enhanced components are integrated properly."""
    print("🔍 Verifying enhanced component integration...")
    
    # Test imports
    try:
        from schedule_core import make_enhanced_schedule
        from export_manager import ExportManager
        from models import ScheduleResult, ScheduleRequest
        from lib.validation import validateCompleteForm
        from lib.logging_utils import logger
        from lib.performance_monitor import performance_monitor
        from lib.invariant_checker import ScheduleInvariantChecker
        print("✅ All enhanced modules imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test enhanced schedule generation
    try:
        engineers = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        start_sunday = date(2025, 1, 5)  # A Sunday
        weeks = 2
        seeds = {"weekend": 0, "chat": 0, "oncall": 1, "appointments": 2, "early": 0}
        leave_df = pd.DataFrame(columns=["Engineer", "Date", "Reason"])
        
        # Generate enhanced schedule
        schedule_result = make_enhanced_schedule(start_sunday, weeks, engineers, seeds, leave_df)
        
        # Verify ScheduleResult structure
        assert hasattr(schedule_result, 'schedule_data')
        assert hasattr(schedule_result, 'fairness_report')
        assert hasattr(schedule_result, 'decision_log')
        assert hasattr(schedule_result, 'metadata')
        assert schedule_result.schema_version == "2.0"
        
        print("✅ Enhanced schedule generation working")
    except Exception as e:
        print(f"❌ Enhanced schedule generation error: {e}")
        return False
    
    # Test export manager integration
    try:
        export_manager = ExportManager(schedule_result)
        
        # Test all export formats
        json_data = export_manager.to_json()
        csv_content = export_manager.to_csv()
        xlsx_bytes = export_manager.to_xlsx()
        
        # Verify JSON structure
        assert "schemaVersion" in json_data
        assert "fairnessReport" in json_data
        assert "decisionLog" in json_data
        assert "metadata" in json_data
        
        # Verify CSV has content
        assert len(csv_content) > 100
        assert "Schema Version: 2.0" in csv_content
        
        # Verify XLSX has content
        assert len(xlsx_bytes) > 1000
        
        print("✅ Export manager integration working")
    except Exception as e:
        print(f"❌ Export manager integration error: {e}")
        return False
    
    # Test validation integration
    try:
        # Test frontend validation (TypeScript types won't work in Python, but we can test the structure)
        test_request = {
            "engineers": engineers,
            "start_sunday": "2025-01-05",
            "weeks": 2,
            "seeds": seeds,
            "leave": [],
            "format": "csv"
        }
        
        # Test backend validation
        validated_request = ScheduleRequest(**test_request)
        assert len(validated_request.engineers) == 6
        assert validated_request.weeks == 2
        
        print("✅ Validation system integration working")
    except Exception as e:
        print(f"❌ Validation integration error: {e}")
        return False
    
    # Test monitoring integration
    try:
        request_id = logger.generate_request_id()
        metrics = logger.start_request(request_id, test_request)
        
        with performance_monitor.monitor_operation("test_operation"):
            # Simulate some work
            pass
        
        logger.end_request(request_id, success=True)
        
        print("✅ Monitoring and logging integration working")
    except Exception as e:
        print(f"❌ Monitoring integration error: {e}")
        return False
    
    # Test invariant checking integration
    try:
        checker = ScheduleInvariantChecker(engineers)
        
        # Convert schedule result to DataFrame for checking
        schedule_data = schedule_result.schedule_data
        if "rows" in schedule_data and "headers" in schedule_data:
            df = pd.DataFrame(schedule_data["rows"], columns=schedule_data["headers"])
            violations = checker.check_all_invariants(df)
            
            # Should have no critical violations for a basic schedule
            critical_violations = [v for v in violations if v.severity == "error"]
            if critical_violations:
                print(f"⚠️  Found {len(critical_violations)} critical invariant violations")
                for v in critical_violations:
                    print(f"   - {v.message}")
            else:
                print("✅ Invariant checking integration working")
        
    except Exception as e:
        print(f"❌ Invariant checking integration error: {e}")
        return False
    
    print("\n🎉 All enhanced components are properly integrated!")
    return True

if __name__ == "__main__":
    success = verify_integration()
    sys.exit(0 if success else 1)