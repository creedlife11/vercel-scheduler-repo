"""
Unit tests for scheduling logic
"""
import unittest
from datetime import date, timedelta
import sys
import os

# Add the parent directory to the path to import from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.generate import (
    build_rotation,
    is_weekday,
    week_index,
    weekend_worker_for_week,
    works_today,
    get_oncall_engineer_for_week,
    validate_request_data
)

class TestSchedulingLogic(unittest.TestCase):
    
    def setUp(self):
        self.engineers = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank']
        self.start_sunday = date(2025, 8, 10)  # A Sunday
    
    def test_build_rotation(self):
        """Test rotation building with different seeds"""
        # Seed 0 should return original order
        rotation = build_rotation(self.engineers, 0)
        self.assertEqual(rotation, self.engineers)
        
        # Seed 1 should start from second engineer
        rotation = build_rotation(self.engineers, 1)
        expected = ['Bob', 'Carol', 'Dan', 'Eve', 'Frank', 'Alice']
        self.assertEqual(rotation, expected)
        
        # Seed beyond length should wrap around
        rotation = build_rotation(self.engineers, 7)  # 7 % 6 = 1
        expected = ['Bob', 'Carol', 'Dan', 'Eve', 'Frank', 'Alice']
        self.assertEqual(rotation, expected)
    
    def test_is_weekday(self):
        """Test weekday detection"""
        # Sunday (weekday 6) should be False
        sunday = date(2025, 8, 10)
        self.assertFalse(is_weekday(sunday))
        
        # Monday (weekday 0) should be True
        monday = date(2025, 8, 11)
        self.assertTrue(is_weekday(monday))
        
        # Friday (weekday 4) should be True
        friday = date(2025, 8, 15)
        self.assertTrue(is_weekday(friday))
        
        # Saturday (weekday 5) should be False
        saturday = date(2025, 8, 16)
        self.assertFalse(is_weekday(saturday))
    
    def test_week_index(self):
        """Test week index calculation"""
        # Same week should be 0
        same_day = self.start_sunday
        self.assertEqual(week_index(self.start_sunday, same_day), 0)
        
        # Next day should still be week 0
        next_day = self.start_sunday + timedelta(days=1)
        self.assertEqual(week_index(self.start_sunday, next_day), 0)
        
        # Next Sunday should be week 1
        next_sunday = self.start_sunday + timedelta(days=7)
        self.assertEqual(week_index(self.start_sunday, next_sunday), 1)
    
    def test_weekend_worker_for_week(self):
        """Test weekend worker assignment"""
        rotation = build_rotation(self.engineers, 0)
        
        # Week 0 should be first engineer
        worker = weekend_worker_for_week(rotation, 0)
        self.assertEqual(worker, 'Alice')
        
        # Week 1 should be second engineer
        worker = weekend_worker_for_week(rotation, 1)
        self.assertEqual(worker, 'Bob')
        
        # Week 6 should wrap around to first engineer
        worker = weekend_worker_for_week(rotation, 6)
        self.assertEqual(worker, 'Alice')
    
    def test_get_oncall_engineer_for_week(self):
        """Test on-call engineer assignment (cannot work weekend same week)"""
        weekend_seeded = build_rotation(self.engineers, 0)  # Alice works weekend week 0
        seeds = {'oncall': 0}
        
        # Week 0: Alice works weekend, so on-call should be Bob (next in rotation)
        oncall = get_oncall_engineer_for_week(self.engineers, 0, weekend_seeded, seeds)
        self.assertNotEqual(oncall, 'Alice')  # Should not be weekend worker
        self.assertIn(oncall, self.engineers)  # Should be valid engineer
    
    def test_validate_request_data_valid(self):
        """Test validation with valid data"""
        valid_data = {
            'engineers': ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank'],
            'start_sunday': '2025-08-10',
            'weeks': 8,
            'seeds': {'weekend': 0, 'oncall': 1, 'contacts': 2, 'appointments': 3, 'early': 0},
            'leave': [{'Engineer': 'Alice', 'Date': '2025-08-15', 'Reason': 'PTO'}],
            'format': 'csv'
        }
        
        is_valid, errors = validate_request_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_request_data_invalid_engineers(self):
        """Test validation with invalid engineers"""
        # Too few engineers
        invalid_data = {
            'engineers': ['Alice', 'Bob', 'Carol'],
            'start_sunday': '2025-08-10',
            'weeks': 8,
            'seeds': {},
            'leave': [],
            'format': 'csv'
        }
        
        is_valid, errors = validate_request_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('6 engineers' in error for error in errors))
    
    def test_validate_request_data_invalid_date(self):
        """Test validation with invalid start date"""
        # Not a Sunday
        invalid_data = {
            'engineers': ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank'],
            'start_sunday': '2025-08-11',  # Monday
            'weeks': 8,
            'seeds': {},
            'leave': [],
            'format': 'csv'
        }
        
        is_valid, errors = validate_request_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('Sunday' in error for error in errors))
    
    def test_validate_request_data_invalid_weeks(self):
        """Test validation with invalid weeks"""
        invalid_data = {
            'engineers': ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank'],
            'start_sunday': '2025-08-10',
            'weeks': 100,  # Too many weeks
            'seeds': {},
            'leave': [],
            'format': 'csv'
        }
        
        is_valid, errors = validate_request_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertTrue(any('between 1 and 52' in error for error in errors))

if __name__ == '__main__':
    unittest.main()