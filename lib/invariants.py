"""
Schedule invariants that must always hold
"""
from datetime import date, timedelta
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter

class ScheduleInvariantError(Exception):
    """Raised when a schedule violates an invariant"""
    pass

def verify_schedule_invariants(schedule_data: List[Dict], engineers: List[str], 
                             start_sunday: date, weeks: int, leave_map: Dict[str, Set[date]]) -> List[str]:
    """
    Verify all schedule invariants and return list of violations
    """
    violations = []
    
    # Group schedule by week and date
    schedule_by_date = {row['Date']: row for row in schedule_data}
    schedule_by_week = defaultdict(list)
    
    for row in schedule_data:
        week_idx = row['WeekIndex']
        schedule_by_week[week_idx].append(row)
    
    # Invariant 1: Exactly one on-call per week
    violations.extend(_verify_oncall_invariants(schedule_by_week, weeks))
    
    # Invariant 2: On-call never scheduled on weekend during their week
    violations.extend(_verify_oncall_weekend_exclusion(schedule_data, start_sunday))
    
    # Invariant 3: No engineer double-booked per day
    violations.extend(_verify_no_double_booking(schedule_data, engineers))
    
    # Invariant 4: Leave excludes all assignments
    violations.extend(_verify_leave_exclusions(schedule_data, leave_map))
    
    # Invariant 5: Weekly rotations are fair (within 1 assignment difference)
    violations.extend(_verify_rotation_fairness(schedule_data, engineers, weeks))
    
    # Invariant 6: Date continuity and correctness
    violations.extend(_verify_date_continuity(schedule_data, start_sunday, weeks))
    
    return violations

