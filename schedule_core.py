from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import asdict
import pandas as pd

from models import ScheduleResult, FairnessReport, DecisionEntry, ScheduleMetadata, EngineerStats, WeekendCompensation
from export_manager import ExportManager, convert_dataframe_to_schedule_data, create_basic_fairness_report, create_basic_metadata
from lib.invariant_checker import ScheduleInvariantChecker
from lib.logging_utils import logger
from lib.enhanced_display import enhance_schedule_display, format_shift_time_display, format_status_display
import numpy as np

def nearest_previous_sunday(d: date) -> date:
    return d - timedelta(days=(d.weekday()+1) % 7)

def build_rotation(engineers: List[str], seed: int=0) -> List[str]:
    seed = seed % len(engineers)
    return engineers[seed:] + engineers[:seed]

def is_weekday(d: date) -> bool:
    return d.weekday() < 5  # Mon=0..Sun=6

def week_index(start_sunday: date, d: date) -> int:
    return (d - start_sunday).days // 7

class EnhancedFairnessTracker:
    """Enhanced fairness tracking with assignment weighting."""
    
    def __init__(self, engineers: List[str]):
        self.engineers = engineers
        self.assignment_history: Dict[str, Dict[str, int]] = {}
        self.weekend_assignments: Dict[str, int] = {}
        self.role_distribution_variance: Dict[str, float] = {}
        
        # Initialize tracking for all engineers
        for engineer in engineers:
            self.assignment_history[engineer] = {
                'weekend': 0, 'oncall': 0, 'early': 0, 'chat': 0, 'appointments': 0
            }
            self.weekend_assignments[engineer] = 0
    
    def track_assignment(self, engineer: str, role: str, weight: float = 1.0):
        """Track role assignment with configurable weighting."""
        if engineer in self.assignment_history:
            if role in self.assignment_history[engineer]:
                self.assignment_history[engineer][role] += weight
            if role == 'weekend':
                self.weekend_assignments[engineer] += 1
            
            # Update role distribution variance
            self._update_role_variance(role)
    
    def _update_role_variance(self, role: str):
        """Update variance calculation for a specific role."""
        role_counts = [self.assignment_history[eng][role] for eng in self.engineers]
        if len(role_counts) > 1:
            mean_count = sum(role_counts) / len(role_counts)
            variance = sum((count - mean_count) ** 2 for count in role_counts) / len(role_counts)
            self.role_distribution_variance[role] = variance
        else:
            self.role_distribution_variance[role] = 0.0
    
    def get_fairness_weights(self, role: str) -> Dict[str, float]:
        """Get fairness weights for role assignment (lower = more preferred)."""
        weights = {}
        role_counts = [self.assignment_history[eng][role] for eng in self.engineers]
        min_count = min(role_counts) if role_counts else 0
        
        for engineer in self.engineers:
            current_count = self.assignment_history[engineer][role]
            # Engineers with fewer assignments get lower weights (higher preference)
            weights[engineer] = max(0.0, current_count - min_count)
        
        return weights
    
    def get_weekend_fairness_order(self, base_rotation: List[str]) -> List[str]:
        """Get weekend assignment order considering fairness."""
        weights = self.get_fairness_weights('weekend')
        
        # Sort by fairness weight (ascending), then by original rotation order
        return sorted(base_rotation, key=lambda eng: (weights.get(eng, 0), base_rotation.index(eng)))
    
    def get_role_distribution_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of role distribution including variance and fairness metrics."""
        summary = {}
        
        for role in ['weekend', 'oncall', 'early', 'chat', 'appointments']:
            role_counts = [self.assignment_history[eng][role] for eng in self.engineers]
            
            summary[role] = {
                'total_assignments': sum(role_counts),
                'min_assignments': min(role_counts) if role_counts else 0,
                'max_assignments': max(role_counts) if role_counts else 0,
                'variance': self.role_distribution_variance.get(role, 0.0),
                'range': max(role_counts) - min(role_counts) if role_counts else 0
            }
        
        return summary
    
    def suggest_fairness_improvements(self) -> List[str]:
        """Generate actionable suggestions for improving fairness."""
        suggestions = []
        summary = self.get_role_distribution_summary()
        
        for role, stats in summary.items():
            if stats['range'] > 2:  # Significant imbalance
                # Find engineers with high and low assignment counts
                role_counts = [(eng, self.assignment_history[eng][role]) for eng in self.engineers]
                role_counts.sort(key=lambda x: x[1])
                
                lowest = role_counts[0]
                highest = role_counts[-1]
                
                if highest[1] - lowest[1] > 2:
                    suggestions.append(
                        f"Role '{role}': Consider assigning more to {lowest[0]} ({lowest[1]} assignments) "
                        f"and fewer to {highest[0]} ({highest[1]} assignments)"
                    )
        
        return suggestions
    
    def calculate_overall_fairness_score(self) -> float:
        """Calculate overall fairness score using Gini coefficient across all roles."""
        total_assignments = []
        
        for engineer in self.engineers:
            total = sum(self.assignment_history[engineer].values())
            total_assignments.append(total)
        
        return calculate_gini_coefficient(total_assignments)
    
    def get_engineer_workload_analysis(self) -> Dict[str, Dict[str, float]]:
        """Get detailed workload analysis for each engineer."""
        analysis = {}
        
        # Calculate total assignments for normalization
        all_totals = []
        for engineer in self.engineers:
            total = sum(self.assignment_history[engineer].values())
            all_totals.append(total)
        
        avg_total = sum(all_totals) / len(all_totals) if all_totals else 0
        
        for engineer in self.engineers:
            engineer_assignments = self.assignment_history[engineer]
            total_assignments = sum(engineer_assignments.values())
            
            analysis[engineer] = {
                'total_assignments': total_assignments,
                'deviation_from_average': total_assignments - avg_total,
                'workload_percentage': (total_assignments / sum(all_totals) * 100) if sum(all_totals) > 0 else 0,
                'role_breakdown': engineer_assignments.copy(),
                'fairness_rank': 0  # Will be calculated below
            }
        
        # Calculate fairness ranks (1 = most underutilized, len(engineers) = most overutilized)
        sorted_engineers = sorted(analysis.items(), key=lambda x: x[1]['total_assignments'])
        for rank, (engineer, data) in enumerate(sorted_engineers, 1):
            analysis[engineer]['fairness_rank'] = rank
        
        return analysis
    
    def get_role_specific_gini_coefficients(self) -> Dict[str, float]:
        """Calculate Gini coefficient for each role type separately."""
        role_gini = {}
        
        for role in ['weekend', 'oncall', 'early', 'chat', 'appointments']:
            role_counts = [self.assignment_history[eng][role] for eng in self.engineers]
            role_gini[role] = calculate_gini_coefficient(role_counts)
        
        return role_gini
    
    def identify_fairness_outliers(self, threshold: float = 1.5) -> Dict[str, List[str]]:
        """Identify engineers who are outliers in terms of assignment distribution."""
        analysis = self.get_engineer_workload_analysis()
        avg_assignments = sum(data['total_assignments'] for data in analysis.values()) / len(analysis)
        
        outliers = {
            'overloaded': [],
            'underutilized': []
        }
        
        for engineer, data in analysis.items():
            deviation = abs(data['deviation_from_average'])
            if deviation > threshold:
                if data['deviation_from_average'] > 0:  # Above average
                    outliers['overloaded'].append(engineer)
                else:  # Below average
                    outliers['underutilized'].append(engineer)
        
        return outliers
    
    def generate_rebalancing_recommendations(self) -> List[str]:
        """Generate specific recommendations for rebalancing assignments."""
        recommendations = []
        outliers = self.identify_fairness_outliers()
        role_gini = self.get_role_specific_gini_coefficients()
        
        # Identify most problematic roles
        problematic_roles = [(role, gini) for role, gini in role_gini.items() if gini > 0.2]
        problematic_roles.sort(key=lambda x: x[1], reverse=True)
        
        if problematic_roles:
            worst_role = problematic_roles[0]
            recommendations.append(f"Priority: Focus on rebalancing '{worst_role[0]}' role (Gini: {worst_role[1]:.3f})")
        
        # Specific engineer recommendations
        if outliers['overloaded'] and outliers['underutilized']:
            overloaded = outliers['overloaded'][0]  # Most overloaded
            underutilized = outliers['underutilized'][0]  # Most underutilized
            
            recommendations.append(f"Suggested swap: Reduce assignments for {overloaded}, increase for {underutilized}")
            
            # Find specific roles to swap
            overloaded_roles = self.assignment_history[overloaded]
            underutilized_roles = self.assignment_history[underutilized]
            
            for role in ['weekend', 'oncall', 'early', 'chat', 'appointments']:
                diff = overloaded_roles[role] - underutilized_roles[role]
                if diff > 1:
                    recommendations.append(f"  - Consider transferring {role} assignments from {overloaded} to {underutilized}")
        
        return recommendations
    
    def track_assignment_with_weight(self, engineer: str, role: str, date: str, weight: float = 1.0):
        """Track role assignment with configurable weighting for fairness (enhanced version)."""
        if engineer in self.assignment_history:
            if role in self.assignment_history[engineer]:
                self.assignment_history[engineer][role] += weight
            
            # Special handling for weekend assignments
            if role == 'weekend':
                self.weekend_assignments[engineer] += 1
            
            # Update role distribution variance
            self._update_role_variance(role)
    
    def get_weighted_workload(self, engineer: str, role_weights: Dict[str, float] = None) -> float:
        """Calculate weighted workload considering role difficulty/desirability."""
        if role_weights is None:
            # Default weights - higher values for more demanding roles
            role_weights = {
                'weekend': 2.0,    # Weekend work is more demanding
                'oncall': 1.5,     # On-call has responsibility burden
                'early': 1.2,      # Early shifts are less desirable
                'chat': 1.0,       # Standard weight
                'appointments': 1.0 # Standard weight
            }
        
        if engineer not in self.assignment_history:
            return 0.0
        
        weighted_total = 0.0
        for role, count in self.assignment_history[engineer].items():
            weight = role_weights.get(role, 1.0)
            weighted_total += count * weight
        
        return weighted_total


def weekend_worker_for_week(engineers_rotated: List[str], week_idx: int) -> str:
    n = len(engineers_rotated)
    return engineers_rotated[week_idx % n]


def calculate_fairness_weighted_selection(candidates: List[str], role: str, 
                                        fairness_tracker: 'EnhancedFairnessTracker',
                                        base_rotation_order: List[str] = None) -> List[str]:
    """
    Calculate fairness-weighted selection order for role assignment.
    
    Args:
        candidates: List of candidate engineers for assignment
        role: Role being assigned ('weekend', 'oncall', 'early', 'chat', 'appointments')
        fairness_tracker: Fairness tracker for weighted selection
        base_rotation_order: Optional base rotation order for tiebreaking
    
    Returns:
        List of candidates ordered by fairness preference (most fair first)
    """
    if not candidates or not fairness_tracker:
        return candidates
    
    # Get fairness weights for this role (lower weight = higher preference)
    fairness_weights = fairness_tracker.get_fairness_weights(role)
    
    # If no base rotation provided, use alphabetical order for consistency
    if base_rotation_order is None:
        base_rotation_order = sorted(candidates)
    
    # Sort by fairness weight (ascending), then by rotation order as tiebreaker
    fairness_ordered = sorted(candidates, 
                             key=lambda eng: (fairness_weights.get(eng, 0), 
                                            base_rotation_order.index(eng) if eng in base_rotation_order else len(base_rotation_order)))
    
    return fairness_ordered


def apply_fairness_impact_tracking(engineer: str, role: str, date: str, 
                                 fairness_tracker: 'EnhancedFairnessTracker',
                                 decision_log: List[DecisionEntry],
                                 impact_weight: float = 1.0):
    """
    Track fairness impact of assignment decisions.
    
    Args:
        engineer: Engineer being assigned
        role: Role being assigned
        date: Date of assignment
        fairness_tracker: Fairness tracker to update
        decision_log: Decision log to append fairness impact to
        impact_weight: Weight of this assignment for fairness calculation
    """
    if not fairness_tracker:
        return
    
    # Track the assignment with weight
    fairness_tracker.track_assignment_with_weight(engineer, role, date, impact_weight)
    
    # Calculate fairness impact
    pre_assignment_score = fairness_tracker.calculate_overall_fairness_score()
    
    # Add fairness impact information to the most recent decision log entry
    if decision_log:
        latest_entry = decision_log[-1]
        if hasattr(latest_entry, 'fairness_impact'):
            latest_entry.fairness_impact = impact_weight
        # Add fairness context to the reason
        fairness_weights = fairness_tracker.get_fairness_weights(role)
        engineer_weight = fairness_weights.get(engineer, 0)
        latest_entry.reason += f" (fairness weight: {engineer_weight}, impact: {impact_weight})"


def get_fairness_weighted_rotation_order(engineers: List[str], role: str, seed: int, 
                                       available_engineers: List[str],
                                       fairness_tracker: 'EnhancedFairnessTracker' = None) -> List[str]:
    """
    Get rotation order with fairness weighting applied.
    
    Args:
        engineers: Full list of engineers for rotation calculation
        role: Role being assigned
        seed: Rotation seed
        available_engineers: Engineers available for assignment
        fairness_tracker: Optional fairness tracker for weighted selection
    
    Returns:
        List of available engineers in fairness-weighted rotation order
    """
    if not available_engineers:
        return []
    
    # Get base rotation order
    base_rotation = build_rotation(engineers, seed)
    available_in_rotation_order = [eng for eng in base_rotation if eng in available_engineers]
    
    # Apply fairness weighting if tracker is available
    if fairness_tracker:
        return calculate_fairness_weighted_selection(available_in_rotation_order, role, fairness_tracker, base_rotation)
    
    return available_in_rotation_order


def enhanced_weekend_assignment(engineers: List[str], week_idx: int, fairness_tracker: 'EnhancedFairnessTracker', 
                               base_seed: int = 0) -> str:
    """
    Enhanced weekend assignment that considers fairness weighting.
    Builds upon existing build_rotation and weekend_worker_for_week functions.
    """
    # Get base rotation
    base_rotation = build_rotation(engineers, base_seed)
    
    # Apply fairness weighting using new fairness-weighted selection
    fairness_ordered = calculate_fairness_weighted_selection(base_rotation, 'weekend', fairness_tracker, base_rotation)
    
    # Select weekend worker using fairness-weighted rotation
    selected_engineer = fairness_ordered[week_idx % len(fairness_ordered)]
    
    # Track the assignment with fairness impact
    fairness_tracker.track_assignment_with_weight(selected_engineer, 'weekend', f"week_{week_idx}", 2.0)  # Weekend work has higher weight
    
    return selected_engineer


def get_weekend_worker_for_week(engineers: List[str], week_idx: int, fairness_tracker: 'EnhancedFairnessTracker' = None, 
                               base_seed: int = 0) -> str:
    """
    Get the weekend worker for a specific week without side effects.
    This is used for querying weekend assignments without tracking fairness.
    """
    if fairness_tracker is None:
        # Fallback to original logic when no fairness tracker available
        base_rotation = build_rotation(engineers, base_seed)
        return base_rotation[week_idx % len(base_rotation)]
    
    # Use fairness-weighted selection but don't track the assignment
    base_rotation = build_rotation(engineers, base_seed)
    fairness_ordered = calculate_fairness_weighted_selection(base_rotation, 'weekend', fairness_tracker, base_rotation)
    return fairness_ordered[week_idx % len(fairness_ordered)]


def calculate_weekend_compensation(engineer: str, weekend_date: date, pattern_type: str) -> List[date]:
    """Calculate compensatory time off for weekend workers."""
    compensation_dates = []
    
    # Weekend workers get compensatory time during the week
    if pattern_type == 'A':
        # Week A: Works Mon,Tue,Wed,Thu,Sat - gets Friday off
        friday = weekend_date + timedelta(days=6)  # Saturday + 6 days = Friday
        compensation_dates.append(friday)
    elif pattern_type == 'B':
        # Week B: Works Sun,Tue,Wed,Thu,Fri - gets Monday off  
        monday = weekend_date + timedelta(days=1)  # Sunday + 1 day = Monday
        compensation_dates.append(monday)
    
    return compensation_dates

def works_today(engineer: str, d: date, start_sunday: date, weekend_seeded: List[str], 
               fairness_tracker: 'EnhancedFairnessTracker' = None, weekend_seed: int = 0) -> bool:
    w = week_index(start_sunday, d)
    dow = d.weekday()  # Mon=0..Sun=6
    
    # Use enhanced weekend assignment logic for consistency
    if fairness_tracker is not None:
        # Extract engineers list from weekend_seeded for enhanced assignment
        engineers = weekend_seeded  # weekend_seeded is already the rotated list
        wk_current = get_weekend_worker_for_week(engineers, w, fairness_tracker, weekend_seed)
        wk_prev = get_weekend_worker_for_week(engineers, w-1, fairness_tracker, weekend_seed) if w-1 >= 0 else get_weekend_worker_for_week(engineers, -1, fairness_tracker, weekend_seed)
    else:
        # Fallback to original logic
        wk_current = weekend_worker_for_week(weekend_seeded, w)
        wk_prev = weekend_worker_for_week(weekend_seeded, w-1) if w-1 >= 0 else weekend_worker_for_week(weekend_seeded, -1)

    default_work = dow <= 4  # Mon-Fri

    if engineer == wk_current:
        # Week A: Mon,Tue,Wed,Thu,Sat
        return dow in (0,1,2,3,5)
    if engineer == wk_prev:
        # Week B: Sun,Tue,Wed,Thu,Fri
        return dow in (1,2,3,4,6)

    return default_work


def enhanced_backfill_selection(engineers: List[str], leave_today: set, expected_working: List[str],
                               d: date, start_sunday: date, weekend_seeded: List[str],
                               required_roles: List[str], fairness_tracker: 'EnhancedFairnessTracker',
                               decision_log: List[DecisionEntry], date_str: str) -> List[str]:
    """
    Enhanced backfill selection that finds candidates and considers fairness and role requirements.
    Replaces find_backfill_candidates function with integrated candidate finding and selection.
    
    Args:
        engineers: All engineers in the team
        leave_today: Set of engineers on leave today
        expected_working: Engineers expected to work today
        d: Current date
        start_sunday: Start of the schedule period
        weekend_seeded: Weekend rotation list
        required_roles: List of roles that need coverage
        fairness_tracker: Fairness tracker for weighted selection
        decision_log: Decision log for tracking selections
        date_str: Date string for logging
    
    Returns:
        List of selected backfill engineers in priority order
    """
    # Find backfill candidates (engineers not on leave and not expected to work today)
    available = [e for e in engineers if e not in leave_today]
    backfill_candidates = [e for e in available if e not in expected_working]
    
    if not backfill_candidates:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="backfill_selection_failure",
            affected_engineers=[],
            reason="No backfill candidates available for coverage",
            alternatives_considered=["Manual override required", "Adjust leave schedules", "Emergency coverage"]
        ))
        return []
    
    # Calculate fairness weights for overall workload
    overall_weights = {}
    for engineer in backfill_candidates:
        # Sum weights across all role types for overall fairness
        total_weight = 0
        for role in ['weekend', 'oncall', 'early', 'chat', 'appointments']:
            role_weights = fairness_tracker.get_fairness_weights(role)
            total_weight += role_weights.get(engineer, 0)
        overall_weights[engineer] = total_weight
    
    # Sort by overall fairness weight (ascending - lower weight = higher preference)
    selected_backfill = sorted(backfill_candidates, 
                              key=lambda eng: overall_weights.get(eng, 0))
    
    # Determine how many backfill engineers we need
    min_needed = min(len(required_roles), len(selected_backfill))
    final_selection = selected_backfill[:min_needed]
    
    # Log the intelligent backfill selection with candidate finding details
    alternatives = selected_backfill[min_needed:min_needed+3] if len(selected_backfill) > min_needed else []
    
    decision_log.append(DecisionEntry(
        date=date_str,
        decision_type="enhanced_backfill_selection",
        affected_engineers=final_selection,
        reason=f"Found {len(backfill_candidates)} candidates, selected {len(final_selection)} based on fairness weighting for {len(required_roles)} required roles",
        alternatives_considered=alternatives
    ))
    
    return final_selection


def calculate_leave_impact_on_fairness(leave_map: Dict[str, set], engineers: List[str]) -> Dict[str, float]:
    """
    Calculate how leave affects fairness distribution.
    
    Args:
        leave_map: Map of engineer names to sets of leave dates
        engineers: List of all engineers
    
    Returns:
        Dictionary mapping engineer names to leave impact scores
    """
    leave_impact = {}
    
    for engineer in engineers:
        leave_days = len(leave_map.get(engineer, set()))
        
        # Calculate impact as percentage of potential work days
        # Higher leave days should result in lower penalty for missing assignments
        total_possible_days = 365  # Approximate annual work days
        leave_impact[engineer] = leave_days / total_possible_days if total_possible_days > 0 else 0.0
    
    return leave_impact


def suggest_leave_alternatives(conflicts: List[str], available_engineers: List[str], 
                              date_str: str) -> List[str]:
    """
    Suggest alternative coverage strategies when leave creates conflicts.
    
    Args:
        conflicts: List of conflict descriptions
        available_engineers: Engineers available for alternative assignments
        date_str: Date string for context
    
    Returns:
        List of alternative suggestions
    """
    suggestions = []
    
    if conflicts:
        suggestions.append(f"Leave conflicts detected on {date_str}")
        
        if available_engineers:
            suggestions.append(f"Consider reassigning roles to: {', '.join(available_engineers[:3])}")
        else:
            suggestions.append("No alternative engineers available - manual intervention required")
        
        suggestions.append("Consider adjusting leave schedules to avoid coverage gaps")
        suggestions.append("Evaluate emergency coverage protocols")
    
    return suggestions


def process_leave_with_enhanced_logic(leave: List, engineers: List[str]) -> Dict[str, set]:
    """
    Process leave entries with enhanced validation and conflict detection.
    
    Args:
        leave: List of leave entries (can be DataFrame rows or dict-like objects)
        engineers: List of all engineers for validation
    
    Returns:
        Dictionary mapping engineer names to sets of leave dates
    """
    leave_map = {}
    
    # Initialize empty sets for all engineers
    for engineer in engineers:
        leave_map[engineer] = set()
    
    # Process leave entries
    for entry in leave:
        # Handle both DataFrame rows and dict-like objects
        if hasattr(entry, 'Engineer'):
            engineer_name = entry.Engineer
            leave_date = entry.Date
        elif isinstance(entry, dict):
            engineer_name = entry.get('Engineer', entry.get('engineer', ''))
            leave_date = entry.get('Date', entry.get('date', ''))
        else:
            # Skip invalid entries
            continue
        
        # Validate engineer name
        if engineer_name in engineers:
            # Convert date if it's a string
            if isinstance(leave_date, str):
                try:
                    from datetime import datetime
                    leave_date = datetime.strptime(leave_date, '%Y-%m-%d').date()
                except ValueError:
                    continue  # Skip invalid date formats
            
            leave_map[engineer_name].add(leave_date)
    
    return leave_map


def should_avoid_weekend_worker(engineer: str, current_date: date, start_sunday: date, weekend_seeded: List[str],
                              fairness_tracker: 'EnhancedFairnessTracker' = None, weekend_seed: int = 0) -> bool:
    """
    Check if engineer should be avoided for on-call due to weekend work.
    
    Args:
        engineer: Engineer name to check
        current_date: Date being scheduled
        start_sunday: Start date of the schedule (must be Sunday)
        weekend_seeded: Weekend rotation order
        fairness_tracker: Optional fairness tracker for enhanced weekend assignment
        weekend_seed: Weekend rotation seed
    
    Returns:
        True if engineer should be avoided for on-call assignment
    """
    current_week = week_index(start_sunday, current_date)
    
    # Check if engineer works weekend this week using enhanced logic
    if fairness_tracker is not None:
        engineers = weekend_seeded  # weekend_seeded is already the rotated list
        current_weekend_worker = get_weekend_worker_for_week(engineers, current_week, fairness_tracker, weekend_seed)
    else:
        current_weekend_worker = weekend_worker_for_week(weekend_seeded, current_week)
    
    if engineer == current_weekend_worker:
        return True
    
    # If it's Friday, also check if engineer works weekend next week
    if current_date.weekday() == 4:  # Friday
        if fairness_tracker is not None:
            next_weekend_worker = get_weekend_worker_for_week(engineers, current_week + 1, fairness_tracker, weekend_seed)
        else:
            next_weekend_worker = weekend_worker_for_week(weekend_seeded, current_week + 1)
        
        if engineer == next_weekend_worker:
            return True
    
    return False


def select_second_early_engineer(available_engineers: List[str], oncall_engineer: str, 
                               engineers: List[str], seeds: Dict[str, int], day_idx: int,
                               fairness_tracker: 'EnhancedFairnessTracker' = None) -> str:
    """
    Select second early shift engineer based on fairness and availability.
    
    Args:
        available_engineers: List of engineers available for early shift (excluding oncall)
        oncall_engineer: The engineer assigned to oncall (already assigned as Early1)
        engineers: Full list of engineers for rotation calculation
        seeds: Rotation seeds for each role
        day_idx: Day index for rotation calculation
        fairness_tracker: Optional fairness tracker for weighted selection
    
    Returns:
        Selected engineer for Early2 assignment
    """
    if not available_engineers:
        return ""
    
    # Remove oncall engineer from consideration for Early2
    remaining_engineers = [e for e in available_engineers if e != oncall_engineer]
    
    if not remaining_engineers:
        return ""
    
    # Use enhanced fairness-weighted selection for second early shift
    if fairness_tracker:
        early2_order = get_fairness_weighted_rotation_order(engineers, 'early', seeds.get("early", 0) + day_idx, 
                                                           remaining_engineers, fairness_tracker)
    else:
        # Fallback to standard rotation if no fairness tracker
        early2_order = sorted(remaining_engineers, 
                            key=lambda name: ((engineers.index(name) + seeds.get("early",0) + day_idx) % len(engineers)))
    
    selected_engineer = early2_order[0]
    
    # Track fairness impact for Early2 assignment
    if fairness_tracker:
        fairness_tracker.track_assignment_with_weight(selected_engineer, 'early', f"day_{day_idx}", 1.2)  # Early shift has moderate weight
    
    return selected_engineer


def enhanced_oncall_selection(available_engineers: List[str], current_date: date, start_sunday: date, 
                             weekend_seeded: List[str], engineers: List[str], seeds: Dict[str, int], 
                             decision_log: List[DecisionEntry], fairness_tracker: 'EnhancedFairnessTracker' = None) -> str:
    """
    Enhanced on-call selection function with conflict avoidance and fairness weighting.
    
    Args:
        available_engineers: List of engineers available for on-call assignment
        current_date: Date being scheduled
        start_sunday: Start date of the schedule (must be Sunday)
        weekend_seeded: Weekend rotation order
        engineers: Full list of engineers for rotation calculation
        seeds: Rotation seeds for each role
        decision_log: List to append decision entries to
        fairness_tracker: Optional fairness tracker for weighted selection
    
    Returns:
        Selected engineer for on-call assignment
    """
    if not available_engineers:
        return ""
    
    date_str = current_date.isoformat()
    day_idx = (current_date - start_sunday).days
    
    # Get fairness-weighted rotation order
    if fairness_tracker:
        oncall_order = get_fairness_weighted_rotation_order(engineers, 'oncall', seeds.get("oncall", 0) + day_idx, 
                                                           available_engineers, fairness_tracker)
    else:
        # Fallback to standard rotation
        oncall_order = sorted(available_engineers, key=lambda name: ((engineers.index(name) + seeds.get("oncall",0) + day_idx) % len(engineers)))
    
    # Separate engineers who should be avoided from those who shouldn't
    non_weekend_candidates = [e for e in oncall_order if not should_avoid_weekend_worker(e, current_date, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0))]
    weekend_workers_to_avoid = [e for e in oncall_order if should_avoid_weekend_worker(e, current_date, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0))]
    
    # Select engineer and determine rationale
    if non_weekend_candidates:
        selected_engineer = non_weekend_candidates[0]
        reason = f"Enhanced OnCall selection with fairness weighting - avoided weekend workers: {', '.join(weekend_workers_to_avoid)}"
        alternatives = non_weekend_candidates[1:3] if len(non_weekend_candidates) > 1 else weekend_workers_to_avoid[:2]
    else:
        # Fallback to any available engineer when no non-weekend options exist
        selected_engineer = oncall_order[0]
        reason = f"Enhanced OnCall selection - fallback used (no non-weekend options available)"
        alternatives = oncall_order[1:3] if len(oncall_order) > 1 else []
    
    # Log decision with detailed rationale
    decision_log.append(DecisionEntry(
        date=date_str,
        decision_type="enhanced_oncall_assignment",
        affected_engineers=[selected_engineer],
        reason=reason,
        alternatives_considered=alternatives
    ))
    
    # Track fairness impact
    if fairness_tracker:
        apply_fairness_impact_tracking(selected_engineer, 'oncall', date_str, fairness_tracker, decision_log, 1.5)  # OnCall has higher weight
    
    return selected_engineer


def validate_scheduling_conflicts(roles: Dict[str, str], working: List[str], d: date) -> List[str]:
    """
    Validate for scheduling conflicts and impossible scenarios.
    Returns list of conflict descriptions.
    """
    conflicts = []
    
    # Check for duplicate assignments
    assigned_engineers = [eng for eng in roles.values() if eng]
    if len(assigned_engineers) != len(set(assigned_engineers)):
        duplicates = [eng for eng in set(assigned_engineers) if assigned_engineers.count(eng) > 1]
        conflicts.append(f"Engineer(s) assigned to multiple roles: {', '.join(duplicates)}")
    
    # Check if assigned engineers are actually working
    for role, engineer in roles.items():
        if engineer and engineer not in working:
            conflicts.append(f"{engineer} assigned to {role} but not scheduled to work")
    
    # Check weekend OnCall constraint (OnCall should not work weekends)
    if d.weekday() in [5, 6]:  # Saturday or Sunday
        oncall = roles.get("OnCall", "")
        if oncall and oncall in working:
            conflicts.append(f"{oncall} assigned OnCall on weekend (violates no-oncall-on-weekends rule)")
    
    return conflicts


def generate_alternative_suggestions(roles: Dict[str, str], working: List[str], 
                                   backfill_candidates: List[str], conflicts: List[str]) -> List[str]:
    """
    Generate alternative suggestions for manual overrides when conflicts exist.
    """
    suggestions = []
    
    if conflicts:
        suggestions.append("Consider manual role reassignment to resolve conflicts")
        
        # Suggest backfill if available
        if backfill_candidates:
            suggestions.append(f"Available backfill engineers: {', '.join(backfill_candidates)}")
        
        # Suggest role swapping if multiple people assigned
        assigned = [eng for eng in roles.values() if eng]
        if len(working) > len(assigned):
            unassigned = [eng for eng in working if eng not in assigned]
            suggestions.append(f"Unassigned working engineers available: {', '.join(unassigned)}")
    
    return suggestions


def get_role_rotation_order(engineers: List[str], role: str, seed: int, day_idx: int, 
                          available_engineers: List[str], fairness_tracker: 'EnhancedFairnessTracker' = None) -> List[str]:
    """
    Get rotation order considering fairness weighting for role assignment.
    
    Args:
        engineers: Full list of engineers for rotation calculation
        role: Role being assigned ('chat', 'appointments', etc.)
        seed: Rotation seed for this role
        day_idx: Day index for rotation calculation
        available_engineers: Engineers available for assignment
        fairness_tracker: Optional fairness tracker for weighted selection
    
    Returns:
        List of engineers in preferred assignment order
    """
    if not available_engineers:
        return []
    
    # Get base rotation order
    base_order = sorted(available_engineers, 
                       key=lambda name: ((engineers.index(name) + seed + day_idx) % len(engineers)))
    
    # Apply fairness weighting if tracker is available
    if fairness_tracker:
        fairness_weights = fairness_tracker.get_fairness_weights(role)
        
        # Sort by fairness weight (ascending - lower weight = higher preference), 
        # then by rotation order as tiebreaker
        fairness_order = sorted(base_order, 
                              key=lambda name: (fairness_weights.get(name, 0), 
                                              base_order.index(name)))
        return fairness_order
    
    return base_order


def handle_engineer_unavailability(expected_engineers: List[str], unavailable_engineers: List[str], 
                                 role: str, date_str: str, decision_log: List[DecisionEntry]) -> List[str]:
    """
    Handle engineer unavailability by finding suitable alternatives and logging decisions.
    
    Args:
        expected_engineers: Engineers expected to be available for the role
        unavailable_engineers: Engineers who are unavailable (on leave, etc.)
        role: Role being assigned
        date_str: Date string for logging
        decision_log: List to append decision entries to
    
    Returns:
        List of available engineers after handling unavailability
    """
    available = [e for e in expected_engineers if e not in unavailable_engineers]
    
    if unavailable_engineers:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type=f"{role}_unavailability_handling",
            affected_engineers=list(unavailable_engineers),
            reason=f"Engineers unavailable for {role} assignment due to leave or other conflicts",
            alternatives_considered=available[:3] if available else ["No alternatives available"]
        ))
    
    return available


def get_alternative_selection_candidates(rotation_order: List[str], selected_engineer: str, 
                                       max_alternatives: int = 3) -> List[str]:
    """
    Get alternative candidates for role assignment with detailed reasoning.
    
    Args:
        rotation_order: Full rotation order for the role
        selected_engineer: Engineer that was selected
        max_alternatives: Maximum number of alternatives to return
    
    Returns:
        List of alternative engineers that could have been selected
    """
    if not rotation_order or selected_engineer not in rotation_order:
        return []
    
    # Get engineers after the selected one in rotation order
    selected_idx = rotation_order.index(selected_engineer)
    alternatives = rotation_order[selected_idx + 1:selected_idx + 1 + max_alternatives]
    
    # If we don't have enough alternatives, wrap around to the beginning
    if len(alternatives) < max_alternatives:
        remaining_needed = max_alternatives - len(alternatives)
        alternatives.extend(rotation_order[:min(remaining_needed, selected_idx)])
    
    return alternatives


def enhanced_role_assignment(available_engineers: List[str], role: str, engineers: List[str], 
                           seeds: Dict[str, int], day_idx: int, date_str: str,
                           decision_log: List[DecisionEntry], 
                           fairness_tracker: 'EnhancedFairnessTracker' = None) -> str:
    """
    Enhanced role assignment with better conflict handling and fairness-weighted selection.
    
    Args:
        available_engineers: Engineers available for assignment
        role: Role being assigned ('chat', 'appointments', etc.)
        engineers: Full list of engineers for rotation calculation
        seeds: Rotation seeds for each role
        day_idx: Day index for rotation calculation
        date_str: Date string for logging
        decision_log: List to append decision entries to
        fairness_tracker: Optional fairness tracker for weighted selection
    
    Returns:
        Selected engineer for the role
    """
    if not available_engineers:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type=f"{role}_assignment_failure",
            affected_engineers=[],
            reason=f"No engineers available for {role} assignment",
            alternatives_considered=["Manual assignment required", "Adjust leave schedules", "Emergency coverage"]
        ))
        return ""
    
    # Get fairness-weighted rotation order
    if fairness_tracker:
        rotation_order = get_fairness_weighted_rotation_order(engineers, role, seeds.get(role, 0) + day_idx, 
                                                             available_engineers, fairness_tracker)
    else:
        # Fallback to standard rotation
        rotation_order = sorted(available_engineers, 
                               key=lambda name: ((engineers.index(name) + seeds.get(role, 0) + day_idx) % len(engineers)))
    
    # Select the first engineer in the fairness-weighted order
    selected_engineer = rotation_order[0]
    
    # Generate detailed alternatives list
    alternatives = get_alternative_selection_candidates(rotation_order, selected_engineer)
    
    # Determine reason based on whether fairness weighting was used
    if fairness_tracker:
        fairness_weights = fairness_tracker.get_fairness_weights(role)
        selected_weight = fairness_weights.get(selected_engineer, 0)
        reason = f"Enhanced {role} assignment with fairness weighting (selected weight: {selected_weight}, seed={seeds.get(role,0)}, day_offset={day_idx})"
        
        # Add fairness context to alternatives
        if alternatives:
            alt_weights = [f"{alt}(weight:{fairness_weights.get(alt, 0)})" for alt in alternatives]
            alternatives = alt_weights
    else:
        reason = f"Standard {role} rotation (seed={seeds.get(role,0)}, day_offset={day_idx})"
    
    decision_log.append(DecisionEntry(
        date=date_str,
        decision_type=f"enhanced_{role}_assignment",
        affected_engineers=[selected_engineer],
        reason=reason,
        alternatives_considered=alternatives
    ))
    
    # Track fairness impact
    if fairness_tracker:
        apply_fairness_impact_tracking(selected_engineer, role, date_str, fairness_tracker, decision_log, 1.0)  # Standard weight for daily roles
    
    return selected_engineer


def generate_day_assignments(d: date, engineers: List[str], start_sunday: date, weekend_seeded: List[str],
                             leave_map: Dict[str,set], seeds: Dict[str,int],
                             assign_early_on_weekends: bool=False, decision_log: List[DecisionEntry] = None,
                             fairness_tracker: 'EnhancedFairnessTracker' = None):
    """
    Generate role assignments for a single day with enhanced conflict resolution and backfill logic.
    
    Args:
        d: Date to generate assignments for
        engineers: List of all engineers
        start_sunday: Start date of the schedule (must be Sunday)
        weekend_seeded: Weekend rotation order
        leave_map: Map of engineer names to sets of leave dates
        seeds: Rotation seeds for each role
        assign_early_on_weekends: Whether to assign early shifts on weekends
        decision_log: List to append decision entries to
        fairness_tracker: Enhanced fairness tracker for weighted assignments
    
    Returns:
        Tuple of (working_engineers, engineers_on_leave, role_assignments)
    """
    if decision_log is None:
        decision_log = []
    
    date_str = d.isoformat()
    
    # Determine who should be working based on weekend rotation
    expected_working = [e for e in engineers if works_today(e, d, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0))]
    leave_today = set([e for e, days in leave_map.items() if d in days])
    
    # Log leave exclusions
    if leave_today:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="leave_exclusion",
            affected_engineers=list(leave_today),
            reason=f"Engineers excluded due to scheduled leave on {d.strftime('%A, %B %d')}",
            alternatives_considered=["Enhanced backfill selection will find alternatives"]
        ))
    
    # Initial working list after leave exclusions
    working = [e for e in expected_working if e not in leave_today]
    
    # Enhanced intelligent backfill logic
    min_required = 3 if is_weekday(d) else 1  # Weekdays need Chat, OnCall, Appointments
    required_roles = ["Chat", "OnCall", "Appointments"] if is_weekday(d) else ["OnCall"]
    
    if len(working) < min_required:
        # Use enhanced backfill selection with integrated candidate finding and fairness consideration
        if fairness_tracker:
            backfill_added = enhanced_backfill_selection(
                engineers, leave_today, expected_working, d, start_sunday, weekend_seeded,
                required_roles, fairness_tracker, decision_log, date_str
            )
        else:
            # Fallback to simple selection if no fairness tracker
            # Find backfill candidates manually for fallback
            available = [e for e in engineers if e not in leave_today]
            backfill_candidates = [e for e in available if e not in expected_working]
            
            needed = min_required - len(working)
            backfill_added = backfill_candidates[:needed]
            
            decision_log.append(DecisionEntry(
                date=date_str,
                decision_type="basic_backfill_assignment",
                affected_engineers=backfill_added,
                reason=f"Added {len(backfill_added)} backfill engineer(s) to meet minimum coverage of {min_required} (no fairness tracker available)",
                alternatives_considered=backfill_candidates[needed:needed+2] if len(backfill_candidates) > needed else []
            ))
        
        # Add selected backfill engineers to working list
        needed = min(min_required - len(working), len(backfill_added))
        working.extend(backfill_added[:needed])
    
    # Log if we still have insufficient coverage after backfill
    if len(working) < min_required:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="insufficient_coverage",
            affected_engineers=working,
            reason=f"Only {len(working)} engineers available for {d.strftime('%A')} requiring {min_required}+ roles",
            alternatives_considered=["Manual override required", "Adjust leave schedules", "Emergency coverage needed"]
        ))

    roles = {"Chat":"", "OnCall":"", "Appointments":"", "Early1":"", "Early2":""}

    # Assign weekday roles first to determine on-call engineer for early shift coordination
    if is_weekday(d):
        day_idx = (d - start_sunday).days
        available = working.copy()
        
        # Enhanced Chat assignment with fairness consideration
        if available:
            roles["Chat"] = enhanced_role_assignment(
                available, "chat", engineers, seeds, day_idx, date_str, decision_log, fairness_tracker
            )
            if roles["Chat"]:
                available.remove(roles["Chat"])
        
        # Enhanced OnCall assignment (avoid weekend workers if possible)
        if available:
            oncall_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("oncall",0) + day_idx) % len(engineers)))
            
            # Use enhanced weekend worker avoidance logic
            non_weekend_oncall = [e for e in oncall_order if not should_avoid_weekend_worker(e, d, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0))]
            weekend_workers_to_avoid = [e for e in oncall_order if should_avoid_weekend_worker(e, d, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0))]
            
            # Apply fairness weighting to non-weekend candidates if available
            if non_weekend_oncall and fairness_tracker:
                fairness_weights = fairness_tracker.get_fairness_weights('oncall')
                non_weekend_oncall = sorted(non_weekend_oncall, 
                                          key=lambda name: (fairness_weights.get(name, 0), 
                                                          oncall_order.index(name)))
            
            if non_weekend_oncall:
                roles["OnCall"] = non_weekend_oncall[0]
                reason = f"Enhanced OnCall assignment with fairness weighting - avoided weekend workers: {', '.join(weekend_workers_to_avoid)}"
                alternatives = non_weekend_oncall[1:3] if len(non_weekend_oncall) > 1 else weekend_workers_to_avoid[:2]
            else:
                # Apply fairness weighting to fallback candidates
                if fairness_tracker:
                    fairness_weights = fairness_tracker.get_fairness_weights('oncall')
                    oncall_order = sorted(oncall_order, 
                                        key=lambda name: (fairness_weights.get(name, 0), 
                                                        oncall_order.index(name)))
                
                roles["OnCall"] = oncall_order[0]
                reason = f"Enhanced OnCall assignment with fairness weighting - no non-weekend options available, using fallback"
                alternatives = oncall_order[1:3] if len(oncall_order) > 1 else []
            
            # Track assignment for fairness
            if fairness_tracker:
                fairness_tracker.track_assignment(roles["OnCall"], 'oncall')
            
            available.remove(roles["OnCall"])
            
            decision_log.append(DecisionEntry(
                date=date_str,
                decision_type="enhanced_oncall_assignment",
                affected_engineers=[roles["OnCall"]],
                reason=reason,
                alternatives_considered=alternatives
            ))
        
        # Enhanced Appointments assignment with fairness consideration
        if available:
            roles["Appointments"] = enhanced_role_assignment(
                available, "appointments", engineers, seeds, day_idx, date_str, decision_log, fairness_tracker
            )

    # Assign Early shifts (after determining on-call for weekdays)
    if is_weekday(d) or assign_early_on_weekends:
        if working:
            day_idx = (d - start_sunday).days
            early_assignments = []
            
            # For weekdays, ensure on-call engineer is always Early1
            if is_weekday(d) and roles.get("OnCall"):
                oncall_engineer = roles["OnCall"]
                
                # Ensure on-call engineer is always Early1 during weekdays
                if oncall_engineer in working:
                    roles["Early1"] = oncall_engineer
                    early_assignments.append(oncall_engineer)
                    
                    # Select second early shift engineer using enhanced selection logic
                    second_early_engineer = select_second_early_engineer(
                        working, oncall_engineer, engineers, seeds, day_idx, fairness_tracker
                    )
                    
                    if second_early_engineer:
                        roles["Early2"] = second_early_engineer
                        early_assignments.append(second_early_engineer)
                        
                        # Track assignments for fairness
                        if fairness_tracker:
                            fairness_tracker.track_assignment(oncall_engineer, 'early')
                            fairness_tracker.track_assignment(second_early_engineer, 'early')
                        
                        # Generate alternatives for decision logging
                        remaining_for_early = [e for e in working if e not in [oncall_engineer, second_early_engineer]]
                        alternatives = remaining_for_early[:2] if remaining_for_early else []
                        
                        # Log enhanced early shift assignment decision
                        decision_log.append(DecisionEntry(
                            date=date_str,
                            decision_type="enhanced_early_shift_assignment",
                            affected_engineers=early_assignments,
                            reason=f"Enhanced early shift: OnCall engineer ({oncall_engineer}) assigned as Early1, second engineer ({second_early_engineer}) selected with fairness consideration",
                            alternatives_considered=alternatives
                        ))
                    else:
                        # Only one engineer available - just assign Early1
                        if fairness_tracker:
                            fairness_tracker.track_assignment(oncall_engineer, 'early')
                        
                        decision_log.append(DecisionEntry(
                            date=date_str,
                            decision_type="enhanced_early_shift_assignment",
                            affected_engineers=early_assignments,
                            reason=f"Enhanced early shift: OnCall engineer ({oncall_engineer}) assigned as Early1, no second engineer available",
                            alternatives_considered=[]
                        ))
                else:
                    # Fallback to original logic if on-call engineer not in working list
                    order = sorted(working, key=lambda name: ((engineers.index(name) + seeds.get("early",0) + day_idx) % len(engineers)))
                    
                    if len(order) >= 1:
                        roles["Early1"] = order[0]
                        early_assignments.append(order[0])
                    if len(order) >= 2:
                        roles["Early2"] = order[1]
                        early_assignments.append(order[1])
                    
                    if early_assignments:
                        alternatives = order[2:4] if len(order) > 2 else []
                        decision_log.append(DecisionEntry(
                            date=date_str,
                            decision_type="early_shift_assignment_fallback",
                            affected_engineers=early_assignments,
                            reason=f"Early shift fallback rotation (oncall not in working list) - seed={seeds.get('early',0)}, day_offset={day_idx}",
                            alternatives_considered=alternatives
                        ))
            else:
                # Weekend early shift assignment or no on-call determined - use original logic
                order = sorted(working, key=lambda name: ((engineers.index(name) + seeds.get("early",0) + day_idx) % len(engineers)))
                
                if len(order) >= 1:
                    roles["Early1"] = order[0]
                    early_assignments.append(order[0])
                if len(order) >= 2:
                    roles["Early2"] = order[1]
                    early_assignments.append(order[1])
                
                if early_assignments:
                    alternatives = order[2:4] if len(order) > 2 else []
                    assignment_type = "weekend_early_shift_assignment" if not is_weekday(d) else "early_shift_assignment_fallback"
                    decision_log.append(DecisionEntry(
                        date=date_str,
                        decision_type=assignment_type,
                        affected_engineers=early_assignments,
                        reason=f"{'Weekend' if not is_weekday(d) else 'Fallback'} early shift rotation (seed={seeds.get('early',0)}, day_offset={day_idx})",
                        alternatives_considered=alternatives
                    ))
    
    # Validate for conflicts and generate suggestions
    conflicts = validate_scheduling_conflicts(roles, working, d)
    if conflicts:
        # Calculate backfill candidates for suggestions
        available = [e for e in engineers if e not in leave_today]
        backfill_candidates_for_suggestions = [e for e in available if e not in expected_working]
        suggestions = generate_alternative_suggestions(roles, working, backfill_candidates_for_suggestions, conflicts)
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="scheduling_conflict",
            affected_engineers=[eng for eng in roles.values() if eng],
            reason=f"Conflicts detected: {'; '.join(conflicts)}",
            alternatives_considered=suggestions
        ))
    
    return working, leave_today, roles

def make_schedule(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], leave: pd.DataFrame,
                  assign_early_on_weekends: bool=False) -> pd.DataFrame:
    assert len(engineers) == 6, "Exactly 6 engineers are required."
    weekend_seeded = build_rotation(engineers, seeds.get("weekend",0))
    fairness_tracker = EnhancedFairnessTracker(engineers)

    leave_map = {}
    if leave is not None and not leave.empty:
        leave = leave.copy()
        leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
        for e in leave["Engineer"].unique():
            leave_map[e] = set(leave.loc[leave["Engineer"]==e, "Date"].tolist())
    for e in engineers:
        leave_map.setdefault(e, set())

    days = weeks * 7
    dates = [start_sunday + timedelta(days=i) for i in range(days)]

    columns = ["Date","Day","WeekIndex","Early1","Early2","Chat","OnCall","Appointments"]
    for i in range(6):
        columns += [f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"]

    rows = []
    for d in dates:
        w = week_index(start_sunday, d)
        dow = pd.Timestamp(d).strftime("%a")
        working, leave_today, roles = generate_day_assignments(d, engineers, start_sunday, weekend_seeded, leave_map, seeds, assign_early_on_weekends, None, fairness_tracker)
        eng_cells = []
        for e in engineers:
            status = "LEAVE" if e in leave_today else ("WORK" if works_today(e, d, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0)) else "OFF")
            shift = ""
            if status == "WORK":
                if e in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    # Enhanced weekend pattern indicators
                    if pd.Timestamp(d).weekday() >= 5:  # Weekend
                        weekend_worker = enhanced_weekend_assignment(engineers, w, fairness_tracker, seeds.get("weekend", 0))
                        if e == weekend_worker:
                            pattern = 'A' if pd.Timestamp(d).weekday() == 5 else 'B'  # Sat=A, Sun=B
                            shift = f"Weekend-{pattern}"
                        else:
                            shift = "Weekend"
                    else:
                        shift = "08:00-17:00"
            eng_cells += [e, status, shift]
        row = [d, dow, w, roles["Early1"], roles["Early2"], roles["Chat"], roles["OnCall"], roles["Appointments"]] + eng_cells
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns)
    return df


def make_schedule_with_decisions(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], 
                                leave: pd.DataFrame, assign_early_on_weekends: bool=False) -> Tuple[pd.DataFrame, List[DecisionEntry], List['WeekendCompensation']]:
    """
    Generate schedule with detailed decision logging.
    
    Returns:
        Tuple of (schedule_dataframe, decision_log, weekend_compensation_tracking)
    """
    assert len(engineers) == 6, "Exactly 6 engineers are required."
    
    decision_log = []
    weekend_compensation_tracking = []
    
    # Initialize enhanced fairness tracker
    fairness_tracker = EnhancedFairnessTracker(engineers)
    
    # Log initial configuration decisions
    weekend_seeded = build_rotation(engineers, seeds.get("weekend",0))
    decision_log.append(DecisionEntry(
        date=start_sunday.isoformat(),
        decision_type="weekend_rotation_setup",
        affected_engineers=weekend_seeded,
        reason=f"Weekend rotation established with seed {seeds.get('weekend',0)}",
        alternatives_considered=[f"Alternative seed {i}" for i in range(6) if i != seeds.get('weekend',0)]
    ))

    leave_map = {}
    if leave is not None and not leave.empty:
        leave = leave.copy()
        leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
        for e in leave["Engineer"].unique():
            leave_dates = leave.loc[leave["Engineer"]==e, "Date"].tolist()
            leave_map[e] = set(leave_dates)
            
            # Log leave processing
            decision_log.append(DecisionEntry(
                date=start_sunday.isoformat(),
                decision_type="leave_processing",
                affected_engineers=[e],
                reason=f"Processed {len(leave_dates)} leave days for {e}",
                alternatives_considered=[]
            ))
    
    for e in engineers:
        leave_map.setdefault(e, set())

    days = weeks * 7
    dates = [start_sunday + timedelta(days=i) for i in range(days)]

    columns = ["Date","Day","WeekIndex","Early1","Early2","Chat","OnCall","Appointments"]
    for i in range(6):
        columns += [f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"]

    rows = []
    for d in dates:
        w = week_index(start_sunday, d)
        dow = pd.Timestamp(d).strftime("%a")
        
        # Track weekend compensation for weekend workers
        if d.weekday() == 5:  # Saturday - start of weekend
            weekend_worker = enhanced_weekend_assignment(engineers, w, fairness_tracker, seeds.get("weekend", 0))
            pattern_type = 'A'  # Week A pattern: Mon,Tue,Wed,Thu,Sat
            compensation_dates = calculate_weekend_compensation(weekend_worker, d, pattern_type)
            
            weekend_compensation_tracking.append(WeekendCompensation(
                engineer=weekend_worker,
                weekend_date=d,
                compensation_dates=compensation_dates,
                pattern_type=pattern_type
            ))
            
            # Log weekend assignment decision with fairness context
            fairness_weights = fairness_tracker.get_fairness_weights('weekend')
            alternatives = [eng for eng in weekend_seeded if eng != weekend_worker][:2]
            decision_log.append(DecisionEntry(
                date=d.isoformat(),
                decision_type="enhanced_weekend_assignment",
                affected_engineers=[weekend_worker],
                reason=f"Enhanced weekend assignment for week {w} using fairness-weighted selection (pattern {pattern_type}, fairness weight: {fairness_weights.get(weekend_worker, 0)})",
                alternatives_considered=alternatives
            ))
        
        elif d.weekday() == 6:  # Sunday - second day of weekend
            weekend_worker = enhanced_weekend_assignment(engineers, w, fairness_tracker, seeds.get("weekend", 0))
            pattern_type = 'B'  # Week B pattern: Sun,Tue,Wed,Thu,Fri
            compensation_dates = calculate_weekend_compensation(weekend_worker, d, pattern_type)
            
            # Update existing compensation tracking for this weekend
            for comp in weekend_compensation_tracking:
                if comp.engineer == weekend_worker and comp.weekend_date == d - timedelta(days=1):
                    comp.compensation_dates.extend(compensation_dates)
                    comp.pattern_type = 'A+B'  # Both Saturday and Sunday
            
            # Log Sunday weekend assignment decision with fairness context
            fairness_weights = fairness_tracker.get_fairness_weights('weekend')
            alternatives = [eng for eng in weekend_seeded if eng != weekend_worker][:2]
            decision_log.append(DecisionEntry(
                date=d.isoformat(),
                decision_type="enhanced_weekend_assignment",
                affected_engineers=[weekend_worker],
                reason=f"Enhanced weekend assignment for week {w} Sunday using fairness-weighted selection (pattern {pattern_type}, fairness weight: {fairness_weights.get(weekend_worker, 0)})",
                alternatives_considered=alternatives
            ))
        
        working, leave_today, roles = generate_day_assignments(
            d, engineers, start_sunday, weekend_seeded, leave_map, seeds, 
            assign_early_on_weekends, decision_log, fairness_tracker
        )
        
        eng_cells = []
        for e in engineers:
            status = "LEAVE" if e in leave_today else ("WORK" if works_today(e, d, start_sunday, weekend_seeded, fairness_tracker, seeds.get("weekend", 0)) else "OFF")
            shift = ""
            if status == "WORK":
                if e in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    # Enhanced weekend pattern indicators
                    if pd.Timestamp(d).weekday() >= 5:  # Weekend
                        weekend_worker = enhanced_weekend_assignment(engineers, w, fairness_tracker, seeds.get("weekend", 0))
                        if e == weekend_worker:
                            pattern = 'A' if pd.Timestamp(d).weekday() == 5 else 'B'  # Sat=A, Sun=B
                            shift = f"Weekend-{pattern}"
                        else:
                            shift = "Weekend"
                    else:
                        shift = "08:00-17:00"
            eng_cells += [e, status, shift]
        row = [d, dow, w, roles["Early1"], roles["Early2"], roles["Chat"], roles["OnCall"], roles["Appointments"]] + eng_cells
        rows.append(row)
    
    df = pd.DataFrame(rows, columns=columns)
    return df, decision_log, weekend_compensation_tracking


def calculate_fairness_report(df: pd.DataFrame, engineers: List[str]) -> FairnessReport:
    """
    Calculate comprehensive fairness analysis with per-engineer role counts,
    max-min deltas, and equity scores using Gini coefficient.
    """
    engineer_stats = {}
    
    # Initialize stats for each engineer
    for engineer in engineers:
        engineer_stats[engineer] = EngineerStats(name=engineer)
    
    # Count role assignments and work patterns
    for _, row in df.iterrows():
        # Count role assignments
        early1 = row.get("Early1", "")
        early2 = row.get("Early2", "")
        chat = row.get("Chat", "")
        oncall = row.get("OnCall", "")
        appointments = row.get("Appointments", "")
        
        if early1 in engineer_stats:
            engineer_stats[early1].early_count += 1
        if early2 in engineer_stats:
            engineer_stats[early2].early_count += 1
        if chat in engineer_stats:
            engineer_stats[chat].chat_count += 1
        if oncall in engineer_stats:
            engineer_stats[oncall].oncall_count += 1
        if appointments in engineer_stats:
            engineer_stats[appointments].appointments_count += 1
        
        # Count work days and leave days for each engineer
        for i, engineer in enumerate(engineers):
            status_col = f"Status {i+1}"
            if status_col in row:
                status = row[status_col]
                if status == "WORK":
                    engineer_stats[engineer].total_work_days += 1
                elif status == "LEAVE":
                    engineer_stats[engineer].leave_days += 1
                
                # Count weekend work (Saturday/Sunday)
                day = row.get("Day", "")
                if day in ["Sat", "Sun"] and status == "WORK":
                    engineer_stats[engineer].weekend_count += 1
    
    # Calculate max-min deltas for each role type
    oncall_counts = [stats.oncall_count for stats in engineer_stats.values()]
    weekend_counts = [stats.weekend_count for stats in engineer_stats.values()]
    early_counts = [stats.early_count for stats in engineer_stats.values()]
    chat_counts = [stats.chat_count for stats in engineer_stats.values()]
    appointments_counts = [stats.appointments_count for stats in engineer_stats.values()]
    
    max_min_deltas = {
        "oncall": max(oncall_counts) - min(oncall_counts) if oncall_counts else 0,
        "weekend": max(weekend_counts) - min(weekend_counts) if weekend_counts else 0,
        "early": max(early_counts) - min(early_counts) if early_counts else 0,
        "chat": max(chat_counts) - min(chat_counts) if chat_counts else 0,
        "appointments": max(appointments_counts) - min(appointments_counts) if appointments_counts else 0
    }
    
    # Calculate equity score using Gini coefficient
    # We'll use total role assignments as the primary equity measure
    total_role_counts = []
    for stats in engineer_stats.values():
        total_roles = (stats.oncall_count + stats.weekend_count + stats.early_count + 
                      stats.chat_count + stats.appointments_count)
        total_role_counts.append(total_roles)
    
    equity_score = calculate_gini_coefficient(total_role_counts)
    
    return FairnessReport(
        engineer_stats=engineer_stats,
        equity_score=equity_score,
        max_min_deltas=max_min_deltas
    )


def calculate_enhanced_fairness_report(df: pd.DataFrame, engineers: List[str], 
                                     leave_map: Dict[str, set] = None, 
                                     decision_log: List[DecisionEntry] = None) -> FairnessReport:
    """
    Enhanced fairness calculation with detailed insights and leave impact analysis.
    Extends existing Gini coefficient calculation with comprehensive analysis.
    
    Args:
        df: Schedule DataFrame
        engineers: List of all engineers
        leave_map: Optional map of engineer names to sets of leave dates
        decision_log: Optional decision log for additional context
    
    Returns:
        Enhanced FairnessReport with detailed insights
    """
    # Start with base fairness calculation
    base_report = calculate_fairness_report(df, engineers)
    
    # Add enhanced analysis for leave impact
    if leave_map:
        # Adjust fairness calculations to account for leave days
        for engineer_name, stats in base_report.engineer_stats.items():
            leave_days = len(leave_map.get(engineer_name, set()))
            
            # Calculate adjusted work capacity (total possible days - leave days)
            total_schedule_days = len(df)
            adjusted_capacity = max(1, total_schedule_days - leave_days)  # Avoid division by zero
            
            # Calculate workload density (assignments per available day)
            total_assignments = (stats.oncall_count + stats.weekend_count + stats.early_count + 
                               stats.chat_count + stats.appointments_count)
            
            # Store leave impact information by adding attributes to the stats object
            # This is safe because we're modifying the object after creation
            setattr(stats, 'leave_days', leave_days)
            setattr(stats, 'leave_impact_factor', leave_days / total_schedule_days if total_schedule_days > 0 else 0.0)
    
    return base_report


def calculate_enhanced_fairness_report(df: pd.DataFrame, engineers: List[str], 
                                     leave_map: Dict[str, set] = None) -> FairnessReport:
    """
    Enhanced fairness calculation that properly handles leave impact.
    Ensures leave days don't negatively affect engineer fairness scores.
    
    Args:
        df: Schedule DataFrame
        engineers: List of all engineers
        leave_map: Optional map of engineer names to sets of leave dates
    
    Returns:
        Enhanced FairnessReport with leave-adjusted calculations
    """
    engineer_stats = {}
    
    # Initialize stats for each engineer
    for engineer in engineers:
        engineer_stats[engineer] = EngineerStats(name=engineer)
    
    # Calculate leave impact if leave_map is provided
    leave_impact = {}
    if leave_map:
        leave_impact = calculate_leave_impact_on_fairness(leave_map, engineers)
    
    # Count role assignments and work patterns
    for _, row in df.iterrows():
        # Count role assignments
        early1 = row.get("Early1", "")
        early2 = row.get("Early2", "")
        chat = row.get("Chat", "")
        oncall = row.get("OnCall", "")
        appointments = row.get("Appointments", "")
        
        if early1 in engineer_stats:
            engineer_stats[early1].early_count += 1
        if early2 in engineer_stats:
            engineer_stats[early2].early_count += 1
        if chat in engineer_stats:
            engineer_stats[chat].chat_count += 1
        if oncall in engineer_stats:
            engineer_stats[oncall].oncall_count += 1
        if appointments in engineer_stats:
            engineer_stats[appointments].appointments_count += 1
        
        # Count work days and leave days for each engineer
        for i, engineer in enumerate(engineers):
            status_col = f"Status {i+1}"
            if status_col in row:
                status = row[status_col]
                if status == "WORK":
                    engineer_stats[engineer].total_work_days += 1
                elif status == "LEAVE":
                    engineer_stats[engineer].leave_days += 1
                
                # Count weekend work (Saturday/Sunday)
                day = row.get("Day", "")
                if day in ["Sat", "Sun"] and status == "WORK":
                    engineer_stats[engineer].weekend_count += 1
    
    # Calculate leave-adjusted max-min deltas for each role type
    # Engineers with more leave get proportional adjustment to their expected assignments
    adjusted_oncall_counts = []
    adjusted_weekend_counts = []
    adjusted_early_counts = []
    adjusted_chat_counts = []
    adjusted_appointments_counts = []
    
    for engineer in engineers:
        stats = engineer_stats[engineer]
        
        # Calculate adjustment factor based on leave impact
        # Engineers with more leave should have their assignment counts adjusted upward for fairness comparison
        leave_adjustment = 1.0 + leave_impact.get(engineer, 0.0)
        
        adjusted_oncall_counts.append(int(stats.oncall_count * leave_adjustment))
        adjusted_weekend_counts.append(int(stats.weekend_count * leave_adjustment))
        adjusted_early_counts.append(int(stats.early_count * leave_adjustment))
        adjusted_chat_counts.append(int(stats.chat_count * leave_adjustment))
        adjusted_appointments_counts.append(int(stats.appointments_count * leave_adjustment))
    
    max_min_deltas = {
        "oncall": max(adjusted_oncall_counts) - min(adjusted_oncall_counts) if adjusted_oncall_counts else 0,
        "weekend": max(adjusted_weekend_counts) - min(adjusted_weekend_counts) if adjusted_weekend_counts else 0,
        "early": max(adjusted_early_counts) - min(adjusted_early_counts) if adjusted_early_counts else 0,
        "chat": max(adjusted_chat_counts) - min(adjusted_chat_counts) if adjusted_chat_counts else 0,
        "appointments": max(adjusted_appointments_counts) - min(adjusted_appointments_counts) if adjusted_appointments_counts else 0
    }
    
    # Calculate equity score using leave-adjusted role counts
    leave_adjusted_total_counts = []
    for i, engineer in enumerate(engineers):
        adjusted_total = (adjusted_oncall_counts[i] + adjusted_weekend_counts[i] + 
                         adjusted_early_counts[i] + adjusted_chat_counts[i] + 
                         adjusted_appointments_counts[i])
        leave_adjusted_total_counts.append(adjusted_total)
    
    equity_score = calculate_gini_coefficient(leave_adjusted_total_counts)
    
    return FairnessReport(
        engineer_stats=engineer_stats,
        equity_score=equity_score,
        max_min_deltas=max_min_deltas
    )


def check_leave_coverage_adequacy(df: pd.DataFrame, engineers: List[str], 
                                 min_coverage_threshold: int = 3) -> List[str]:
    """
    Check for days with inadequate coverage due to leave and generate warnings.
    
    Args:
        df: Schedule DataFrame
        engineers: List of all engineers
        min_coverage_threshold: Minimum number of working engineers required
    
    Returns:
        List of warning messages for days with inadequate coverage
    """
    warnings = []
    
    for _, row in df.iterrows():
        date_str = row.get("Date", "")
        day = row.get("Day", "")
        
        # Count working engineers for this day
        working_count = 0
        leave_count = 0
        
        for i, engineer in enumerate(engineers):
            status_col = f"Status {i+1}"
            if status_col in row:
                status = row[status_col]
                if status == "WORK":
                    working_count += 1
                elif status == "LEAVE":
                    leave_count += 1
        
        # Check if coverage is adequate
        if working_count < min_coverage_threshold:
            warnings.append(
                f"Inadequate coverage on {date_str} ({day}): Only {working_count} engineers working, "
                f"{leave_count} on leave. Minimum required: {min_coverage_threshold}"
            )
    
    return warnings


def calculate_gini_coefficient(values: List[int]) -> float:
    """
    Calculate Gini coefficient for a list of values.
    Returns 0 for perfect equality, 1 for maximum inequality.
    """
    if not values or len(values) <= 1:
        return 0.0
    
    # Convert to numpy array and sort
    sorted_values = np.array(sorted(values))
    n = len(sorted_values)
    
    # Handle case where all values are the same
    if np.all(sorted_values == sorted_values[0]):
        return 0.0
    
    # Calculate Gini coefficient
    # Formula: G = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1) / n
    cumsum = np.cumsum(sorted_values)
    total = cumsum[-1]
    
    if total == 0:
        return 0.0
    
    # Gini coefficient calculation
    gini = (2 * np.sum((np.arange(1, n + 1) * sorted_values))) / (n * total) - (n + 1) / n
    
    return max(0.0, min(1.0, gini))  # Clamp between 0 and 1


def generate_fairness_insights(fairness_report: FairnessReport) -> List[str]:
    """
    Generate actionable insights from the fairness report with enhanced analysis.
    Provides detailed recommendations for improving fairness distribution.
    """
    insights = []
    
    # Enhanced equity score analysis with specific thresholds
    equity_score = fairness_report.equity_score
    if equity_score < 0.05:
        insights.append("🟢 Excellent: Role distribution is exceptionally equitable (Gini coefficient < 0.05)")
    elif equity_score < 0.1:
        insights.append("🟢 Very Good: Role distribution is very equitable with minimal imbalances")
    elif equity_score < 0.15:
        insights.append("🟡 Good: Role distribution is reasonably fair with minor imbalances")
    elif equity_score < 0.25:
        insights.append("🟡 Moderate: Some role distribution imbalances detected - consider adjustments")
    elif equity_score < 0.35:
        insights.append("🟠 Attention Needed: Significant role distribution imbalances detected")
    else:
        insights.append("🔴 Critical: Major fairness issues detected - immediate rebalancing recommended")
    
    insights.append(f"   Equity Score: {equity_score:.3f} (0.000 = perfect equality, 1.000 = maximum inequality)")
    
    # Enhanced role-specific analysis with actionable recommendations
    role_analysis = []
    critical_roles = []
    
    for role, delta in fairness_report.max_min_deltas.items():
        if delta > 3:  # Critical imbalance
            critical_roles.append(f"{role} ({delta} assignment difference)")
        elif delta > 1:  # Moderate imbalance
            role_analysis.append(f"{role} ({delta} difference)")
    
    if critical_roles:
        insights.append(f"🔴 Critical Imbalances: {', '.join(critical_roles)}")
        insights.append("   Recommendation: Prioritize rebalancing these roles in future schedules")
    
    if role_analysis:
        insights.append(f"🟡 Moderate Imbalances: {', '.join(role_analysis)}")
    
    # Enhanced engineer-specific analysis with detailed recommendations
    total_assignments = {}
    role_breakdowns = {}
    leave_impact_analysis = {}
    
    for name, stats in fairness_report.engineer_stats.items():
        total = (stats.oncall_count + stats.weekend_count + stats.early_count + 
                stats.chat_count + stats.appointments_count)
        total_assignments[name] = total
        
        # Detailed role breakdown for insights
        role_breakdowns[name] = {
            'oncall': stats.oncall_count,
            'weekend': stats.weekend_count, 
            'early': stats.early_count,
            'chat': stats.chat_count,
            'appointments': stats.appointments_count
        }
        
        # Leave impact analysis if available
        if hasattr(stats, 'leave_impact_factor'):
            leave_impact_analysis[name] = {
                'leave_days': getattr(stats, 'leave_days', 0),
                'impact_factor': stats.leave_impact_factor
            }
    
    if total_assignments:
        # Sort engineers by total assignments
        sorted_engineers = sorted(total_assignments.items(), key=lambda x: x[1])
        min_engineer, min_count = sorted_engineers[0]
        max_engineer, max_count = sorted_engineers[-1]
        
        assignment_range = max_count - min_count
        
        if assignment_range > 4:
            insights.append(f"🔴 High Assignment Variance: {assignment_range} assignment difference")
            insights.append(f"   Overloaded: {max_engineer} ({max_count} assignments)")
            insights.append(f"   Underutilized: {min_engineer} ({min_count} assignments)")
            
            # Provide specific rebalancing suggestions
            overloaded_roles = []
            underutilized_roles = []
            
            max_breakdown = role_breakdowns[max_engineer]
            min_breakdown = role_breakdowns[min_engineer]
            
            for role in ['oncall', 'weekend', 'early', 'chat', 'appointments']:
                if max_breakdown[role] - min_breakdown[role] > 1:
                    overloaded_roles.append(f"{role} ({max_breakdown[role]} vs {min_breakdown[role]})")
            
            if overloaded_roles:
                insights.append(f"   Suggested rebalancing: {', '.join(overloaded_roles)}")
        
        elif assignment_range > 2:
            insights.append(f"🟡 Moderate Assignment Variance: {assignment_range} assignment difference")
            insights.append(f"   Consider minor adjustments between {max_engineer} and {min_engineer}")
        
        else:
            insights.append("🟢 Good Assignment Balance: Assignment variance within acceptable range")
    
    # Leave impact insights if available
    if leave_impact_analysis:
        high_leave_engineers = [(name, data) for name, data in leave_impact_analysis.items() 
                               if data['impact_factor'] > 0.1]  # More than 10% leave
        
        if high_leave_engineers:
            insights.append("📅 Leave Impact Analysis:")
            for name, data in high_leave_engineers:
                leave_days = data['leave_days']
                impact_pct = data['impact_factor'] * 100
                insights.append(f"   {name}: {leave_days} leave days ({impact_pct:.1f}% schedule impact)")
            
            insights.append("   Note: Engineers with high leave should have proportionally fewer assignments")
    
    # Role distribution variance analysis
    role_variances = {}
    for role in ['oncall', 'weekend', 'early', 'chat', 'appointments']:
        role_counts = [role_breakdowns[eng][role] for eng in fairness_report.engineer_stats.keys()]
        if len(role_counts) > 1:
            mean_count = sum(role_counts) / len(role_counts)
            variance = sum((count - mean_count) ** 2 for count in role_counts) / len(role_counts)
            role_variances[role] = variance
    
    # Identify roles with highest variance for targeted improvement
    if role_variances:
        high_variance_roles = [(role, var) for role, var in role_variances.items() if var > 1.0]
        if high_variance_roles:
            high_variance_roles.sort(key=lambda x: x[1], reverse=True)
            top_variance_role = high_variance_roles[0]
            insights.append(f"🎯 Priority Focus: '{top_variance_role[0]}' role has highest distribution variance ({top_variance_role[1]:.2f})")
    
    # Summary recommendations
    if equity_score > 0.2:
        insights.append("💡 Recommendations:")
        insights.append("   • Use fairness-weighted assignment selection in future schedules")
        insights.append("   • Consider manual adjustments for engineers with extreme assignment counts")
        insights.append("   • Review rotation seeds to improve initial distribution")
        
        if leave_impact_analysis:
            insights.append("   • Account for leave days when calculating fair assignment targets")
    
    return insights


def make_enhanced_schedule(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], 
                          leave: pd.DataFrame, assign_early_on_weekends: bool=False) -> ScheduleResult:
    """
    Enhanced schedule generation that returns a complete ScheduleResult with metadata,
    fairness analysis, and decision logging.
    """
    # Generate the schedule with detailed decision logging
    df, decision_log, weekend_compensation_tracking = make_schedule_with_decisions(start_sunday, weeks, engineers, seeds, leave, assign_early_on_weekends)
    
    # Convert DataFrame to schedule data
    schedule_data = convert_dataframe_to_schedule_data(df)
    
    # Create metadata
    config = {
        "seeds": seeds,
        "assign_early_on_weekends": assign_early_on_weekends,
        "leave_entries": len(leave) if leave is not None and not leave.empty else 0
    }
    metadata = create_basic_metadata(engineers, weeks, start_sunday, config)
    
    # Process leave data for enhanced fairness calculation
    leave_map = process_leave_with_enhanced_logic(leave.to_dict('records') if leave is not None and not leave.empty else [], engineers)
    
    # Calculate enhanced fairness report with leave impact analysis
    fairness_report = calculate_enhanced_fairness_report(df, engineers, leave_map)
    
    # Check for leave coverage adequacy and add warnings to decision log
    coverage_warnings = check_leave_coverage_adequacy(df, engineers)
    if coverage_warnings:
        for warning in coverage_warnings:
            decision_log.append(DecisionEntry(
                date="schedule_analysis",
                decision_type="leave_coverage_warning",
                affected_engineers=[],
                reason=warning,
                alternatives_considered=["Adjust leave schedules", "Add emergency coverage", "Manual intervention required"]
            ))
    
    # Run invariant checks on the generated schedule
    invariant_checker = ScheduleInvariantChecker(engineers)
    violations = invariant_checker.check_all_invariants(df)
    
    # Check fairness distribution violations (skip for now due to serialization issues)
    # fairness_violations = invariant_checker.check_fairness_distribution(asdict(fairness_report))
    # violations.extend(fairness_violations)
    
    # Log any invariant violations
    if violations:
        violation_summary = invariant_checker.get_violation_summary()
        logger.log_invariant_violation(
            request_id="schedule_generation",  # This will be overridden by the API layer
            violation_type="multiple_violations",
            details=violation_summary
        )
        
        # Add critical violations to decision log
        for violation in violations:
            if violation.severity == "error":
                decision_log.append(DecisionEntry(
                    date=start_sunday.isoformat(),
                    decision_type="invariant_violation",
                    affected_engineers=violation.affected_engineers or [],
                    reason=f"Invariant violation: {violation.message}",
                    alternatives_considered=[str(violation.details)]
                ))
    
    # Generate comprehensive fairness insights
    insights = generate_fairness_insights(fairness_report)
    
    # Add fairness insights to decision log for backward compatibility
    if insights:
        decision_log.append(DecisionEntry(
            date=start_sunday.isoformat(),
            decision_type="fairness_analysis",
            affected_engineers=engineers,
            reason="Fairness analysis completed",
            alternatives_considered=insights
        ))
    
    # Create initial schedule result with enhanced fairness insights
    initial_result = ScheduleResult(
        schedule_data=schedule_data,
        fairness_report=fairness_report,
        decision_log=decision_log,
        metadata=metadata,
        weekend_compensation_tracking=weekend_compensation_tracking,
        fairness_insights=insights,
        schema_version="2.0"
    )
    
    # Apply enhanced display formatting
    enhanced_result = enhance_schedule_display(initial_result)
    
    return enhanced_result
