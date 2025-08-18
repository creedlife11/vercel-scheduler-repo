"""
Tests for CSV integrity and column alignment
"""
import unittest
import csv
import io
from datetime import date
import sys
import os

# Add the parent directory to the path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.generate import (
    make_schedule_simple,
    generate_csv_content,
    get_csv_fieldnames,
    validate_csv_row_integrity
)

class TestCSVIntegrity(unittest.TestCase):
    
    def setUp(self):
        self.engineers = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank']
        self.start_sunday = date(2025, 8, 17)  # A Sunday
        self.weeks = 2
        self.seeds = {'weekend': 0, 'oncall': 0, 'contacts': 0, 'appointments': 0, 'early': 0}
    
    def test_csv_fieldnames_generation(self):
        """Test that fieldnames are generated correctly for different team sizes"""
        # Test 6-person team
        fieldnames = get_csv_fieldnames(6)
        expected_base = ["Date", "Day", "WeekIndex", "OnCall", "Contacts", "Appointments", "Early1", "Early2", "Tickets"]
        expected_engineer_fields = []
        for i in range(1, 7):
            expected_engineer_fields.extend([
                f"{i}) Engineer", f"Status {i}", f"Assignment {i}", f"Shift {i}"
            ])
        
        expected = expected_base + expected_engineer_fields
        self.assertEqual(fieldnames, expected)
        self.assertEqual(len(fieldnames), 9 + 6*4)  # 9 base + 24 engineer fields = 33
    
    def test_csv_column_count_consistency(self):
        """Test that all CSV rows have exactly the same number of columns"""
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=self.weeks,
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        metadata = result['metadata']
        
        # Generate CSV content
        csv_content = generate_csv_content(schedule_data, len(self.engineers), metadata, include_fairness=False)
        
        # Parse CSV and verify column counts
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Filter out comment lines
        data_rows = [row for row in rows if not (len(row) == 1 and row[0].startswith('#'))]
        
        # All rows should have the same number of columns
        expected_columns = len(get_csv_fieldnames(len(self.engineers)))
        
        for i, row in enumerate(data_rows):
            self.assertEqual(len(row), expected_columns, 
                           f"Row {i} has {len(row)} columns, expected {expected_columns}. Row: {row[:10]}...")
    
    def test_csv_header_data_alignment(self):
        """Test that CSV header and data rows are properly aligned"""
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=self.weeks,
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        metadata = result['metadata']
        
        # Generate CSV content
        csv_content = generate_csv_content(schedule_data, len(self.engineers), metadata, include_fairness=False)
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Verify we have data
        self.assertGreater(len(rows), 0)
        
        # Check first few rows for proper structure
        for i, row in enumerate(rows[:5]):  # Check first 5 rows
            # Date should be a valid date string
            self.assertRegex(row['Date'], r'^\d{4}-\d{2}-\d{2}$', f"Row {i}: Invalid date format")
            
            # Day should be a valid day name
            self.assertIn(row['Day'], ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], f"Row {i}: Invalid day")
            
            # WeekIndex should be numeric
            self.assertTrue(row['WeekIndex'].isdigit(), f"Row {i}: WeekIndex not numeric")
            
            # Engineer fields should contain engineer names or be empty
            for j in range(1, len(self.engineers) + 1):
                engineer_field = f"{j}) Engineer"
                status_field = f"Status {j}"
                
                engineer_name = row[engineer_field]
                status = row[status_field]
                
                # If engineer name is present, it should be one of our engineers
                if engineer_name:
                    self.assertIn(engineer_name, self.engineers, 
                                f"Row {i}: Unknown engineer '{engineer_name}' in {engineer_field}")
                
                # Status should be valid
                if status:
                    self.assertIn(status, ['WORK', 'OFF', 'LEAVE'], 
                                f"Row {i}: Invalid status '{status}' in {status_field}")
    
    def test_no_column_shift_with_leave(self):
        """Test that leave doesn't cause column shifts"""
        # Add some leave data
        leave_data = [
            {'Engineer': 'Alice', 'Date': '2025-08-19', 'Reason': 'PTO'},
            {'Engineer': 'Bob', 'Date': '2025-08-20', 'Reason': 'Sick'}
        ]
        
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=self.weeks,
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=leave_data
        )
        
        schedule_data = result['schedule']
        metadata = result['metadata']
        
        # Generate CSV content
        csv_content = generate_csv_content(schedule_data, len(self.engineers), metadata, include_fairness=False)
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Find the leave days and verify structure
        leave_rows = [row for row in rows if row['Date'] in ['2025-08-19', '2025-08-20']]
        
        for row in leave_rows:
            # Verify that engineer names are still in engineer columns, not status columns
            for j in range(1, len(self.engineers) + 1):
                engineer_field = f"{j}) Engineer"
                status_field = f"Status {j}"
                assignment_field = f"Assignment {j}"
                shift_field = f"Shift {j}"
                
                engineer_name = row[engineer_field]
                status = row[status_field]
                assignment = row[assignment_field]
                shift = row[shift_field]
                
                # Engineer field should contain engineer name or be empty
                if engineer_name:
                    self.assertIn(engineer_name, self.engineers, 
                                f"Engineer field contains non-engineer value: '{engineer_name}'")
                
                # Status field should not contain engineer names
                if status:
                    self.assertNotIn(status, self.engineers, 
                                   f"Status field contains engineer name: '{status}'")
                    self.assertIn(status, ['WORK', 'OFF', 'LEAVE'], 
                                f"Invalid status: '{status}'")
                
                # Assignment field should not contain time strings
                if assignment and ':' in assignment and '-' in assignment:
                    self.fail(f"Assignment field contains time string: '{assignment}'")
                
                # Shift field should be time format, Weekend, or empty
                if shift and shift not in ['Weekend', '']:
                    self.assertRegex(shift, r'^\d{2}:\d{2}-\d{2}:\d{2}$', 
                                   f"Invalid shift format: '{shift}'")
    
    def test_variable_team_sizes(self):
        """Test CSV integrity with different team sizes"""
        for team_size in [5, 6, 7, 8]:
            with self.subTest(team_size=team_size):
                engineers = [f"Engineer{i}" for i in range(1, team_size + 1)]
                
                result = make_schedule_simple(
                    start_sunday=self.start_sunday,
                    weeks=1,  # Short test
                    engineers=engineers,
                    seeds=self.seeds,
                    leave_data=[]
                )
                
                schedule_data = result['schedule']
                metadata = result['metadata']
                
                # Generate CSV content
                csv_content = generate_csv_content(schedule_data, team_size, metadata, include_fairness=False)
                
                # Parse and verify
                csv_reader = csv.reader(io.StringIO(csv_content))
                rows = list(csv_reader)
                
                # Filter out comments
                data_rows = [row for row in rows if not (len(row) == 1 and row[0].startswith('#'))]
                
                expected_columns = len(get_csv_fieldnames(team_size))
                
                for i, row in enumerate(data_rows):
                    self.assertEqual(len(row), expected_columns, 
                                   f"Team size {team_size}, Row {i}: Expected {expected_columns} columns, got {len(row)}")
    
    def test_row_validation(self):
        """Test the row validation function"""
        # Valid row
        valid_row = {
            'Date': '2025-08-17',
            'Day': 'Sun',
            'WeekIndex': '0',
            '1) Engineer': 'Alice',
            'Status 1': 'WORK',
            'Assignment 1': 'Weekend Coverage',
            'Shift 1': 'Weekend'
        }
        
        errors = validate_csv_row_integrity(valid_row, 1)
        self.assertEqual(len(errors), 0)
        
        # Invalid row - missing required field
        invalid_row = {
            'Day': 'Sun',
            'WeekIndex': '0'
            # Missing Date
        }
        
        errors = validate_csv_row_integrity(invalid_row, 1)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Missing required field: Date' in error for error in errors))
        
        # Invalid status
        invalid_status_row = {
            'Date': '2025-08-17',
            'Day': 'Sun',
            'WeekIndex': '0',
            '1) Engineer': 'Alice',
            'Status 1': 'INVALID_STATUS'
        }
        
        errors = validate_csv_row_integrity(invalid_status_row, 1)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Invalid status' in error for error in errors))

if __name__ == '__main__':
    unittest.main()