from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd

from models import ScheduleResult, FairnessReport, DecisionEntry, ScheduleMetadata, EngineerStats
from export_manager import ExportManager, convert_dataframe_to_schedule_data, create_basic_fairness_report, create_basic_metadata
from lib.invariant_checker import ScheduleInvariantChecker
from lib.logging_utils import logger
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

def weekend_worker_for_week(engineers_rotated: List[str], week_idx: int) -> str:
    n = len(engineers_rotated)
    return engineers_rotated[week_idx % n]

def works_today(engineer: str, d: date, start_sunday: date, weekend_seeded: List[str]) -> bool:
    w = week_index(start_sunday, d)
    dow = d.weekday()  # Mon=0..Sun=6
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

def find_backfill_candidates(engineers: List[str], leave_today: set, expected_working: List[str], 
                            d: date, start_sunday: date, weekend_seeded: List[str]) -> List[str]:
    """
    Find engineers who could serve as backfill when regular engineers are on leave.
    """
    # Engineers not on leave
    available = [e for e in engineers if e not in leave_today]
    
    # Engineers who normally wouldn't work today but could backfill
    backfill_candidates = [e for e in available if e not in expected_working]
    
    return backfill_candidates


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


def generate_day_assignments(d: date, engineers: List[str], start_sunday: date, weekend_seeded: List[str],
                             leave_map: Dict[str,set], seeds: Dict[str,int],
                             assign_early_on_weekends: bool=False, decision_log: List[DecisionEntry] = None):
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
    
    Returns:
        Tuple of (working_engineers, engineers_on_leave, role_assignments)
    """
    if decision_log is None:
        decision_log = []
    
    date_str = d.isoformat()
    
    # Determine who should be working based on weekend rotation
    expected_working = [e for e in engineers if works_today(e, d, start_sunday, weekend_seeded)]
    leave_today = set([e for e, days in leave_map.items() if d in days])
    
    # Find backfill candidates
    backfill_candidates = find_backfill_candidates(engineers, leave_today, expected_working, d, start_sunday, weekend_seeded)
    
    # Log leave exclusions with backfill options
    if leave_today:
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="leave_exclusion",
            affected_engineers=list(leave_today),
            reason=f"Engineers excluded due to scheduled leave on {d.strftime('%A, %B %d')}",
            alternatives_considered=backfill_candidates[:3] if backfill_candidates else ["No backfill available"]
        ))
    
    # Initial working list after leave exclusions
    working = [e for e in expected_working if e not in leave_today]
    
    # Intelligent backfill logic
    min_required = 3 if is_weekday(d) else 1  # Weekdays need Chat, OnCall, Appointments
    if len(working) < min_required and backfill_candidates:
        # Add backfill engineers to meet minimum requirements
        needed = min_required - len(working)
        backfill_added = backfill_candidates[:needed]
        working.extend(backfill_added)
        
        decision_log.append(DecisionEntry(
            date=date_str,
            decision_type="backfill_assignment",
            affected_engineers=backfill_added,
            reason=f"Added {len(backfill_added)} backfill engineer(s) to meet minimum coverage of {min_required}",
            alternatives_considered=backfill_candidates[needed:needed+2] if len(backfill_candidates) > needed else []
        ))
    
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

    # Assign Early shifts
    if is_weekday(d) or assign_early_on_weekends:
        if working:
            day_idx = (d - start_sunday).days
            order = sorted(working, key=lambda name: ((engineers.index(name) + seeds.get("early",0) + day_idx) % len(engineers)))
            
            early_assignments = []
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
                    decision_type="early_shift_assignment",
                    affected_engineers=early_assignments,
                    reason=f"Early shift rotation (seed={seeds.get('early',0)}, day_offset={day_idx})",
                    alternatives_considered=alternatives
                ))

    # Assign weekday roles (Chat, OnCall, Appointments)
    if is_weekday(d):
        day_idx = (d - start_sunday).days
        available = working.copy()
        
        # Chat assignment
        if available:
            chat_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("chat",0) + day_idx) % len(engineers)))
            roles["Chat"] = chat_order[0]
            available.remove(roles["Chat"])
            
            alternatives = chat_order[1:3] if len(chat_order) > 1 else []
            decision_log.append(DecisionEntry(
                date=date_str,
                decision_type="chat_assignment",
                affected_engineers=[roles["Chat"]],
                reason=f"Chat rotation (seed={seeds.get('chat',0)}, day_offset={day_idx})",
                alternatives_considered=alternatives
            ))
        
        # OnCall assignment (avoid weekend workers if possible)
        if available:
            oncall_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("oncall",0) + day_idx) % len(engineers)))
            
            # Prefer engineers who don't work weekends for OnCall
            weekend_workers = [weekend_worker_for_week(weekend_seeded, week_index(start_sunday, d))]
            if d.weekday() == 4:  # Friday - also avoid next week's weekend worker
                weekend_workers.append(weekend_worker_for_week(weekend_seeded, week_index(start_sunday, d) + 1))
            
            non_weekend_oncall = [e for e in oncall_order if e not in weekend_workers]
            if non_weekend_oncall:
                roles["OnCall"] = non_weekend_oncall[0]
                reason = f"OnCall rotation (seed={seeds.get('oncall',0)}, day_offset={day_idx}) - avoided weekend workers"
                alternatives = non_weekend_oncall[1:3] if len(non_weekend_oncall) > 1 else oncall_order[:2]
            else:
                roles["OnCall"] = oncall_order[0]
                reason = f"OnCall rotation (seed={seeds.get('oncall',0)}, day_offset={day_idx}) - no non-weekend options"
                alternatives = oncall_order[1:3] if len(oncall_order) > 1 else []
            
            available.remove(roles["OnCall"])
            
            decision_log.append(DecisionEntry(
                date=date_str,
                decision_type="oncall_assignment",
                affected_engineers=[roles["OnCall"]],
                reason=reason,
                alternatives_considered=alternatives
            ))
        
        # Appointments assignment
        if available:
            appt_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("appointments",0) + day_idx) % len(engineers)))
            roles["Appointments"] = appt_order[0]
            
            alternatives = appt_order[1:3] if len(appt_order) > 1 else []
            decision_log.append(DecisionEntry(
                date=date_str,
                decision_type="appointments_assignment",
                affected_engineers=[roles["Appointments"]],
                reason=f"Appointments rotation (seed={seeds.get('appointments',0)}, day_offset={day_idx})",
                alternatives_considered=alternatives
            ))
    
    # Validate for conflicts and generate suggestions
    conflicts = validate_scheduling_conflicts(roles, working, d)
    if conflicts:
        suggestions = generate_alternative_suggestions(roles, working, backfill_candidates, conflicts)
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

    leave_map = {}
    if leave is not None and not leave.empty:
        leave = leave.copy()
        leave["Date"] = pd.to_datetime(leave["Date"]).dt.date
        for e in leave["Engineer"].unique():
            leave_map[e] = set(leave.loc[leave["Engineer"]==e, "Date"].tolist())
    for e in engineers:
        leave_map.setdefault(e, set())

    days = weeks * 7
    dates = [start_sunday + pd.Timedelta(days=i) for i in range(days)]
    dates = [d.date() for d in dates]

    columns = ["Date","Day","WeekIndex","Early1","Early2","Chat","OnCall","Appointments"]
    for i in range(6):
        columns += [f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"]

    rows = []
    for d in dates:
        w = week_index(start_sunday, d)
        dow = pd.Timestamp(d).strftime("%a")
        working, leave_today, roles = generate_day_assignments(d, engineers, start_sunday, weekend_seeded, leave_map, seeds, assign_early_on_weekends)
        eng_cells = []
        for e in engineers:
            status = "LEAVE" if e in leave_today else ("WORK" if works_today(e, d, start_sunday, weekend_seeded) else "OFF")
            shift = ""
            if status == "WORK":
                if e in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    shift = "08:00-17:00" if pd.Timestamp(d).weekday() < 5 else "Weekend"
            eng_cells += [e, status, shift]
        row = [d, dow, w, roles["Early1"], roles["Early2"], roles["Chat"], roles["OnCall"], roles["Appointments"]] + eng_cells
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns)
    return df


def make_schedule_with_decisions(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], 
                                leave: pd.DataFrame, assign_early_on_weekends: bool=False) -> Tuple[pd.DataFrame, List[DecisionEntry]]:
    """
    Generate schedule with detailed decision logging.
    
    Returns:
        Tuple of (schedule_dataframe, decision_log)
    """
    assert len(engineers) == 6, "Exactly 6 engineers are required."
    
    decision_log = []
    
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
    dates = [start_sunday + pd.Timedelta(days=i) for i in range(days)]
    dates = [d.date() for d in dates]

    columns = ["Date","Day","WeekIndex","Early1","Early2","Chat","OnCall","Appointments"]
    for i in range(6):
        columns += [f"{i+1}) Engineer", f"Status {i+1}", f"Shift {i+1}"]

    rows = []
    for d in dates:
        w = week_index(start_sunday, d)
        dow = pd.Timestamp(d).strftime("%a")
        working, leave_today, roles = generate_day_assignments(
            d, engineers, start_sunday, weekend_seeded, leave_map, seeds, 
            assign_early_on_weekends, decision_log
        )
        
        eng_cells = []
        for e in engineers:
            status = "LEAVE" if e in leave_today else ("WORK" if works_today(e, d, start_sunday, weekend_seeded) else "OFF")
            shift = ""
            if status == "WORK":
                if e in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    shift = "08:00-17:00" if pd.Timestamp(d).weekday() < 5 else "Weekend"
            eng_cells += [e, status, shift]
        row = [d, dow, w, roles["Early1"], roles["Early2"], roles["Chat"], roles["OnCall"], roles["Appointments"]] + eng_cells
        rows.append(row)
    
    df = pd.DataFrame(rows, columns=columns)
    return df, decision_log


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
    Generate actionable insights from the fairness report.
    """
    insights = []
    
    # Analyze equity score
    if fairness_report.equity_score < 0.1:
        insights.append("Excellent: Role distribution is very equitable across all engineers.")
    elif fairness_report.equity_score < 0.2:
        insights.append("Good: Role distribution is reasonably fair with minor imbalances.")
    elif fairness_report.equity_score < 0.3:
        insights.append("Moderate: Some role distribution imbalances detected.")
    else:
        insights.append("Attention needed: Significant role distribution imbalances detected.")
    
    # Analyze max-min deltas
    high_delta_roles = []
    for role, delta in fairness_report.max_min_deltas.items():
        if delta > 2:  # More than 2 assignment difference
            high_delta_roles.append(f"{role} ({delta} difference)")
    
    if high_delta_roles:
        insights.append(f"High variation in: {', '.join(high_delta_roles)}")
    
    # Find engineers with highest and lowest total assignments
    total_assignments = {}
    for name, stats in fairness_report.engineer_stats.items():
        total = (stats.oncall_count + stats.weekend_count + stats.early_count + 
                stats.chat_count + stats.appointments_count)
        total_assignments[name] = total
    
    if total_assignments:
        max_engineer = max(total_assignments, key=total_assignments.get)
        min_engineer = min(total_assignments, key=total_assignments.get)
        max_count = total_assignments[max_engineer]
        min_count = total_assignments[min_engineer]
        
        if max_count - min_count > 3:
            insights.append(f"Consider balancing: {max_engineer} has {max_count} assignments vs {min_engineer} with {min_count}")
    
    return insights


