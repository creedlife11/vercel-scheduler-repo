"""
Tests for contacts rotation logic - ensuring no consecutive days
"""
import unittest
from datetime import date, timedelta
import sys
import os

# Add the parent directory to the path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.generate import make_schedule_simple

class TestContactsRotation(unittest.TestCase):
    
    def setUp(self):
        self.engineers = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank']
        self.start_sunday = date(2025, 8, 17)  # A Sunday
        self.seeds = {'weekend': 0, 'oncall': 0, 'contacts': 0, 'appointments': 0, 'early': 0}
    
    def test_no_consecutive_contacts_days(self):
        """Test that no engineer works contacts on consecutive weekdays"""
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=4,  # Test over multiple weeks
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        
        # Extract weekday contacts assignments
        weekday_contacts = []
        for row in schedule_data:
            if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] and row['Contacts']:
                weekday_contacts.append({
                    'date': row['Date'],
                    'day': row['Day'],
                    'engineer': row['Contacts']
                })
        
        # Verify no consecutive assignments
        for i in range(1, len(weekday_contacts)):
            current_engineer = weekday_contacts[i]['engineer']
            previous_engineer = weekday_contacts[i-1]['engineer']
            current_date = weekday_contacts[i]['date']
            previous_date = weekday_contacts[i-1]['date']
            
            # Check if these are consecutive weekdays
            current_dt = date.fromisoformat(current_date)
            previous_dt = date.fromisoformat(previous_date)
            
            # If it's the next weekday, they shouldn't be the same engineer
            if (current_dt - previous_dt).days == 1:  # Consecutive calendar days
                self.assertNotEqual(current_engineer, previous_engineer,
                                  f"Engineer {current_engineer} assigned contacts on consecutive days: {previous_date} and {current_date}")
            elif (current_dt - previous_dt).days == 3 and previous_dt.weekday() == 4:  # Friday to Monday
                self.assertNotEqual(current_engineer, previous_engineer,
                                  f"Engineer {current_engineer} assigned contacts on Friday {previous_date} and Monday {current_date}")
    
    def test_contacts_rotation_with_leave(self):
        """Test contacts rotation when engineers are on leave"""
        # Add leave for some engineers
        leave_data = [
            {'Engineer': 'Alice', 'Date': '2025-08-19', 'Reason': 'PTO'},  # Tuesday
            {'Engineer': 'Bob', 'Date': '2025-08-20', 'Reason': 'PTO'},    # Wednesday
        ]
        
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=2,
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=leave_data
        )
        
        schedule_data = result['schedule']
        
        # Extract weekday contacts assignments
        weekday_contacts = []
        for row in schedule_data:
            if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] and row['Contacts']:
                weekday_contacts.append({
                    'date': row['Date'],
                    'day': row['Day'],
                    'engineer': row['Contacts']
                })
        
        # Verify no consecutive assignments (even with leave)
        for i in range(1, len(weekday_contacts)):
            current_engineer = weekday_contacts[i]['engineer']
            previous_engineer = weekday_contacts[i-1]['engineer']
            current_date = weekday_contacts[i]['date']
            previous_date = weekday_contacts[i-1]['date']
            
            current_dt = date.fromisoformat(current_date)
            previous_dt = date.fromisoformat(previous_date)
            
            # Check consecutive weekdays
            if (current_dt - previous_dt).days == 1:
                self.assertNotEqual(current_engineer, previous_engineer,
                                  f"Engineer {current_engineer} assigned contacts on consecutive days: {previous_date} and {current_date}")
            elif (current_dt - previous_dt).days == 3 and previous_dt.weekday() == 4:  # Friday to Monday
                self.assertNotEqual(current_engineer, previous_engineer,
                                  f"Engineer {current_engineer} assigned contacts on Friday {previous_date} and Monday {current_date}")
        
        # Verify engineers on leave are not assigned contacts
        for row in schedule_data:
            if row['Date'] in ['2025-08-19', '2025-08-20']:
                contacts_engineer = row['Contacts']
                if row['Date'] == '2025-08-19':
                    self.assertNotEqual(contacts_engineer, 'Alice', "Alice on leave but assigned to contacts")
                elif row['Date'] == '2025-08-20':
                    self.assertNotEqual(contacts_engineer, 'Bob', "Bob on leave but assigned to contacts")
    
    def test_contacts_fairness_over_time(self):
        """Test that contacts assignments are distributed fairly over time"""
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=6,  # Longer period for fairness testing
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        
        # Count contacts assignments per engineer
        contacts_count = {engineer: 0 for engineer in self.engineers}
        
        for row in schedule_data:
            if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] and row['Contacts']:
                contacts_count[row['Contacts']] += 1
        
        # Check fairness - max difference should be <= 1
        counts = list(contacts_count.values())
        max_count = max(counts)
        min_count = min(counts)
        
        self.assertLessEqual(max_count - min_count, 1,
                           f"Contacts assignments not fair: {contacts_count}")
        
        # Ensure everyone gets some contacts assignments
        for engineer, count in contacts_count.items():
            self.assertGreater(count, 0, f"Engineer {engineer} never assigned to contacts")
    
    def test_small_team_contacts_rotation(self):
        """Test contacts rotation with smaller team (5 engineers)"""
        small_team = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve']
        
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=3,
            engineers=small_team,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        
        # Extract weekday contacts assignments
        weekday_contacts = []
        for row in schedule_data:
            if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] and row['Contacts']:
                weekday_contacts.append({
                    'date': row['Date'],
                    'engineer': row['Contacts']
                })
        
        # Verify no consecutive assignments
        for i in range(1, len(weekday_contacts)):
            current_engineer = weekday_contacts[i]['engineer']
            previous_engineer = weekday_contacts[i-1]['engineer']
            current_date = weekday_contacts[i]['date']
            previous_date = weekday_contacts[i-1]['date']
            
            current_dt = date.fromisoformat(current_date)
            previous_dt = date.fromisoformat(previous_date)
            
            if (current_dt - previous_dt).days == 1:
                self.assertNotEqual(current_engineer, previous_engineer,
                                  f"Small team: Engineer {current_engineer} assigned contacts on consecutive days")
    
    def test_weekend_does_not_affect_contacts_rotation(self):
        """Test that weekend days don't interfere with weekday contacts rotation"""
        result = make_schedule_simple(
            start_sunday=self.start_sunday,
            weeks=2,
            engineers=self.engineers,
            seeds=self.seeds,
            leave_data=[]
        )
        
        schedule_data = result['schedule']
        
        # Find Friday and following Monday
        friday_contacts = None
        monday_contacts = None
        
        for row in schedule_data:
            if row['Day'] == 'Fri' and row['Contacts']:
                friday_contacts = row['Contacts']
            elif row['Day'] == 'Mon' and row['Contacts'] and friday_contacts:
                monday_contacts = row['Contacts']
                break
        
        # Friday and Monday contacts should be different engineers
        if friday_contacts and monday_contacts:
            self.assertNotEqual(friday_contacts, monday_contacts,
                              f"Same engineer ({friday_contacts}) assigned contacts on Friday and following Monday")
    
    def test_contacts_assignment_with_multiple_seeds(self):
        """Test that different seeds still prevent consecutive contacts assignments"""
        for seed in range(6):  # Test different starting positions
            with self.subTest(seed=seed):
                test_seeds = self.seeds.copy()
                test_seeds['contacts'] = seed
                
                result = make_schedule_simple(
                    start_sunday=self.start_sunday,
                    weeks=2,
                    engineers=self.engineers,
                    seeds=test_seeds,
                    leave_data=[]
                )
                
                schedule_data = result['schedule']
                
                # Extract consecutive weekdays and verify no same engineer
                weekday_contacts = []
                for row in schedule_data:
                    if row['Day'] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] and row['Contacts']:
                        weekday_contacts.append({
                            'date': row['Date'],
                            'engineer': row['Contacts']
                        })
                
                # Check first few consecutive days
                for i in range(1, min(5, len(weekday_contacts))):
                    current_engineer = weekday_contacts[i]['engineer']
                    previous_engineer = weekday_contacts[i-1]['engineer']
                    
                    self.assertNotEqual(current_engineer, previous_engineer,
                                      f"Seed {seed}: Consecutive contacts assignment on days {i-1} and {i}")

if __name__ == '__main__':
    unittest.main()