"""
Name hygiene and normalization utilities for engineer names.
Handles whitespace trimming, Unicode normalization, and duplicate detection.
"""

import re
import unicodedata
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass


@dataclass
class NameValidationResult:
    """Result of name validation with warnings and suggestions."""
    is_valid: bool
    normalized_name: str
    warnings: List[str]
    errors: List[str]


@dataclass
class DuplicateAnalysis:
    """Analysis of potential duplicate names."""
    exact_duplicates: List[Tuple[str, str]]
    similar_names: List[Tuple[str, str, float]]  # (name1, name2, similarity_score)
    case_only_differences: List[Tuple[str, str]]


def normalize_name(name: str) -> str:
    """
    Normalize a name with comprehensive whitespace and Unicode handling.
    
    Args:
        name: Raw name input
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Step 1: Basic trimming
    name = name.strip()
    
    # Step 2: Normalize Unicode characters (NFD -> NFC)
    # This handles accented characters consistently
    name = unicodedata.normalize('NFC', name)
    
    # Step 3: Normalize whitespace (multiple spaces -> single space)
    name = re.sub(r'\s+', ' ', name)
    
    # Step 4: Handle common name formatting issues
    # Remove extra periods (but keep single periods for abbreviations)
    name = re.sub(r'\.{2,}', '.', name)
    
    # Normalize apostrophes (various Unicode apostrophes -> standard ASCII)
    name = re.sub(r'[''`]', "'", name)
    
    # Normalize hyphens (various Unicode hyphens -> standard ASCII)
    name = re.sub(r'[–—−]', '-', name)
    
    return name


def validate_name_characters(name: str) -> bool:
    """
    Check if a name contains only valid characters.
    
    Args:
        name: Name to validate
        
    Returns:
        True if name contains only valid characters
    """
    if not name:
        return False
    
    # Allow letters (including diacritics), spaces, hyphens, apostrophes, and periods
    # This regex covers most international names
    pattern = r"^[a-zA-ZÀ-ÿĀ-žА-я\u4e00-\u9fff\s\-'\.]+$"
    return bool(re.match(pattern, name))


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two names using Levenshtein distance.
    
    Args:
        name1: First name
        name2: Second name
        
    Returns:
        Similarity score between 0.0 and 1.0 (1.0 = identical)
    """
    if not name1 or not name2:
        return 0.0
    
    # Normalize for comparison
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    
    if n1 == n2:
        return 1.0
    
    # Calculate Levenshtein distance
    distance = levenshtein_distance(n1, n2)
    max_len = max(len(n1), len(n2))
    
    return (max_len - distance) / max_len if max_len > 0 else 0.0


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Edit distance between the strings
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def validate_single_name(name: str) -> NameValidationResult:
    """
    Validate and normalize a single engineer name.
    
    Args:
        name: Raw name input
        
    Returns:
        NameValidationResult with validation status and normalized name
    """
    errors = []
    warnings = []
    
    # Check if name is empty
    if not name or not name.strip():
        return NameValidationResult(
            is_valid=False,
            normalized_name="",
            warnings=[],
            errors=["Name cannot be empty"]
        )
    
    # Normalize the name
    normalized = normalize_name(name)
    
    # Check if normalization resulted in empty string
    if not normalized:
        return NameValidationResult(
            is_valid=False,
            normalized_name="",
            warnings=[],
            errors=["Name is empty after normalization"]
        )
    
    # Check character validity
    if not validate_name_characters(normalized):
        errors.append("Name contains invalid characters. Use only letters, spaces, hyphens, apostrophes, and periods")
    
    # Check length constraints
    if len(normalized) > 100:
        errors.append("Name is too long (maximum 100 characters)")
    elif len(normalized) > 50:
        warnings.append("Name is quite long - consider using a shorter version")
    
    # Check for suspicious patterns
    if normalized != name.strip():
        warnings.append("Name was normalized (whitespace or Unicode characters adjusted)")
    
    # Check for all caps or all lowercase (might be formatting issue)
    if normalized.isupper() and len(normalized) > 3:
        warnings.append("Name is all uppercase - consider proper capitalization")
    elif normalized.islower() and len(normalized) > 3:
        warnings.append("Name is all lowercase - consider proper capitalization")
    
    # Check for repeated characters (possible typos)
    if re.search(r'(.)\1{2,}', normalized):
        warnings.append("Name contains repeated characters - please verify spelling")
    
    return NameValidationResult(
        is_valid=len(errors) == 0,
        normalized_name=normalized,
        warnings=warnings,
        errors=errors
    )


