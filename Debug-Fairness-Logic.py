#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from schedule_core import EnhancedFairnessTracker, build_rotation, calculate_fairness_weighted_selection

def test_fairness_logic():
    print("🔍 Debugging Fairness Logic")
    print("=" * 50)
    
    engineers = ["Dan", "Dami", "Mario", "Mahmoud", "Prince", "Sherwin"]
    fairness_tracker = EnhancedFairnessTracker(engineers)
    
    print(f"Engineers: {engineers}")
    print()
    
    # Test base rotation
    base_rotation = build_rotation(engineers, 0)
    print(f"Base rotation (seed=0): {base_rotation}")
    print()
    
    # Test fairness weights initially (should be all 0)
    initial_weights = fairness_tracker.get_fairness_weights('weekend')
    print(f"Initial fairness weights: {initial_weights}")
    print()
    
    # Test fairness-weighted selection initially
    fairness_ordered = calculate_fairness_weighted_selection(base_rotation, 'weekend', fairness_tracker, base_rotation)
    print(f"Initial fairness-ordered selection: {fairness_ordered}")
    print()
    
    # Simulate weekend assignments for several weeks
    weekend_assignments = {}
    
    for week in range(5):
        print(f"--- Week {week} ---")
        
        # Get fairness weights before assignment
        weights_before = fairness_tracker.get_fairness_weights('weekend')
        print(f"Fairness weights before: {weights_before}")
        
        # Get fairness-ordered candidates
        fairness_ordered = calculate_fairness_weighted_selection(base_rotation, 'weekend', fairness_tracker, base_rotation)
        print(f"Fairness-ordered candidates: {fairness_ordered}")
        
        # Apply consecutive weekend prevention
        available_engineers = fairness_ordered.copy()
        if week > 0 and (week - 1) in weekend_assignments:
            previous_weekend_worker = weekend_assignments[week - 1]
            print(f"Previous weekend worker (week {week-1}): {previous_weekend_worker}")
            
            if previous_weekend_worker in available_engineers and len(available_engineers) > 1:
                available_engineers.remove(previous_weekend_worker)
                print(f"Removed {previous_weekend_worker} to prevent consecutive weekends")
            
        print(f"Available engineers after consecutive prevention: {available_engineers}")
        
        # Select weekend worker
        selected_engineer = available_engineers[0]
        weekend_assignments[week] = selected_engineer
        
        print(f"Selected: {selected_engineer}")
        
        # Track the assignment
        fairness_tracker.track_assignment_with_weight(selected_engineer, 'weekend', f"week_{week}", 2.0)
        
        # Get fairness weights after assignment
        weights_after = fairness_tracker.get_fairness_weights('weekend')
        print(f"Fairness weights after: {weights_after}")
        print()
    
    print("Final Weekend Assignments:")
    for week, engineer in weekend_assignments.items():
        print(f"Week {week}: {engineer}")
    
    # Check for consecutive weekends
    print("\nConsecutive Weekend Check:")
    for week in range(1, len(weekend_assignments)):
        if weekend_assignments[week] == weekend_assignments[week - 1]:
            print(f"❌ CONSECUTIVE: {weekend_assignments[week]} works Week {week-1} and Week {week}")
        else:
            print(f"✅ OK: Week {week-1} ({weekend_assignments[week-1]}) → Week {week} ({weekend_assignments[week]})")

if __name__ == "__main__":
    test_fairness_logic()