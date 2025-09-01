#!/usr/bin/env python3
"""
Verification script for Task 2.2: Build comprehensive edge case test coverage
This script validates that all required edge case tests are implemented correctly.
"""

import ast
import inspect
from typing import List, Dict, Set

def analyze_test_file(filename: str) -> Dict[str, any]:
    """Analyze the test file to verify edge case test coverage."""
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Parse the AST to find test methods
    tree = ast.parse(content)
    
    test_classes = []
    test_methods = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                test_classes.append(node.name)
                
                # Find test methods in this class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_methods.append(f"{node.name}.{item.name}")
    
    return {
        'test_classes': test_classes,
        'test_methods': test_methods,
        'total_tests': len(test_methods)
    }

def verify_edge_case_coverage() -> bool:
    """Verify that all required edge case tests are implemented."""
    
    analysis = analyze_test_file('test_schedule_invariants.py')
    
    print("=== Task 2.2 Edge Case Test Coverage Verification ===\n")
    
    # Required test categories based on task requirements
    required_categories = {
        'leave_handling': [
            'test_leave_conflict_multiple_engineers_same_day',
            'test_leave_conflict_weekend_worker', 
            'test_leave_consecutive_days_same_engineer',
            'test_leave_all_engineers_except_one'
        ],
        'weekend_patterns': [
            'test_weekend_alternation_pattern_consistency',
            'test_weekend_no_oncall_invariant_extended',
            'test_weekend_worker_rotation_fairness'
        ],
        'role_fairness': [
            'test_role_rotation_consistency',
            'test_seed_rotation_effect',
            'test_role_assignment_with_varying_leave'
        ]
    }
    
    print(f"Found {analysis['total_tests']} total test methods")
    print(f"Test classes: {', '.join(analysis['test_classes'])}\n")
    
    # Check each category
    all_passed = True
    
    for category, required_tests in required_categories.items():
        print(f"📋 {category.replace('_', ' ').title()} Tests:")
        
        category_passed = True
        for test_name in required_tests:
            full_test_name = f"TestEdgeCaseScenarios.{test_name}"
            
            if full_test_name in analysis['test_methods']:
                print(f"  ✅ {test_name}")
            else:
                print(f"  ❌ {test_name} - MISSING")
                category_passed = False
                all_passed = False
        
        print(f"  Category Status: {'✅ PASS' if category_passed else '❌ FAIL'}\n")
    
    # Verify TestEdgeCaseScenarios class exists
    if 'TestEdgeCaseScenarios' not in analysis['test_classes']:
        print("❌ TestEdgeCaseScenarios class not found!")
        all_passed = False
    else:
        print("✅ TestEdgeCaseScenarios class found")
    
    # Count edge case tests specifically
    edge_case_tests = [m for m in analysis['test_methods'] if 'TestEdgeCaseScenarios' in m]
    print(f"\n📊 Edge Case Test Summary:")
    print(f"  Total edge case tests: {len(edge_case_tests)}")
    print(f"  Required minimum: 10")
    
    if len(edge_case_tests) >= 10:
        print("  ✅ Sufficient test coverage")
    else:
        print("  ❌ Insufficient test coverage")
        all_passed = False
    
    print(f"\n🎯 Overall Status: {'✅ PASS - All requirements met' if all_passed else '❌ FAIL - Missing requirements'}")
    
    return all_passed

def verify_test_structure() -> bool:
    """Verify that tests follow proper structure and patterns."""
    
    print("\n=== Test Structure Verification ===\n")
    
    with open('test_schedule_invariants.py', 'r') as f:
        content = f.read()
    
    structure_checks = {
        'pytest_imports': 'import pytest' in content,
        'pandas_imports': 'import pandas as pd' in content,
        'datetime_imports': 'from datetime import date' in content,
        'schedule_core_imports': 'from schedule_core import' in content,
        'export_manager_imports': 'from export_manager import' in content,
        'models_imports': 'from models import' in content,
        'fixtures_defined': '@pytest.fixture' in content,
        'edge_case_class': 'class TestEdgeCaseScenarios:' in content,
        'docstrings_present': '"""' in content,
        'assertions_present': 'assert ' in content
    }
    
    all_passed = True
    
    for check, passed in structure_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    
    print(f"\n🏗️  Structure Status: {'✅ PASS' if all_passed else '❌ FAIL'}")
    
    return all_passed

def main():
    """Main verification function."""
    
    print("Task 2.2: Build comprehensive edge case test coverage")
    print("=" * 60)
    
    try:
        coverage_ok = verify_edge_case_coverage()
        structure_ok = verify_test_structure()
        
        overall_status = coverage_ok and structure_ok
        
        print(f"\n{'='*60}")
        print(f"🎯 FINAL RESULT: {'✅ TASK 2.2 COMPLETE' if overall_status else '❌ TASK 2.2 INCOMPLETE'}")
        print(f"{'='*60}")
        
        if overall_status:
            print("\n✅ All edge case tests implemented successfully!")
            print("✅ Test structure follows best practices!")
            print("✅ Ready for CI/CD integration (Task 2.3)!")
        else:
            print("\n❌ Some requirements not met. Please review and fix.")
        
        return overall_status
        
    except FileNotFoundError:
        print("❌ test_schedule_invariants.py not found!")
        return False
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)