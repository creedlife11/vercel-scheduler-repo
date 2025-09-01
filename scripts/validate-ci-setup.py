#!/usr/bin/env python3
"""
Validation script to check CI/CD setup completeness.
This script verifies that all required configuration files are present and properly configured.
"""

import os
import json
import yaml
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and report status."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def validate_json_file(filepath: str, description: str) -> bool:
    """Validate JSON file syntax."""
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"✅ {description}: Valid JSON syntax")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ {description}: Invalid JSON - {e}")
        return False
    except FileNotFoundError:
        print(f"❌ {description}: File not found")
        return False

def validate_yaml_file(filepath: str, description: str) -> bool:
    """Validate YAML file syntax."""
    try:
        with open(filepath, 'r') as f:
            yaml.safe_load(f)
        print(f"✅ {description}: Valid YAML syntax")
        return True
    except yaml.YAMLError as e:
        print(f"❌ {description}: Invalid YAML - {e}")
        return False
    except FileNotFoundError:
        print(f"❌ {description}: File not found")
        return False

def main():
    """Main validation function."""
    print("=== CI/CD Setup Validation ===\n")
    
    all_good = True
    
    # Check GitHub Actions workflow
    print("📁 GitHub Actions Configuration:")
    all_good &= check_file_exists(".github/workflows/ci.yml", "CI/CD Workflow")
    all_good &= validate_yaml_file(".github/workflows/ci.yml", "CI/CD Workflow YAML")
    print()
    
    # Check Python configuration files
    print("🐍 Python Configuration:")
    all_good &= check_file_exists("requirements.txt", "Python Dependencies")
    all_good &= check_file_exists("requirements-dev.txt", "Python Dev Dependencies")
    all_good &= check_file_exists("pytest.ini", "Pytest Configuration")
    all_good &= check_file_exists("ruff.toml", "Ruff Configuration")
    all_good &= check_file_exists("mypy.ini", "MyPy Configuration")
    all_good &= check_file_exists(".coveragerc", "Coverage Configuration")
    print()
    
    # Check Node.js configuration files
    print("📦 Node.js Configuration:")
    all_good &= check_file_exists("package.json", "Package Configuration")
    all_good &= validate_json_file("package.json", "Package.json")
    all_good &= check_file_exists("jest.config.js", "Jest Configuration")
    all_good &= check_file_exists("jest.setup.js", "Jest Setup")
    all_good &= check_file_exists(".eslintrc.json", "ESLint Configuration")
    all_good &= validate_json_file(".eslintrc.json", "ESLint Configuration")
    all_good &= check_file_exists("playwright.config.ts", "Playwright Configuration")
    print()
    
    # Check test directories and files
    print("🧪 Test Infrastructure:")
    all_good &= check_file_exists("test_schedule_invariants.py", "Python Test Suite")
    all_good &= check_file_exists("lib/__tests__/validation.test.ts", "TypeScript Unit Tests")
    all_good &= check_file_exists("tests/e2e/scheduler.spec.ts", "E2E Tests")
    print()
    
    # Check utility files
    print("🔧 Utility Files:")
    all_good &= check_file_exists("Makefile", "Build Automation")
    print()
    
    # Validate package.json scripts
    print("📜 Package.json Scripts Validation:")
    try:
        with open("package.json", 'r') as f:
            package_data = json.load(f)
        
        required_scripts = [
            "test", "test:coverage", "test:e2e", 
            "lint", "lint:fix", "type-check"
        ]
        
        scripts = package_data.get("scripts", {})
        for script in required_scripts:
            if script in scripts:
                print(f"✅ Script '{script}': {scripts[script]}")
            else:
                print(f"❌ Script '{script}': Missing")
                all_good = False
    except Exception as e:
        print(f"❌ Error validating package.json scripts: {e}")
        all_good = False
    
    print()
    
    # Final summary
    if all_good:
        print("🎉 All CI/CD configuration files are present and valid!")
        print("\nNext steps:")
        print("1. Commit and push these changes to trigger the CI/CD pipeline")
        print("2. Check GitHub Actions tab for pipeline execution")
        print("3. Ensure all tests pass before merging to main branch")
    else:
        print("⚠️  Some configuration issues found. Please fix them before proceeding.")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    exit(main())