def analyze_name_duplicates(names: List[str]) -> DuplicateAnalysis:
    """
    Analyze a list of names for duplicates and similar names.
    
    Args:
        names: List of names to analyze
        
    Returns:
        DuplicateAnalysis with detected issues
    """
    exact_duplicates = []
    similar_names = []
    case_only_differences = []
    
    # Normalize all names first
    normalized_names = [normalize_name(name) for name in names]
    
    # Check for duplicates and similarities
    for i in range(len(normalized_names)):
        for j in range(i + 1, len(normalized_names)):
            name1 = normalized_names[i]
            name2 = normalized_names[j]
            
            if not name1 or not name2:
                continue
            
            # Check for exact duplicates (case-insensitive)
            if name1.lower() == name2.lower():
                if name1 == name2:
                    exact_duplicates.append((names[i], names[j]))
                else:
                    case_only_differences.append((names[i], names[j]))
            else:
                # Check for similar names
                similarity = calculate_name_similarity(name1, name2)
                if similarity > 0.8:  # Very similar names
                    similar_names.append((names[i], names[j], similarity))
    
    return DuplicateAnalysis(
        exact_duplicates=exact_duplicates,
        similar_names=similar_names,
        case_only_differences=case_only_differences
    )


def validate_engineer_list(names: List[str]) -> Dict[str, any]:
    """
    Validate a complete list of engineer names.
    
    Args:
        names: List of engineer names
        
    Returns:
        Dictionary with validation results and normalized names
    """
    if len(names) != 6:
        return {
            "is_valid": False,
            "errors": [f"Expected exactly 6 engineers, got {len(names)}"],
            "warnings": [],
            "normalized_names": [],
            "duplicate_analysis": None
        }
    
    # Validate each name individually
    individual_results = [validate_single_name(name) for name in names]
    
    # Collect all errors and warnings
    all_errors = []
    all_warnings = []
    normalized_names = []
    
    for i, result in enumerate(individual_results):
        if not result.is_valid:
            all_errors.extend([f"Engineer {i+1}: {error}" for error in result.errors])
        
        all_warnings.extend([f"Engineer {i+1}: {warning}" for warning in result.warnings])
        normalized_names.append(result.normalized_name)
    
    # Analyze duplicates
    duplicate_analysis = analyze_name_duplicates(names)
    
    # Add duplicate errors
    if duplicate_analysis.exact_duplicates:
        for name1, name2 in duplicate_analysis.exact_duplicates:
            all_errors.append(f"Duplicate names: '{name1}' and '{name2}'")
    
    if duplicate_analysis.case_only_differences:
        for name1, name2 in duplicate_analysis.case_only_differences:
            all_errors.append(f"Names differ only by case: '{name1}' and '{name2}'")
    
    # Add similarity warnings
    if duplicate_analysis.similar_names:
        for name1, name2, similarity in duplicate_analysis.similar_names:
            all_warnings.append(f"Very similar names: '{name1}' and '{name2}' ({similarity:.1%} similar)")
    
    return {
        "is_valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
        "normalized_names": normalized_names,
        "duplicate_analysis": duplicate_analysis
    }


def suggest_name_corrections(name: str, valid_names: List[str]) -> List[str]:
    """
    Suggest corrections for a potentially misspelled name.
    
    Args:
        name: Name that might be misspelled
        valid_names: List of known valid names
        
    Returns:
        List of suggested corrections, ordered by similarity
    """
    if not name or not valid_names:
        return []
    
    suggestions = []
    normalized_input = normalize_name(name)
    
    for valid_name in valid_names:
        similarity = calculate_name_similarity(normalized_input, valid_name)
        if similarity > 0.6:  # Reasonable similarity threshold
            suggestions.append((valid_name, similarity))
    
    # Sort by similarity (highest first)
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    return [name for name, _ in suggestions[:3]]  # Return top 3 suggestions