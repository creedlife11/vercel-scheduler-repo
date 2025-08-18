from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, date, timedelta
from typing import List, Dict
import uuid

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        request_id = str(uuid.uuid4())
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_response(400, "Request body is required", request_id)
                return
            
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Basic validation - support 5-8 engineers
            engineers = data.get('engineers', [])
            if len(engineers) < 5 or len(engineers) > 8:
                self.send_error_response(400, f"Team size must be 5-8 engineers, got {len(engineers)}", request_id)
                return
            
            start_sunday_str = data.get('start_sunday', '')
            if not start_sunday_str:
                self.send_error_response(400, "start_sunday is required", request_id)
                return
            
            try:
                start_sunday = datetime.strptime(start_sunday_str, '%Y-%m-%d').date()
            except ValueError:
                self.send_error_response(400, "Invalid date format. Use YYYY-MM-DD", request_id)
                return
            
            weeks = data.get('weeks', 8)
            if not isinstance(weeks, int) or weeks < 1 or weeks > 52:
                self.send_error_response(400, "weeks must be between 1 and 52", request_id)
                return
            
            seeds = data.get('seeds', {})
            leave_data = data.get('leave', [])
            format_type = data.get('format', 'csv')
            include_fairness = data.get('include_fairness', False)
            
            # Generate schedule
            result = make_schedule_simple(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave_data=leave_data
            )
            
            schedule_data = result['schedule']
            metadata = result['metadata']
            
            # Handle different output formats
            if format_type.lower() == 'json':
                # JSON response with full metadata
                response_data = {
                    'schedule': schedule_data,
                    'metadata': {
                        **metadata,
                        'generated_at': datetime.utcnow().isoformat(),
                        'request_id': request_id,
                        'input_summary': {
                            'engineers': len(engineers),
                            'weeks': weeks,
                            'leave_entries': len(leave_data),
                            'start_date': start_sunday.isoformat()
                        }
                    }
                }
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.send_header('X-Request-ID', request_id)
                self.end_headers()
                self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))
                
            else:
                # CSV format (default)
                csv_lines = []
                if schedule_data:
                    csv_lines.append(','.join(schedule_data[0].keys()))
                    for row in schedule_data:
                        csv_lines.append(','.join(str(v) for v in row.values()))
                    
                    # Add warnings as comments at the end
                    if metadata['warnings']:
                        csv_lines.append('')
                        csv_lines.append('# Warnings:')
                        for warning in metadata['warnings']:
                            csv_lines.append(f'# {warning}')
                    
                    # Add fairness summary
                    if include_fairness and metadata.get('fairness'):
                        csv_lines.append('')
                        csv_lines.append('# Fairness Summary:')
                        for role, metrics in metadata['fairness'].items():
                            csv_lines.append(f'# {role}: {metrics["badge"]} (delta: {metrics["delta"]}, gini: {metrics["gini"]})')
                
                csv_content = '\n'.join(csv_lines)
                
                # Generate smart filename
                filename = f"schedule_{start_sunday.strftime('%Y-%m-%d')}_{weeks}w_{len(engineers)}eng.csv"
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'text/csv')
                self.send_header('Content-Disposition', f'attachment; filename={filename}')
                self.send_header('X-Request-ID', request_id)
                self.end_headers()
                self.wfile.write(csv_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error_response(500, f"Internal error: {str(e)}", request_id)
    
    def send_error_response(self, status_code: int, message: str, request_id: str):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_data = {
            'error': message,
            'requestId': request_id
        }
        
        self.wfile.write(json.dumps(error_data).encode())

# Scheduling functions
def build_rotation(engineers: List[str], seed: int = 0) -> List[str]:
    """Build rotation starting from seed position"""
    seed = seed % len(engineers)
    return engineers[seed:] + engineers[:seed]

def is_weekday(d: date) -> bool:
    """Check if date is a weekday (Mon-Fri)"""
    return d.weekday() < 5

def week_index(start_sunday: date, d: date) -> int:
    """Get week index from start date"""
    return (d - start_sunday).days // 7

def weekend_worker_for_week(engineers_rotated: List[str], week_idx: int) -> str:
    """Get weekend worker for given week"""
    n = len(engineers_rotated)
    return engineers_rotated[week_idx % n]

def works_today(engineer: str, d: date, start_sunday: date, weekend_seeded: List[str]) -> bool:
    """Check if engineer works on given date"""
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

def get_oncall_engineer_for_week(engineers: List[str], week_idx: int, weekend_seeded: List[str], seeds: Dict[str,int]) -> str:
    """Get on-call engineer for the week, ensuring they don't work weekend that week"""
    oncall_rotation = build_rotation(engineers, seeds.get("oncall", 0))
    weekend_worker = weekend_worker_for_week(weekend_seeded, week_idx)
    
    # Find an engineer who is not the weekend worker for this week
    for i in range(len(oncall_rotation)):
        candidate = oncall_rotation[(week_idx + i) % len(oncall_rotation)]
        if candidate != weekend_worker:
            return candidate
    
    # Fallback if all engineers are weekend workers (shouldn't happen with 6 engineers)
    return oncall_rotation[week_idx % len(oncall_rotation)]

def get_early2_engineer_for_week(engineers: List[str], week_idx: int, weekend_seeded: List[str], oncall_engineer: str, seeds: Dict[str,int]) -> str:
    """Get second early shift engineer for the week"""
    early_rotation = build_rotation(engineers, seeds.get("early", 0))
    weekend_worker = weekend_worker_for_week(weekend_seeded, week_idx)
    
    # Find an engineer who is not the weekend worker and not the on-call engineer
    for i in range(len(early_rotation)):
        candidate = early_rotation[(week_idx + i) % len(early_rotation)]
        if candidate != weekend_worker and candidate != oncall_engineer:
            return candidate
    
    # Fallback - find any engineer who isn't on-call
    for engineer in early_rotation:
        if engineer != oncall_engineer:
            return engineer
    
    # Final fallback
    return early_rotation[week_idx % len(early_rotation)]

def compute_role_assignments(team_size: int) -> Dict[str, int]:
    """Compute role counts based on team size"""
    if team_size <= 5:
        return {
            'oncall': 1,
            'early_shifts': 1,  # Only Early1, no Early2
            'contacts': 1,
            'appointments': 1,
            'min_tickets': max(1, team_size - 4)
        }
    elif team_size == 6:
        return {
            'oncall': 1,
            'early_shifts': 2,  # Early1 + Early2
            'contacts': 1,
            'appointments': 1,
            'min_tickets': 2
        }
    else:  # 7-8 engineers
        return {
            'oncall': 1,
            'early_shifts': 2,
            'contacts': 1,
            'appointments': 1,
            'min_tickets': team_size - 5
        }

def generate_warnings(team_size: int, role_config: Dict[str, int]) -> List[str]:
    """Generate warnings about staffing levels"""
    warnings = []
    
    if team_size <= 5:
        warnings.append(f"Team size ({team_size}) is below optimal. Consider adding more engineers for better coverage.")
        warnings.append("Early shift coverage reduced to single engineer due to limited staff.")
    
    if role_config['min_tickets'] < 2:
        warnings.append("Limited ticket coverage - consider redistributing roles during high-demand periods.")
    
    return warnings

def calculate_fairness_metrics(schedule_data: List[Dict], engineers: List[str]) -> Dict:
    """Calculate fairness metrics for the schedule"""
    from collections import Counter
    import math
    
    # Count assignments per engineer per role
    role_counts = {
        'oncall_days': Counter(),
        'early_shifts': Counter(),
        'contacts_days': Counter(),
        'appointments_days': Counter(),
        'weekend_days': Counter(),
        'tickets_days': Counter()
    }
    
    for row in schedule_data:
        # Count weekday roles
        if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
            if row['OnCall']:
                role_counts['oncall_days'][row['OnCall']] += 1
            if row['Early1']:
                role_counts['early_shifts'][row['Early1']] += 1
            if row['Early2']:
                role_counts['early_shifts'][row['Early2']] += 1
            if row['Contacts']:
                role_counts['contacts_days'][row['Contacts']] += 1
            if row['Appointments']:
                role_counts['appointments_days'][row['Appointments']] += 1
            
            # Count tickets
            tickets_engineers = row.get('Tickets', '').split(', ') if row.get('Tickets') else []
            for engineer in tickets_engineers:
                if engineer.strip():
                    role_counts['tickets_days'][engineer.strip()] += 1
        
        # Count weekend work
        elif row['Day'] in ['Sat', 'Sun']:
            for i in range(len(engineers)):
                engineer = row.get(f'{i+1}) Engineer', '')
                status = row.get(f'Status {i+1}', '')
                if engineer and status == 'WORK':
                    role_counts['weekend_days'][engineer] += 1
    
    # Calculate metrics for each role
    fairness_report = {}
    
    for role, counts in role_counts.items():
        if not counts:
            continue
            
        # Ensure all engineers are represented
        for engineer in engineers:
            if engineer not in counts:
                counts[engineer] = 0
        
        values = list(counts.values())
        min_count = min(values)
        max_count = max(values)
        mean_count = sum(values) / len(values)
        
        # Calculate Gini coefficient
        n = len(values)
        if n > 1 and sum(values) > 0:
            sorted_values = sorted(values)
            cumsum = sum((i + 1) * val for i, val in enumerate(sorted_values))
            gini = (2 * cumsum) / (n * sum(values)) - (n + 1) / n
        else:
            gini = 0
        
        # Determine fairness badge
        delta = max_count - min_count
        if delta <= 1:
            badge = 'green'
        elif delta <= 2:
            badge = 'yellow'
        else:
            badge = 'red'
        
        fairness_report[role] = {
            'counts': dict(counts),
            'min': min_count,
            'max': max_count,
            'mean': round(mean_count, 1),
            'delta': delta,
            'gini': round(gini, 3),
            'badge': badge
        }
    
    return fairness_report

def make_schedule_simple(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], leave_data: List[Dict]) -> Dict:
    """Generate schedule with variable team sizes and warnings"""
    
    team_size = len(engineers)
    role_config = compute_role_assignments(team_size)
    warnings = generate_warnings(team_size, role_config)
    
    weekend_seeded = build_rotation(engineers, seeds.get("weekend", 0))
    
    # Process leave data
    leave_map = {}
    for engineer in engineers:
        leave_map[engineer] = set()
    
    for leave_entry in leave_data:
        engineer = leave_entry.get('Engineer', '')
        date_str = leave_entry.get('Date', '')
        if engineer and date_str:
            try:
                leave_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if engineer in leave_map:
                    leave_map[engineer].add(leave_date)
            except ValueError:
                continue
    
    # Pre-calculate weekly assignments
    weekly_oncall = {}
    weekly_early2 = {}
    for w in range(weeks):
        oncall_eng = get_oncall_engineer_for_week(engineers, w, weekend_seeded, seeds)
        weekly_oncall[w] = oncall_eng
        weekly_early2[w] = get_early2_engineer_for_week(engineers, w, weekend_seeded, oncall_eng, seeds)
    
    # Generate schedule
    schedule_rows = []
    days = weeks * 7
    
    for i in range(days):
        current_date = start_sunday + timedelta(days=i)
        w = week_index(start_sunday, current_date)
        dow = current_date.strftime("%a")
        
        # Find who's working today
        working = [e for e in engineers if works_today(e, current_date, start_sunday, weekend_seeded)]
        leave_today = set([e for e, days in leave_map.items() if current_date in days])
        working = [e for e in working if e not in leave_today]
        
        # Initialize roles
        roles = {
            "OnCall": "",
            "Contacts": "", 
            "Appointments": "",
            "Early1": "",
            "Early2": "",
            "Tickets": []
        }
        
        # Weekday role assignments
        if is_weekday(current_date):
            day_idx = (current_date - start_sunday).days
            available = working.copy()
            
            # 1. On-call engineer (weekly assignment)
            week_oncall = weekly_oncall.get(w, "")
            if week_oncall in available:
                roles["OnCall"] = week_oncall
                roles["Early1"] = week_oncall  # On-call engineer is always Early1
                available.remove(week_oncall)
            
            # 2. Second early shift engineer (weekly assignment) - only if team size allows
            if role_config['early_shifts'] > 1:
                week_early2 = weekly_early2.get(w, "")
                if week_early2 in available:
                    roles["Early2"] = week_early2
                    available.remove(week_early2)
            
            # 3. Contacts (rotating daily)
            if available:
                contacts_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("contacts", 0) + day_idx) % len(engineers)))
                roles["Contacts"] = contacts_order[0]
                available.remove(roles["Contacts"])
            
            # 4. Appointments (rotating daily)
            if available:
                appt_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("appointments", 0) + day_idx) % len(engineers)))
                roles["Appointments"] = appt_order[0]
                available.remove(roles["Appointments"])
            
            # 5. Remaining engineers work on tickets
            roles["Tickets"] = available
        
        # Build row
        row = {
            "Date": current_date.strftime('%Y-%m-%d'),
            "Day": dow,
            "WeekIndex": w,
            "OnCall": roles["OnCall"],
            "Contacts": roles["Contacts"],
            "Appointments": roles["Appointments"],
            "Early1": roles["Early1"],
            "Early2": roles["Early2"],
            "Tickets": ", ".join(roles["Tickets"])
        }
        
        # Add engineer status columns with detailed assignments
        for i, engineer in enumerate(engineers):
            status = "LEAVE" if engineer in leave_today else ("WORK" if works_today(engineer, current_date, start_sunday, weekend_seeded) else "OFF")
            
            # Determine specific assignment
            assignment = ""
            shift = ""
            
            if status == "WORK":
                if engineer == roles["OnCall"]:
                    assignment = "On-Call"
                    shift = "06:45-15:45"  # On-call always works early shift
                elif engineer == roles["Contacts"]:
                    assignment = "Contacts"
                    shift = "08:00-17:00"
                elif engineer == roles["Appointments"]:
                    assignment = "Appointments"
                    shift = "08:00-17:00"
                elif engineer == roles["Early1"]:
                    assignment = "On-Call (Early)"  # This should be the same as OnCall
                    shift = "06:45-15:45"
                elif engineer == roles["Early2"]:
                    assignment = "Tickets (Early)"
                    shift = "06:45-15:45"
                elif engineer in roles["Tickets"]:
                    assignment = "Tickets"
                    shift = "08:00-17:00"
                elif not is_weekday(current_date):
                    assignment = "Weekend Coverage"
                    shift = "Weekend"
                else:
                    assignment = "Available"
                    shift = "08:00-17:00"
            
            row[f"{i+1}) Engineer"] = engineer
            row[f"Status {i+1}"] = status
            row[f"Assignment {i+1}"] = assignment
            row[f"Shift {i+1}"] = shift
        
        schedule_rows.append(row)
    
    # Calculate fairness metrics
    fairness_report = calculate_fairness_metrics(schedule_rows, engineers)
    
    return {
        'schedule': schedule_rows,
        'metadata': {
            'team_size': team_size,
            'role_config': role_config,
            'warnings': warnings,
            'fairness': fairness_report
        }
    }