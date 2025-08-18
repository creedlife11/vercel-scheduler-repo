"""
Property-based tests using Hypothesis to fuzz inputs and verify invariants
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import date, timedelta
import sys
import os

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

from api.generate import make_schedule_simple, validate_request_data
from lib.invariants import verify_schedule_invariants

# Strategies for generating test data
@st.composite
def valid_engineers(draw):
    """Generate exactly 6 unique engineer names"""
    names = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=20),
        min_size=6, max_size=6, unique=True
    ))
    return names

@st.composite
def valid_sunday_date(draw):
    """Generate a valid Sunday date within reasonable range"""
    # Generate dates from 2024 to 2026
    base_date = date(2024, 1, 7)  # A Sunday
    days_offset = draw(st.integers(min_value=0, max_value=730))  # ~2 years
    candidate_date = base_date + timedelta(days=days_offset)
    
    # Ensure it's a Sunday
    days_to_sunday = (candidate_date.weekday() + 1) % 7
    sunday_date = candidate_date - timedelta(days=days_to_sunday)
    return sunday_date

@st.composite
def valid_seeds(draw):
    """Generate valid seed configuration"""
    return {
        'weekend': draw(st.integers(min_value=0, max_value=5)),
        'oncall': draw(st.integers(min_value=0, max_value=5)),
        'contacts': draw(st.integers(min_value=0, max_value=5)),
        'appointments': draw(st.integers(min_value=0, max_value=5)),
        'early': draw(st.integers(min_value=0, max_value=5)),
    }

@st.composite
def valid_leave_data(draw, engineers, start_date, weeks):
    """Generate valid leave data"""
    end_date = start_date + timedelta(days=weeks * 7 - 1)
    
    # Generate 0-10 leave entries
    num_entries = draw(st.integers(min_value=0, max_value=10))
    leave_entries = []
    
    for _ in range(num_entries):
        engineer = draw(st.sampled_from(engineers))
        # Generate date within the schedule period
        days_offset = draw(st.integers(min_value=0, max_value=weeks * 7 - 1))
        leave_date = start_date + timedelta(days=days_offset)
        reason = draw(st.text(min_size=1, max_size=20))
        
        leave_entries.append({
            'Engineer': engineer,
            'Date': leave_date.strftime('%Y-%m-%d'),
            'Reason': reason
        })
    
    return leave_entries

class TestScheduleInvariants:
    
    @given(
        engineers=valid_engineers(),
        start_sunday=valid_sunday_date(),
        weeks=st.integers(min_value=1, max_value=8),
        seeds=valid_seeds()
    )
    @settings(max_examples=50, deadline=5000)
    def test_schedule_invariants_hold(self, engineers, start_sunday, weeks, seeds):
        """Test that all schedule invariants hold for various inputs"""
        
        # Generate leave data
        leave_data = []  # Start with no leave for simplicity
        
        try:
            # Generate schedule
            schedule_data = make_schedule_simple(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave_data=leave_data
            )
            
            # Convert leave data to map format
            leave_map = {engineer: set() for engineer in engineers}
            
            # Verify invariants
            violations = verify_schedule_invariants(
                schedule_data, engineers, start_sunday, weeks, leave_map
            )
            
            # Assert no violations
            assert len(violations) == 0, f"Invariant violations: {violations}"
            
        except Exception as e:
            # If schedule generation fails, that's also a test failure
            pytest.fail(f"Schedule generation failed: {e}")
    
    @given(
        engineers=valid_engineers(),
        start_sunday=valid_sunday_date(),
        weeks=st.integers(min_value=2, max_value=6),
        seeds=valid_seeds()
    )
    @settings(max_examples=30, deadline=5000)
    def test_schedule_with_leave_invariants(self, engineers, start_sunday, weeks, seeds):
        """Test invariants hold even with leave data"""
        
        # Generate some leave data
        leave_data = []
        if weeks >= 2:  # Only add leave for longer schedules
            # Add 1-2 leave entries
            for i in range(min(2, len(engineers))):
                leave_date = start_sunday + timedelta(days=7 + i)  # Second week
                leave_data.append({
                    'Engineer': engineers[i],
                    'Date': leave_date.strftime('%Y-%m-%d'),
                    'Reason': 'PTO'
                })
        
        try:
            # Generate schedule
            schedule_data = make_schedule_simple(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave_data=leave_data
            )
            
            # Convert leave data to map format
            leave_map = {engineer: set() for engineer in engineers}
            for entry in leave_data:
                engineer = entry['Engineer']
                leave_date = date.fromisoformat(entry['Date'])
                leave_map[engineer].add(leave_date)
            
            # Verify invariants
            violations = verify_schedule_invariants(
                schedule_data, engineers, start_sunday, weeks, leave_map
            )
            
            # Assert no violations
            assert len(violations) == 0, f"Invariant violations: {violations}"
            
        except Exception as e:
            pytest.fail(f"Schedule generation with leave failed: {e}")
    
    @given(
        engineers=valid_engineers(),
        weeks=st.integers(min_value=4, max_value=12)
    )
    @settings(max_examples=20, deadline=10000)
    def test_fairness_across_multiple_weeks(self, engineers, weeks):
        """Test that assignments are fair across longer periods"""
        
        start_sunday = date(2025, 1, 5)  # Fixed Sunday
        seeds = {'weekend': 0, 'oncall': 0, 'contacts': 0, 'appointments': 0, 'early': 0}
        
        try:
            schedule_data = make_schedule_simple(
                start_sunday=start_sunday,
                weeks=weeks,
                engineers=engineers,
                seeds=seeds,
                leave_data=[]
            )
            
            leave_map = {engineer: set() for engineer in engineers}
            
            violations = verify_schedule_invariants(
                schedule_data, engineers, start_sunday, weeks, leave_map
            )
            
            assert len(violations) == 0, f"Fairness violations: {violations}"
            
        except Exception as e:
            pytest.fail(f"Long-term fairness test failed: {e}")

class TestInputValidation:
    
    @given(
        engineers=st.lists(st.text(), min_size=0, max_size=10),
        start_date=st.text(),
        weeks=st.integers(),
        seeds=st.dictionaries(st.text(), st.integers())
    )
    @settings(max_examples=100, deadline=1000)
    def test_validation_catches_invalid_inputs(self, engineers, start_date, weeks, seeds):
        """Test that validation catches various invalid inputs"""
        
        data = {
            'engineers': engineers,
            'start_sunday': start_date,
            'weeks': weeks,
            'seeds': seeds,
            'leave': [],
            'format': 'csv'
        }
        
        is_valid, errors = validate_request_data(data)
        
        # If input is clearly invalid, validation should catch it
        if (len(engineers) != 6 or 
            not isinstance(weeks, int) or weeks < 1 or weeks > 52 or
            not start_date or not isinstance(start_date, str)):
            assert not is_valid, f"Validation should have failed for: {data}"
            assert len(errors) > 0, "Should have validation errors"

class TestEdgeCases:
    
    def test_year_boundary(self):
        """Test schedule generation across year boundary"""
        engineers = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank']
        start_sunday = date(2024, 12, 29)  # Last Sunday of 2024
        weeks = 3  # Crosses into 2025
        seeds = {'weekend': 0, 'oncall': 0, 'contacts': 0, 'appointments': 0, 'early': 0}
        
        schedule_data = make_schedule_simple(
            start_sunday=start_sunday,
            weeks=weeks,
            engineers=engineers,
            seeds=seeds,
            leave_data=[]
        )
        
        leave_map = {engineer: set() for engineer in engineers}
        violations = verify_schedule_invariants(
            schedule_data, engineers, start_sunday, weeks, leave_map
        )
        
        assert len(violations) == 0, f"Year boundary violations: {violations}"
    
    def test_leap_year_february(self):
        """Test schedule generation in leap year February"""
        engineers = ['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank']
        start_sunday = date(2024, 2, 25)  # Leap year
        weeks = 2
        seeds = {'weekend': 0, 'oncall': 0, 'contacts': 0, 'appointments': 0, 'early': 0}
        
        schedule_data = make_schedule_simple(
            start_sunday=start_sunday,
            weeks=weeks,
            engineers=engineers,
            seeds=seeds,
            leave_data=[]
        )
        
        leave_map = {engineer: set() for engineer in engineers}
        violations = verify_schedule_invariants(
            schedule_data, engineers, start_sunday, weeks, leave_map
        )
        
        assert len(violations) == 0, f"Leap year violations: {violations}"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])