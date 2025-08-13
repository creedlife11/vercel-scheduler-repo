from http.server import BaseHTTPRequestHandler
import json
import pandas as pd
from datetime import datetime
import sys
import os

# Add the parent directory to the path to import schedule_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schedule_core import make_schedule

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extract parameters
            engineers = data.get('engineers', [])
            start_sunday_str = data.get('start_sunday', '')
            weeks = data.get('weeks', 8)
            seeds = data.get('seeds', {})
            leave_data = data.get('leave', [])
            format_type = data.get('format', 'csv')
            
            # Validate engineers
            if len(engineers) != 6:
                self.send_error(400, "Exactly 6 engineers are required")
                return
            
            # Parse start date
            try:
                start_sunday = datetime.strptime(start_sunday_str, '%Y-%m-%d').date()
            except ValueError:
                self.send_error(400, "Invalid date format. Use YYYY-MM-DD")
                return
            
            # Convert leave data to DataFrame
            leave_df = pd.DataFrame(leave_data) if leave_data else pd.DataFrame()
            
            # Generate schedule
            schedule_df = make_schedule(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave=leave_df
            )
            
            # Return appropriate format
            if format_type.lower() == 'xlsx':
                # Excel format
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    schedule_df.to_excel(writer, index=False, sheet_name='Schedule')
                output.seek(0)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', 'attachment; filename=schedule.xlsx')
                self.end_headers()
                self.wfile.write(output.getvalue())
            else:
                # CSV format (default)
                csv_data = schedule_df.to_csv(index=False)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv')
                self.send_header('Content-Disposition', 'attachment; filename=schedule.csv')
                self.end_headers()
                self.wfile.write(csv_data.encode('utf-8'))
                
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()