def make_enhanced_schedule(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], 
                          leave: pd.DataFrame, assign_early_on_weekends: bool=False) -> ScheduleResult:
    """
    Enhanced schedule generation that returns a complete ScheduleResult with metadata,
    fairness analysis, and decision logging.
    """
    # Generate the schedule with detailed decision logging
    df, decision_log = make_schedule_with_decisions(start_sunday, weeks, engineers, seeds, leave, assign_early_on_weekends)
    
    # Convert DataFrame to schedule data
    schedule_data = convert_dataframe_to_schedule_data(df)
    
    # Create metadata
    config = {
        "seeds": seeds,
        "assign_early_on_weekends": assign_early_on_weekends,
        "leave_entries": len(leave) if leave is not None and not leave.empty else 0
    }
    metadata = create_basic_metadata(engineers, weeks, start_sunday, config)
    
    # Calculate comprehensive fairness report
    fairness_report = calculate_fairness_report(df, engineers)
    
    # Run invariant checks on the generated schedule
    invariant_checker = ScheduleInvariantChecker(engineers)
    violations = invariant_checker.check_all_invariants(df)
    
    # Check fairness distribution violations
    fairness_violations = invariant_checker.check_fairness_distribution(fairness_report.dict())
    violations.extend(fairness_violations)
    
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
    
    # Add fairness insights to decision log
    insights = generate_fairness_insights(fairness_report)
    if insights:
        decision_log.append(DecisionEntry(
            date=start_sunday.isoformat(),
            decision_type="fairness_analysis",
            affected_engineers=engineers,
            reason="Fairness analysis completed",
            alternatives_considered=insights
        ))
    
    return ScheduleResult(
        schedule_data=schedule_data,
        fairness_report=fairness_report,
        decision_log=decision_log,
        metadata=metadata,
        schema_version="2.0"
    )
