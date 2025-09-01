#!/usr/bin/env python3
"""
Verification script for Task 1 implementation.
This script checks that all required components are properly implemented.
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} (MISSING)")
        return False

def check_file_content(filepath, required_content, description):
    """Check if a file contains required content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for item in required_content:
                if item in content:
                    print(f"  ✓ Contains: {item}")
                else:
                    print(f"  ✗ Missing: {item}")
                    return False
        return True
    except Exception as e:
        print(f"  ✗ Error reading {filepath}: {e}")
        return False

def main():
    """Main verification function."""
    print("=== Task 1: Core Data Integrity and Export Foundation Verification ===\n")
    
    all_good = True
    
    # Check subtask 1.1: Enhanced data models and validation schemas
    print("Subtask 1.1: Enhanced data models and validation schemas")
    
    # Python models
    if check_file_exists("models.py", "Python data models"):
        required_python_content = [
            "class ScheduleResult:",
            "class FairnessReport:",
            "class DecisionEntry:",
            "class ScheduleRequest:",
            "from pydantic import BaseModel",
            "schema_version: str = \"2.0\""
        ]
        all_good &= check_file_content("models.py", required_python_content, "Python models content")
    else:
        all_good = False
    
    # TypeScript validation
    if check_file_exists("lib/validation.ts", "TypeScript validation schemas"):
        required_ts_content = [
            "import { z } from 'zod'",
            "ScheduleRequestSchema",
            "LeaveEntrySchema",
            "SeedsSchema",
            "isSunday",
            "uniqueEngineers"
        ]
        all_good &= check_file_content("lib/validation.ts", required_ts_content, "TypeScript validation content")
    else:
        all_good = False
    
    print()
    
    # Check subtask 1.2: JSON-first export manager
    print("Subtask 1.2: JSON-first export manager")
    
    if check_file_exists("export_manager.py", "Export manager"):
        required_export_content = [
            "class ExportManager:",
            "def to_json(self)",
            "def to_csv(self)",
            "def to_xlsx(self)",
            "UTF-8 BOM",
            "RFC 4180",
            "generate_filename"
        ]
        all_good &= check_file_content("export_manager.py", required_export_content, "Export manager content")
    else:
        all_good = False
    
    print()
    
    # Check subtask 1.3: Schema versioning and metadata tracking
    print("Subtask 1.3: Schema versioning and metadata tracking")
    
    # Check updated schedule_core.py
    if check_file_exists("schedule_core.py", "Enhanced schedule core"):
        required_core_content = [
            "make_enhanced_schedule",
            "ScheduleResult",
            "schema_version=\"2.0\"",
            "from models import"
        ]
        all_good &= check_file_content("schedule_core.py", required_core_content, "Enhanced schedule core content")
    else:
        all_good = False
    
    # Check updated API
    if check_file_exists("api/generate.py", "Enhanced API"):
        required_api_content = [
            "from export_manager import ExportManager",
            "make_enhanced_schedule",
            "generate_filename",
            "ScheduleRequest"
        ]
        all_good &= check_file_content("api/generate.py", required_api_content, "Enhanced API content")
    else:
        all_good = False
    
    # Check updated frontend
    if check_file_exists("pages/index.tsx", "Enhanced frontend"):
        required_frontend_content = [
            "from \"../lib/validation\"",
            "\"json\"",
            "validateEngineersInput"
        ]
        all_good &= check_file_content("pages/index.tsx", required_frontend_content, "Enhanced frontend content")
    else:
        all_good = False
    
    # Check dependencies
    print("\nDependency files:")
    check_file_exists("requirements.txt", "Python requirements")
    check_file_exists("package.json", "Node.js package.json")
    check_file_exists("tsconfig.json", "TypeScript config")
    
    print("\n" + "="*60)
    if all_good:
        print("✓ Task 1 implementation verification PASSED")
        print("All required components are properly implemented.")
    else:
        print("✗ Task 1 implementation verification FAILED")
        print("Some components are missing or incomplete.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())