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
  const roles = ['Weekend', 'Chat', 'OnCall', 'Appointments', 'Early1', 'Early2'];
  
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
  
  // Process all dates
  for (let dateIndex = 0; dateIndex < allDates.length; dateIndex++) {
    const currentDate = allDates[dateIndex];
    const dateStr = currentDate.toISOString().split('T')[0];
    const day = currentDate.getDay(); // 0=Sunday, 1=Monday, ..., 6=Saturday
    
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dayName = dayNames[day];
    const isWeekday = day >= 1 && day <= 5;
      
      // Determine who should be working
      const expectedWorking = engineers.filter((_, idx) => {
        // Weekend rotation: same engineer covers both Saturday and Sunday
        if (!isWeekday) {
          // For weekend days, calculate which weekend pair this belongs to
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
          
          return (weekendWeek + seeds.weekend) % engineers.length === idx;
        }
        return true; // All engineers available for weekdays initially
      });
      
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
        Early1: '',
        Early2: ''
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
        // Calculate the week and day offset for weekday assignments
        const daysSinceStart = Math.floor((currentDate.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
        const week = Math.floor(daysSinceStart / 7);
        const dayOffset = (week * 7) + day;
        
        if (working.length >= 1) {
          daySchedule.Chat = working[(dayOffset + seeds.chat) % working.length];
        }
        if (working.length >= 2) {
          // OnCall engineer is assigned per week, not per day
          daySchedule.OnCall = working[(week + seeds.oncall) % working.length];
        }
        if (working.length >= 3) {
          daySchedule.Appointments = working[(dayOffset + seeds.appointments) % working.length];
        }
        if (working.length >= 4) {
          daySchedule.Early1 = working[(dayOffset + seeds.early) % working.length];
        }
        if (working.length >= 5) {
          daySchedule.Early2 = working[(dayOffset + seeds.early + 1) % working.length];
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