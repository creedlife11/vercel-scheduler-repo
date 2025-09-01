#!/usr/bin/env python3
"""
Test script for name hygiene functionality.
Verifies that name normalization and duplicate detection work correctly.
"""

import sys
import os

# Add lib directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from name_hygiene import (
    normalize_name,
    validate_name_characters,
    validate_single_name,
    analyze_name_duplicates,
    validate_engineer_list,
    calculate_name_similarity
)


def test_name_normalization():
    """Test name normalization functionality."""
    print("Testing name normalization...")
    
    test_cases = [
        ("  John Doe  ", "John Doe"),
        ("John    Doe", "John Doe"),
        ("José María", "José María"),  # Unicode handling
        ("O'Connor", "O'Connor"),
        ("Mary-Jane", "Mary-Jane"),
        ("Dr. Smith", "Dr. Smith"),
        ("", ""),
        ("   ", ""),
    ]
    
    for input_name, expected in test_cases:
        result = normalize_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_name}' -> '{result}' (expected: '{expected}')")
        if result != expected:
            print(f"    ERROR: Expected '{expected}', got '{result}'")


def test_character_validation():
    """Test character validation functionality."""
    print("\nTesting character validation...")
    
    valid_names = [
        "John Doe",
        "José María",
        "O'Connor",
        "Mary-Jane",
        "Dr. Smith",
        "李小明",  # Chinese characters
        "Müller",  # German umlaut
    ]
    
    invalid_names = [
        "John@Doe",
        "John#Doe",
        "John123",
        "John$Doe",
        "",
    ]
    
    for name in valid_names:
        result = validate_name_characters(name)
        status = "✓" if result else "✗"
        print(f"  {status} Valid: '{name}' -> {result}")
    
    for name in invalid_names:
        result = validate_name_characters(name)
        status = "✓" if not result else "✗"
        print(f"  {status} Invalid: '{name}' -> {result}")


def test_duplicate_detection():
    """Test duplicate detection functionality."""
    print("\nTesting duplicate detection...")
    
    # Test case with various duplicate scenarios
    names = [
        "John Doe",
        "Jane Smith",
        "john doe",  # Case difference
        "Bob Johnson",
        "Jon Doe",   # Similar name
        "Jane Smith", # Exact duplicate
    ]
    
    analysis = analyze_name_duplicates(names)
    
    print(f"  Exact duplicates: {len(analysis.exact_duplicates)}")
    for name1, name2 in analysis.exact_duplicates:
        print(f"    - '{name1}' and '{name2}'")
    
    print(f"  Case-only differences: {len(analysis.case_only_differences)}")
    for name1, name2 in analysis.case_only_differences:
        print(f"    - '{name1}' and '{name2}'")
    
    print(f"  Similar names: {len(analysis.similar_names)}")
    for name1, name2, similarity in analysis.similar_names:
        print(f"    - '{name1}' and '{name2}' ({similarity:.1%} similar)")


def test_engineer_list_validation():
    """Test complete engineer list validation."""
    print("\nTesting engineer list validation...")
    
    # Valid list
    valid_engineers = [
        "Alice Johnson",
        "Bob Smith", 
        "Carol Davis",
        "David Wilson",
        "Eve Brown",
        "Frank Miller"
    ]
    
    result = validate_engineer_list(valid_engineers)
    print(f"  Valid list: {result['is_valid']}")
    if result['errors']:
        print(f"    Errors: {result['errors']}")
    if result['warnings']:
        print(f"    Warnings: {result['warnings']}")
    
    # Invalid list with duplicates
    invalid_engineers = [
        "Alice Johnson",
        "Bob Smith",
        "alice johnson",  # Duplicate (case difference)
        "David Wilson",
        "Eve Brown",
        "Bob Smith"  # Exact duplicate
    ]
    
    result = validate_engineer_list(invalid_engineers)
    print(f"  Invalid list: {result['is_valid']}")
    if result['errors']:
        print(f"    Errors: {result['errors']}")
    if result['warnings']:
        print(f"    Warnings: {result['warnings']}")


def test_similarity_calculation():
    """Test name similarity calculation."""
    print("\nTesting similarity calculation...")
    
    test_pairs = [
        ("John", "John", 1.0),
        ("John", "Jon", 0.75),
        ("Smith", "Smyth", 0.8),
        ("Alice", "Bob", 0.0),
        ("", "", 1.0),
        ("Test", "", 0.0),
    ]
    
    for name1, name2, expected_min in test_pairs:
        similarity = calculate_name_similarity(name1, name2)
        status = "✓" if similarity >= expected_min else "✗"
        print(f"  {status} '{name1}' vs '{name2}': {similarity:.2f} (expected >= {expected_min})")


if __name__ == "__main__":
    print("Name Hygiene Test Suite")
    print("=" * 50)
    
    test_name_normalization()
    test_character_validation()
    test_duplicate_detection()
    test_engineer_list_validation()
    test_similarity_calculation()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")