def _verify_oncall_invariants(schedule_by_week: Dict[int, List[Dict]], weeks: int) -> List[str]:
    """Verify exactly one on-call per week"""
    violations = []
    
    for week_idx in range(weeks):
        if week_idx not in schedule_by_week:
            violations.append(f"Missing week {week_idx} in schedule")
            continue
            
        week_schedule = schedule_by_week[week_idx]
        weekday_schedule = [row for row in week_schedule if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']]
        
        if not weekday_schedule:
            continue  # No weekdays in this week (shouldn't happen)
            
        # Get all on-call assignments for this week
        oncall_engineers = set()
        for row in weekday_schedule:
            if row['OnCall']:
                oncall_engineers.add(row['OnCall'])
        
        if len(oncall_engineers) == 0:
            violations.append(f"Week {week_idx}: No on-call engineer assigned")
        elif len(oncall_engineers) > 1:
            violations.append(f"Week {week_idx}: Multiple on-call engineers: {oncall_engineers}")
    
    return violations

def _verify_oncall_weekend_exclusion(schedule_data: List[Dict], start_sunday: date) -> List[str]:
    """Verify on-call engineers don't work weekends during their week"""
    violations = []
    
    # Group by week and find on-call engineers
    week_oncall = {}
    for row in schedule_data:
        week_idx = row['WeekIndex']
        if row['OnCall'] and row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
            week_oncall[week_idx] = row['OnCall']
    
    # Check weekend assignments
    for row in schedule_data:
        if row['Day'] in ['Sat', 'Sun']:
            week_idx = row['WeekIndex']
            oncall_engineer = week_oncall.get(week_idx)
            
            if oncall_engineer:
                # Check if on-call engineer is working this weekend
                for i, engineer in enumerate([row.get(f'{j+1}) Engineer', '') for j in range(6)]):
                    status = row.get(f'Status {i+1}', '')
                    if engineer == oncall_engineer and status == 'WORK':
                        violations.append(f"Week {week_idx}: On-call engineer {oncall_engineer} working weekend on {row['Date']}")
    
    return violations

def _verify_no_double_booking(schedule_data: List[Dict], engineers: List[str]) -> List[str]:
    """Verify no engineer is assigned to multiple roles on the same day"""
    violations = []
    
    for row in schedule_data:
        if row['Day'] not in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
            continue  # Skip weekends
            
        # Count role assignments per engineer
        engineer_roles = defaultdict(list)
        
        roles = ['OnCall', 'Contacts', 'Appointments', 'Early1', 'Early2']
        for role in roles:
            engineer = row.get(role, '')
            if engineer:
                engineer_roles[engineer].append(role)
        
        # Check tickets assignment
        tickets_engineers = row.get('Tickets', '').split(', ') if row.get('Tickets') else []
        for engineer in tickets_engineers:
            if engineer.strip():
                engineer_roles[engineer.strip()].append('Tickets')
        
        # Find double bookings
        for engineer, assigned_roles in engineer_roles.items():
            if len(assigned_roles) > 1:
                violations.append(f"{row['Date']}: Engineer {engineer} assigned to multiple roles: {assigned_roles}")
    
    return violations

def _verify_leave_exclusions(schedule_data: List[Dict], leave_map: Dict[str, Set[date]]) -> List[str]:
    """Verify engineers on leave are not assigned to any roles"""
    violations = []
    
    for row in schedule_data:
        row_date = date.fromisoformat(row['Date'])
        
        # Find engineers on leave this day
        engineers_on_leave = set()
        for engineer, leave_dates in leave_map.items():
            if row_date in leave_dates:
                engineers_on_leave.add(engineer)
        
        if not engineers_on_leave:
            continue
            
        # Check role assignments
        roles = ['OnCall', 'Contacts', 'Appointments', 'Early1', 'Early2']
        for role in roles:
            engineer = row.get(role, '')
            if engineer in engineers_on_leave:
                violations.append(f"{row['Date']}: Engineer {engineer} on leave but assigned to {role}")
        
        # Check tickets assignment
        tickets_engineers = row.get('Tickets', '').split(', ') if row.get('Tickets') else []
        for engineer in tickets_engineers:
            if engineer.strip() in engineers_on_leave:
                violations.append(f"{row['Date']}: Engineer {engineer} on leave but assigned to Tickets")
    
    return violations

def _verify_rotation_fairness(schedule_data: List[Dict], engineers: List[str], weeks: int) -> List[str]:
    """Verify rotations are fair (max-min delta <= 1 per role)"""
    violations = []
    
    # Count assignments per engineer per role
    role_counts = {
        'OnCall': Counter(),
        'Contacts': Counter(),
        'Appointments': Counter(),
        'Early1': Counter(),
        'Early2': Counter(),
        'Weekend': Counter()
    }
    
    for row in schedule_data:
        # Count weekday roles
        if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
            for role in ['OnCall', 'Contacts', 'Appointments', 'Early1', 'Early2']:
                engineer = row.get(role, '')
                if engineer:
                    role_counts[role][engineer] += 1
        
        # Count weekend work
        elif row['Day'] in ['Sat', 'Sun']:
            for i in range(6):
                engineer = row.get(f'{i+1}) Engineer', '')
                status = row.get(f'Status {i+1}', '')
                if engineer and status == 'WORK':
                    role_counts['Weekend'][engineer] += 1
    
    # Check fairness for each role
    for role, counts in role_counts.items():
        if not counts:
            continue
            
        min_count = min(counts.values()) if counts else 0
        max_count = max(counts.values()) if counts else 0
        
        # For engineers not assigned to this role, count is 0
        for engineer in engineers:
            if engineer not in counts:
                min_count = 0
        
        if max_count - min_count > 1:
            violations.append(f"Role {role}: Unfair distribution (min={min_count}, max={max_count})")
    
    return violations

def _verify_date_continuity(schedule_data: List[Dict], start_sunday: date, weeks: int) -> List[str]:
    """Verify dates are continuous and correct"""
    violations = []
    
    expected_dates = []
    for i in range(weeks * 7):
        expected_dates.append(start_sunday + timedelta(days=i))
    
    actual_dates = [date.fromisoformat(row['Date']) for row in schedule_data]
    
    if len(actual_dates) != len(expected_dates):
        violations.append(f"Expected {len(expected_dates)} days, got {len(actual_dates)}")
        return violations
    
    for i, (expected, actual) in enumerate(zip(expected_dates, actual_dates)):
        if expected != actual:
            violations.append(f"Date mismatch at position {i}: expected {expected}, got {actual}")
    
    return violations

def assert_schedule_invariants(schedule_data: List[Dict], engineers: List[str], 
                             start_sunday: date, weeks: int, leave_map: Dict[str, Set[date]]):
    """Assert all invariants hold, raise exception if any violations"""
    violations = verify_schedule_invariants(schedule_data, engineers, start_sunday, weeks, leave_map)
    
    if violations:
        violation_text = '\n'.join(f"- {v}" for v in violations)
        raise ScheduleInvariantError(f"Schedule invariant violations:\n{violation_text}")