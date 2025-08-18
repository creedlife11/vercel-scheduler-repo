from http.server import BaseHTTPRequestHandler
import json
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional

def validate_request_data(data: Dict) -> Tuple[bool, List[str]]:
    """
    Comprehensive validation of request data
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate engineers
    engineers = data.get('engineers', [])
    if not isinstance(engineers, list):
        errors.append("Engineers must be a list")
    elif len(engineers) != 6:
        errors.append(f"Exactly 6 engineers are required, got {len(engineers)}")
    else:
        # Check individual engineer names
        for i, engineer in enumerate(engineers):
            if not isinstance(engineer, str):
                errors.append(f"Engineer {i+1} must be a string")
            elif not engineer.strip():
                errors.append(f"Engineer {i+1} cannot be empty")
            elif len(engineer.strip()) > 50:
                errors.append(f"Engineer {i+1} name too long (max 50 characters)")
        
        # Check for duplicates
        if len(set(engineer.strip() for engineer in engineers)) != len(engineers):
            errors.append("Engineer names must be unique")
    
    # Validate start date
    start_sunday_str = data.get('start_sunday', '')
    if not isinstance(start_sunday_str, str):
        errors.append("start_sunday must be a string")
    elif not re.match(r'^\d{4}-\d{2}-\d{2}$', start_sunday_str):
        errors.append("start_sunday must be in YYYY-MM-DD format")
    else:
        try:
            start_date = datetime.strptime(start_sunday_str, '%Y-%m-%d').date()
            if start_date.weekday() != 6:  # Sunday = 6
                errors.append("start_sunday must be a Sunday")
            # Check if date is reasonable (not too far in past/future)
            today = date.today()
            if start_date < today - timedelta(days=365):
                errors.append("start_sunday cannot be more than 1 year in the past")
            elif start_date > today + timedelta(days=730):
                errors.append("start_sunday cannot be more than 2 years in the future")
        except ValueError:
            errors.append("Invalid start_sunday date")
    
    # Validate weeks
    weeks = data.get('weeks', 0)
    if not isinstance(weeks, int):
        errors.append("weeks must be an integer")
    elif weeks < 1 or weeks > 52:
        errors.append("weeks must be between 1 and 52")
    
    # Validate seeds
    seeds = data.get('seeds', {})
    if not isinstance(seeds, dict):
        errors.append("seeds must be an object")
    else:
        valid_seed_keys = {'weekend', 'oncall', 'contacts', 'appointments', 'early'}
        for key, value in seeds.items():
            if key not in valid_seed_keys:
                errors.append(f"Invalid seed key: {key}")
            elif not isinstance(value, int):
                errors.append(f"Seed {key} must be an integer")
            elif value < 0 or value > 5:
                errors.append(f"Seed {key} must be between 0 and 5")
    
    # Validate leave data
    leave_data = data.get('leave', [])
    if not isinstance(leave_data, list):
        errors.append("leave must be a list")
    else:
        for i, leave_entry in enumerate(leave_data):
            if not isinstance(leave_entry, dict):
                errors.append(f"Leave entry {i+1} must be an object")
                continue
            
            engineer = leave_entry.get('Engineer', '')
            if not isinstance(engineer, str) or not engineer.strip():
                errors.append(f"Leave entry {i+1}: Engineer name is required")
            
            leave_date = leave_entry.get('Date', '')
            if not isinstance(leave_date, str):
                errors.append(f"Leave entry {i+1}: Date must be a string")
            elif not re.match(r'^\d{4}-\d{2}-\d{2}$', leave_date):
                errors.append(f"Leave entry {i+1}: Date must be in YYYY-MM-DD format")
            else:
                try:
                    datetime.strptime(leave_date, '%Y-%m-%d')
                except ValueError:
                    errors.append(f"Leave entry {i+1}: Invalid date")
    
    # Validate format
    format_type = data.get('format', 'csv')
    if not isinstance(format_type, str):
        errors.append("format must be a string")
    elif format_type.lower() not in ['csv', 'xlsx']:
        errors.append("format must be 'csv' or 'xlsx'")
    
    return len(errors) == 0, errors

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_error_response(self, status_code: int, error_message: str, details: Optional[List[str]] = None):
        """Send standardized error response"""
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        error_data = {'error': error_message}
        if details:
            error_data['details'] = details
        
        self.wfile.write(json.dumps(error_data).encode())
    
    def do_POST(self):
        """Handle POST requests with comprehensive validation"""
        try:
            # Check content length
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_response(400, "Request body is required")
                return
            
            if content_length > 1024 * 1024:  # 1MB limit
                self.send_error_response(413, "Request body too large (max 1MB)")
                return
            
            # Read and parse request body
            try:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.send_error_response(400, "Invalid JSON format", [str(e)])
                return
            except UnicodeDecodeError:
                self.send_error_response(400, "Invalid character encoding")
                return
            
            # Validate request data
            is_valid, validation_errors = validate_request_data(data)
            if not is_valid:
                self.send_error_response(400, "Validation failed", validation_errors)
                return
            
            # Extract validated parameters
            engineers = [eng.strip() for eng in data['engineers']]
            start_sunday = datetime.strptime(data['start_sunday'], '%Y-%m-%d').date()
            weeks = data['weeks']
            seeds = data.get('seeds', {})
            leave_data = data.get('leave', [])
            format_type = data.get('format', 'csv').lower()
            
            # Generate schedule
            schedule_data = make_schedule_simple(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave_data=leave_data
            )
            
            # Convert to CSV
            csv_lines = []
            if schedule_data:
                # Header
                csv_lines.append(','.join(schedule_data[0].keys()))
                # Data rows
                for row in schedule_data:
                    csv_lines.append(','.join(str(v) for v in row.values()))
            
            csv_content = '\n'.join(csv_lines)
            
            # Send response
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename=schedule.csv')
            self.end_headers()
            self.wfile.write(csv_content.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Internal server error: {str(e)}'}).encode())

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

def make_schedule_simple(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], leave_data: List[Dict]) -> List[Dict]:
    """Generate schedule with updated requirements"""
    
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
    
    # Pre-calculate weekly on-call assignments
    weekly_oncall = {}
    for w in range(weeks):
        weekly_oncall[w] = get_oncall_engineer_for_week(engineers, w, weekend_seeded, seeds)
    
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
            
            # 1. On-call engineer (same for entire week, cannot work weekend that week)
            # On-call engineer always works early shift
            week_oncall = weekly_oncall.get(w, "")
            if week_oncall in available:
                roles["OnCall"] = week_oncall
                roles["Early1"] = week_oncall  # On-call engineer is always Early1
                available.remove(week_oncall)
            
            # 2. Second early shift engineer
            if available:
                early_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("early", 0) + day_idx) % len(engineers)))
                roles["Early2"] = early_order[0] if len(early_order) >= 1 else ""
                if roles["Early2"]: available.remove(roles["Early2"])
            
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
    
    return schedule_rows