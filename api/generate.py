from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, date, timedelta
from typing import List, Dict

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
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
            else:
                data = {}
        
            # Extract parameters
            engineers = data.get('engineers', [])
            start_sunday_str = data.get('start_sunday', '')
            weeks = data.get('weeks', 8)
            seeds = data.get('seeds', {})
            leave_data = data.get('leave', [])
            format_type = data.get('format', 'csv')
            
            # Validate engineers
            if len(engineers) != 6:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Exactly 6 engineers are required'}).encode())
                return
            
            # Parse start date
            try:
                start_sunday = datetime.strptime(start_sunday_str, '%Y-%m-%d').date()
            except ValueError:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD'}).encode())
                return
            
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

def make_schedule_simple(start_sunday: date, weeks: int, engineers: List[str], seeds: Dict[str,int], leave_data: List[Dict]) -> List[Dict]:
    """Generate schedule without pandas dependency"""
    
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
        
        # Assign roles
        roles = {"Chat": "", "OnCall": "", "Appointments": "", "Early1": "", "Early2": ""}
        
        # Early shifts
        if is_weekday(current_date) and working:
            day_idx = (current_date - start_sunday).days
            order = sorted(working, key=lambda name: ((engineers.index(name) + seeds.get("early", 0) + day_idx) % len(engineers)))
            roles["Early1"] = order[0] if len(order) >= 1 else ""
            roles["Early2"] = order[1] if len(order) >= 2 else ""
        
        # Weekday roles
        if is_weekday(current_date):
            day_idx = (current_date - start_sunday).days
            available = working.copy()
            
            if available:
                chat_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("chat", 0) + day_idx) % len(engineers)))
                roles["Chat"] = chat_order[0]
                available.remove(roles["Chat"])
            
            if available:
                oncall_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("oncall", 0) + day_idx) % len(engineers)))
                roles["OnCall"] = oncall_order[0]
                available.remove(roles["OnCall"])
            
            if available:
                appt_order = sorted(available, key=lambda name: ((engineers.index(name) + seeds.get("appointments", 0) + day_idx) % len(engineers)))
                roles["Appointments"] = appt_order[0]
        
        # Build row
        row = {
            "Date": current_date.strftime('%Y-%m-%d'),
            "Day": dow,
            "WeekIndex": w,
            "Early1": roles["Early1"],
            "Early2": roles["Early2"],
            "Chat": roles["Chat"],
            "OnCall": roles["OnCall"],
            "Appointments": roles["Appointments"]
        }
        
        # Add engineer status columns
        for i, engineer in enumerate(engineers):
            status = "LEAVE" if engineer in leave_today else ("WORK" if works_today(engineer, current_date, start_sunday, weekend_seeded) else "OFF")
            shift = ""
            if status == "WORK":
                if engineer in (roles["Early1"], roles["Early2"]):
                    shift = "06:45-15:45"
                else:
                    shift = "08:00-17:00" if is_weekday(current_date) else "Weekend"
            
            row[f"{i+1}) Engineer"] = engineer
            row[f"Status {i+1}"] = status
            row[f"Shift {i+1}"] = shift
        
        schedule_rows.append(row)
    
    return schedule_rows