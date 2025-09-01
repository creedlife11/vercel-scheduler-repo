import { NextApiRequest, NextApiResponse } from 'next';

// Simple Node.js implementation of the scheduler
function generateSchedule(engineers: string[], startDate: string, weeks: number, seeds: any) {
  const schedule = [];
  const roles = ['weekend', 'chat', 'oncall', 'appointments', 'early'];
  
  // Simple round-robin assignment with seed offsets
  for (let week = 0; week < weeks; week++) {
    const weekSchedule: any = { week: week + 1 };
    
    roles.forEach((role, roleIndex) => {
      const seedOffset = seeds[role] || 0;
      const assigneeIndex = (week + seedOffset + roleIndex) % engineers.length;
      weekSchedule[role] = engineers[assigneeIndex];
    });
    
    schedule.push(weekSchedule);
  }
  
  return {
    schedule,
    metadata: {
      engineers,
      startDate,
      weeks,
      generatedAt: new Date().toISOString()
    },
    fairnessReport: {
      totalAssignments: schedule.length * roles.length,
      engineerStats: engineers.map(eng => ({
        engineer: eng,
        totalAssignments: schedule.filter(week => 
          roles.some(role => week[role] === eng)
        ).length
      }))
    }
  };
}

function generateCSV(data: any) {
  const { schedule } = data;
  const roles = ['weekend', 'chat', 'oncall', 'appointments', 'early'];
  
  let csv = 'Week,' + roles.join(',') + '\n';
  
  schedule.forEach((week: any) => {
    const row = [week.week, ...roles.map(role => week[role])];
    csv += row.join(',') + '\n';
  });
  
  return csv;
}

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { engineers, start_sunday, weeks, seeds, format = 'csv' } = req.body;

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

    // Generate the schedule
    const scheduleData = generateSchedule(engineers, start_sunday, weeks, seeds || {});

    if (format === 'json') {
      res.setHeader('Content-Type', 'application/json');
      return res.status(200).json(scheduleData);
    } else if (format === 'csv') {
      const csv = generateCSV(scheduleData);
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="schedule.csv"');
      return res.status(200).send(csv);
    } else {
      return res.status(400).json({ 
        error: 'Unsupported format',
        details: 'Supported formats: csv, json'
      });
    }

  } catch (error) {
    console.error('Schedule generation error:', error);
    return res.status(500).json({ 
      error: 'Schedule generation failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}