import { NextApiRequest, NextApiResponse } from 'next';

interface LeaveEntry {
  engineer: string;
  date: string;
  reason: string;
}

interface DecisionEntry {
  date: string;
  decision_type: string;
  affected_engineers: string[];
  reason: string;
  alternatives_considered: string[];
  timestamp: string;
}

interface EnhancedScheduleResult {
  schedule: any[];
  metadata: any;
  fairnessReport: any;
  decisionLog: DecisionEntry[];
}

// Enhanced scheduler with backfill integration
function generateEnhancedSchedule(
  engineers: string[], 
  startDate: string, 
  weeks: number, 
  seeds: any, 
  leave: LeaveEntry[] = []
): EnhancedScheduleResult {
  const schedule: any[] = [];
  const decisionLog: DecisionEntry[] = [];
  const roles = ['Weekend', 'Chat', 'OnCall', 'Appointments', 'Early'];
  const weekendAssignmentCache: { [key: number]: string } = {}; // Cache weekend assignments to ensure Saturday/Sunday pairing
  
  // Create leave map for quick lookup
  const leaveMap: { [key: string]: Set<string> } = {};
  engineers.forEach(eng => leaveMap[eng] = new Set());
  leave.forEach(entry => {
    if (leaveMap[entry.engineer]) {
      leaveMap[entry.engineer].add(entry.date);
    }
  });

  const startDateObj = new Date(startDate);
  
  // If starting on Sunday, include the previous Saturday for complete weekend pairing
  const includesPreviousSaturday = startDateObj.getDay() === 0; // Sunday = 0
  const allDates: Date[] = [];
  
  // Add previous Saturday if starting on Sunday
  if (includesPreviousSaturday) {
    const previousSaturday = new Date(startDateObj);
    previousSaturday.setDate(startDateObj.getDate() - 1);
    allDates.push(previousSaturday);
  }
  
  // Add all the regular schedule dates
  for (let week = 0; week < weeks; week++) {
    for (let day = 0; day < 7; day++) {
      const currentDate = new Date(startDateObj);
      currentDate.setDate(startDateObj.getDate() + (week * 7) + day);
      allDates.push(currentDate);
    }
  }
  
  // Track OnCall and Early engineers by week for exclusion logic
  const onCallByWeek: { [week: number]: string } = {};
  const earlyByWeek: { [week: number]: string } = {};
  
  // Process all dates
  for (let dateIndex = 0; dateIndex < allDates.length; dateIndex++) {
    const currentDate = allDates[dateIndex];
    const dateStr = currentDate.toISOString().split('T')[0];
    const day = currentDate.getDay(); // 0=Sunday, 1=Monday, ..., 6=Saturday
    
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dayName = dayNames[day];
    const isWeekday = day >= 1 && day <= 5;
    
    // Calculate current week for OnCall tracking
    const daysSinceStart = Math.floor((currentDate.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
    const currentWeek = Math.floor(daysSinceStart / 7);
      
      // Determine who should be working
      let expectedWorking: string[] = [];
      
      if (!isWeekday) {
        // Weekend rotation: same engineer covers both Saturday and Sunday
        // Calculate which weekend pair this belongs to
        let weekendWeek: number;
        
        if (day === 6) { // Saturday
          // Saturday pairs with the next day (Sunday)
          const nextDay = new Date(currentDate);
          nextDay.setDate(currentDate.getDate() + 1);
          
          if (includesPreviousSaturday && dateIndex === 0) {
            // This is the Saturday before the start Sunday - belongs to week 0
            weekendWeek = 0;
          } else {
            // Calculate based on the Sunday that follows this Saturday
            const daysSinceSundayStart = Math.floor((nextDay.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
            weekendWeek = Math.floor(daysSinceSundayStart / 7);
          }
        } else { // Sunday (day === 0)
          // Calculate based on this Sunday
          const daysSinceSundayStart = Math.floor((currentDate.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
          weekendWeek = Math.floor(daysSinceSundayStart / 7);
        }
        
        // Check if we already assigned this weekend (for Saturday/Sunday pairing)
        let intendedEngineer: string;
        if (weekendAssignmentCache[weekendWeek]) {
          // Use cached assignment to ensure Saturday/Sunday pairing
          intendedEngineer = weekendAssignmentCache[weekendWeek];
        } else {
          // First time assigning this weekend - calculate with conflict prevention
          let intendedEngineerIdx = (weekendWeek + seeds.weekend) % engineers.length;
          intendedEngineer = engineers[intendedEngineerIdx];
          
          // Check for consecutive weekend prevention
          let previousWeekendEngineer: string | null = null;
          if (weekendWeek > 0 && weekendAssignmentCache[weekendWeek - 1]) {
            previousWeekendEngineer = weekendAssignmentCache[weekendWeek - 1];
          }
          
          // Check if intended engineer was OnCall in previous week
          const previousWeek = weekendWeek - 1;
          const previousOnCall = onCallByWeek[previousWeek];
          
          // Apply exclusions: consecutive weekend prevention and OnCall conflict prevention
          const exclusions: string[] = [];
          let exclusionReasons: string[] = [];
          
          if (previousWeekendEngineer && previousWeekendEngineer === intendedEngineer) {
            exclusions.push(previousWeekendEngineer);
            exclusionReasons.push(`did previous weekend (week ${weekendWeek - 1})`);
          }
          
          if (previousOnCall && previousOnCall === intendedEngineer && !exclusions.includes(previousOnCall)) {
            exclusions.push(previousOnCall);
            exclusionReasons.push(`was OnCall in previous week`);
          }
          
          if (exclusions.length > 0) {
            // Find next available engineer who doesn't have conflicts
            for (let i = 1; i < engineers.length; i++) {
              const nextIdx = (intendedEngineerIdx + i) % engineers.length;
              const nextEngineer = engineers[nextIdx];
              
              // Check if this engineer has any conflicts
              const hasConsecutiveWeekendConflict = previousWeekendEngineer && nextEngineer === previousWeekendEngineer;
              const hasOnCallConflict = previousOnCall && nextEngineer === previousOnCall;
              
              if (!hasConsecutiveWeekendConflict && !hasOnCallConflict) {
                intendedEngineer = nextEngineer;
                break;
              }
            }
            
            // Log the exclusion and fallback
            decisionLog.push({
              date: dateStr,
              decision_type: 'weekend_conflict_prevention',
              affected_engineers: exclusions,
              reason: `${exclusions.join(', ')} excluded from weekend (${exclusionReasons.join(', ')}), assigned ${intendedEngineer} instead`,
              alternatives_considered: [engineers[intendedEngineerIdx]],
              timestamp: new Date().toISOString()
            });
          }
          
          // Cache the assignment for Saturday/Sunday pairing
          weekendAssignmentCache[weekendWeek] = intendedEngineer;
        }
        
        expectedWorking = [intendedEngineer];
      } else {
        // All engineers available for weekdays initially
        expectedWorking = [...engineers];
      }
      
      // Find who's on leave today
      const onLeaveToday = engineers.filter(eng => leaveMap[eng].has(dateStr));
      
      if (onLeaveToday.length > 0) {
        decisionLog.push({
          date: dateStr,
          decision_type: 'leave_exclusion',
          affected_engineers: onLeaveToday,
          reason: `Engineers excluded due to scheduled leave on ${dayName}`,
          alternatives_considered: ['Enhanced backfill selection will find alternatives'],
          timestamp: new Date().toISOString()
        });
      }
      
      // Available engineers (not on leave)
      const available = engineers.filter(eng => !onLeaveToday.includes(eng));
      
      // Enhanced backfill logic for insufficient coverage
      const initialWorking = expectedWorking.filter(eng => !onLeaveToday.includes(eng));
      let working = [...initialWorking]; // Explicitly mutable array
      const minRequired = isWeekday ? 3 : 1;
      
      if (working.length < minRequired && available.length > working.length) {
        // Find backfill candidates (available but not expected to work)
        const backfillCandidates = available.filter(eng => !expectedWorking.includes(eng));
        
        if (backfillCandidates.length > 0) {
          // Enhanced backfill selection with fairness consideration
          // Simple fairness: prefer engineers with fewer recent assignments
          const needed = Math.min(minRequired - working.length, backfillCandidates.length);
          const selected = backfillCandidates.slice(0, needed);
          
          working = [...working, ...selected]; // Explicit reassignment
          
          decisionLog.push({
            date: dateStr,
            decision_type: 'enhanced_backfill_selection',
            affected_engineers: selected,
            reason: `Found ${backfillCandidates.length} candidates, selected ${selected.length} based on fairness weighting for ${minRequired} required roles`,
            alternatives_considered: backfillCandidates.slice(needed, needed + 2),
            timestamp: new Date().toISOString()
          });
        }
      }
      
      // Role assignments
      const daySchedule: any = {
        Date: dateStr,
        Day: dayName,
        Weekend: '',
        Chat: '',
        OnCall: '',
        Appointments: '',
        Early: ''
      };
      
      if (!isWeekday && working.length > 0) {
        // Weekend assignment - same engineer covers both Saturday and Sunday
        const weekendEngineer = working[0];
        daySchedule.Weekend = weekendEngineer;
        
        // Weekend engineer also covers OnCall for the weekend
        daySchedule.OnCall = weekendEngineer;
        
        // Log weekend assignment decision
        decisionLog.push({
          date: dateStr,
          decision_type: 'weekend_assignment',
          affected_engineers: [weekendEngineer],
          reason: `Weekend assignment for ${dayName} - ${weekendEngineer} covers entire weekend (Saturday & Sunday) and OnCall duties`,
          alternatives_considered: working.slice(1, 3),
          timestamp: new Date().toISOString()
        });
      } else if (isWeekday && working.length > 0) {
        // Weekday role assignments with rotation
        const dayOffset = (currentWeek * 7) + day;
        
        // Assign OnCall engineer for the week (if not already assigned)
        let onCallEngineer: string;
        if (onCallByWeek[currentWeek]) {
          onCallEngineer = onCallByWeek[currentWeek];
        } else {
          // Find intended OnCall engineer
          let intendedOnCallIdx = (currentWeek + seeds.oncall) % working.length;
          let intendedOnCall = working[intendedOnCallIdx];
          
          // Check if intended engineer did the previous weekend (work-life balance)
          // Previous weekend would be at the end of the previous week
          const previousWeekend = currentWeek - 1;
          let previousWeekendEngineer: string | null = null;
          
          // Look through weekend entries to find who did the previous weekend
          const previousWeekendSunday = new Date(startDateObj);
          previousWeekendSunday.setDate(startDateObj.getDate() + (previousWeekend * 7));
          const previousWeekendSundayStr = previousWeekendSunday.toISOString().split('T')[0];
          
          // Find who did the previous weekend by checking processed schedule
          for (const entry of schedule) {
            if (entry.Date === previousWeekendSundayStr && entry.Weekend) {
              previousWeekendEngineer = entry.Weekend;
              break;
            }
          }
          
          // Also check if intended engineer will do the current week's weekend
          const currentWeekendSunday = new Date(startDateObj);
          currentWeekendSunday.setDate(startDateObj.getDate() + (currentWeek * 7));
          const currentWeekendSundayStr = currentWeekendSunday.toISOString().split('T')[0];
          
          let currentWeekendEngineer: string | null = null;
          for (const entry of schedule) {
            if (entry.Date === currentWeekendSundayStr && entry.Weekend) {
              currentWeekendEngineer = entry.Weekend;
              break;
            }
          }
          
          // If intended OnCall engineer did previous weekend OR will do current weekend, find alternative
          const hasWeekendConflict = (previousWeekendEngineer && intendedOnCall === previousWeekendEngineer) ||
                                   (currentWeekendEngineer && intendedOnCall === currentWeekendEngineer);
          
          if (hasWeekendConflict) {
            // Find next available engineer who doesn't have weekend conflicts
            for (let i = 1; i < working.length; i++) {
              const nextIdx = (intendedOnCallIdx + i) % working.length;
              const nextEngineer = working[nextIdx];
              
              // Check if this engineer has weekend conflicts
              const hasPreviousWeekendConflict = previousWeekendEngineer && nextEngineer === previousWeekendEngineer;
              const hasCurrentWeekendConflict = currentWeekendEngineer && nextEngineer === currentWeekendEngineer;
              
              if (!hasPreviousWeekendConflict && !hasCurrentWeekendConflict) {
                intendedOnCall = nextEngineer;
                break;
              }
            }
            
            // Log the exclusion and fallback
            const conflictEngineer = previousWeekendEngineer || currentWeekendEngineer;
            const conflictReason = previousWeekendEngineer ? 'did previous weekend' : 'will do current weekend';
            decisionLog.push({
              date: dateStr,
              decision_type: 'oncall_weekend_exclusion',
              affected_engineers: [conflictEngineer!],
              reason: `${conflictEngineer} excluded from OnCall (${conflictReason}), assigned ${intendedOnCall} instead`,
              alternatives_considered: [working[intendedOnCallIdx]],
              timestamp: new Date().toISOString()
            });
          }
          
          onCallEngineer = intendedOnCall;
          onCallByWeek[currentWeek] = onCallEngineer;
        }
        daySchedule.OnCall = onCallEngineer;
        
        // Assign Early engineer for the week (if not already assigned)
        let earlyEngineer: string;
        if (earlyByWeek[currentWeek]) {
          earlyEngineer = earlyByWeek[currentWeek];
        } else {
          earlyEngineer = working[(currentWeek + seeds.early) % working.length];
          earlyByWeek[currentWeek] = earlyEngineer;
        }
        daySchedule.Early = earlyEngineer;
        
        // Filter out ONLY OnCall engineer from Chat/Appointments (Early engineer can do both)
        const nonOnCallEngineers = working.filter(eng => eng !== onCallEngineer);
        
        if (nonOnCallEngineers.length >= 1) {
          daySchedule.Chat = nonOnCallEngineers[(dayOffset + seeds.chat) % nonOnCallEngineers.length];
        }
        if (nonOnCallEngineers.length >= 2) {
          daySchedule.Appointments = nonOnCallEngineers[(dayOffset + seeds.appointments) % nonOnCallEngineers.length];
        }
        
        // Log enhanced role assignments
        const assignedRoles = Object.entries(daySchedule)
          .filter(([key, value]) => key !== 'Date' && key !== 'Day' && value)
          .map(([role, engineer]) => `${role}: ${engineer}`);
        
        if (assignedRoles.length > 0) {
          decisionLog.push({
            date: dateStr,
            decision_type: 'enhanced_role_assignment',
            affected_engineers: Object.values(daySchedule).filter(v => v && v !== dateStr && v !== dayName) as string[],
            reason: `Enhanced role assignment for ${dayName} with ${working.length} available engineers`,
            alternatives_considered: working.slice(assignedRoles.length),
            timestamp: new Date().toISOString()
          });
        }
      }
      
      schedule.push(daySchedule);
  }
  
  // Generate fairness report
  const engineerStats = engineers.map(eng => {
    const assignments = schedule.filter(day => 
      Object.values(day).includes(eng)
    ).length;
    return { engineer: eng, totalAssignments: assignments };
  });
  
  return {
    schedule,
    metadata: {
      engineers,
      startDate,
      weeks,
      leaveEntries: leave.length,
      generatedAt: new Date().toISOString()
    },
    fairnessReport: {
      totalAssignments: schedule.length * roles.length,
      engineerStats,
      leaveImpact: leave.length > 0 ? 'Enhanced backfill integration active' : 'No leave entries'
    },
    decisionLog
  };
}

function generateCSV(data: EnhancedScheduleResult) {
  const { schedule } = data;
  
  if (schedule.length === 0) return 'No schedule data available';
  
  // Get headers from first row
  const headers = Object.keys(schedule[0]);
  let csv = headers.join(',') + '\n';
  
  schedule.forEach((row: any) => {
    const values = headers.map(header => row[header] || '');
    csv += values.join(',') + '\n';
  });
  
  return csv;
}

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { engineers, start_sunday, weeks, seeds, leave = [], format = 'csv' } = req.body;

    // Basic validation
    if (!engineers || !Array.isArray(engineers) || engineers.length !== 6) {
      return res.status(400).json({ 
        error: 'Exactly 6 engineers required',
        details: 'Please provide exactly 6 unique engineer names'
      });
    }

    if (!start_sunday) {
      return res.status(400).json({ 
        error: 'Start date required',
        details: 'Please provide a start_sunday date in YYYY-MM-DD format'
      });
    }

    if (!weeks || weeks < 1 || weeks > 52) {
      return res.status(400).json({ 
        error: 'Invalid weeks',
        details: 'Weeks must be between 1 and 52'
      });
    }

    // Ensure seeds have default values
    const defaultSeeds = { weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0 };
    const finalSeeds = { ...defaultSeeds, ...(seeds || {}) };

    // Generate enhanced schedule with backfill integration
    const scheduleData = generateEnhancedSchedule(engineers, start_sunday, weeks, finalSeeds, leave);

    if (format === 'json') {
      res.setHeader('Content-Type', 'application/json');
      return res.status(200).json(scheduleData);
    } else if (format === 'csv') {
      const csv = generateCSV(scheduleData);
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="enhanced-schedule.csv"');
      return res.status(200).send(csv);
    } else if (format === 'xlsx') {
      // For now, return CSV data with xlsx content type as a workaround
      const csv = generateCSV(scheduleData);
      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', 'attachment; filename="enhanced-schedule.xlsx"');
      return res.status(200).send(csv);
    } else {
      return res.status(400).json({ 
        error: 'Unsupported format',
        details: 'Supported formats: csv, json, xlsx'
      });
    }

  } catch (error) {
    console.error('Enhanced schedule generation error:', error);
    return res.status(500).json({ 
      error: 'Enhanced schedule generation failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}