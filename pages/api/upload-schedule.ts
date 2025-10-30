import { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import fs from 'fs';
import Papa from 'papaparse';

export const config = {
  api: {
    bodyParser: false,
  },
};

interface ScheduleEntry {
  Date: string;
  Day: string;
  Weekend?: string;
  Chat?: string;
  OnCall?: string;
  Appointments?: string;
  Early?: string;
}

interface ScheduleAnalysis {
  totalEntries: number;
  dateRange: {
    start: string;
    end: string;
  };
  engineers: string[];
  roleStats: {
    [engineer: string]: {
      weekends: number;
      onCall: number;
      early: number;
      chat: number;
      appointments: number;
      total: number;
    };
  };
  conflicts: string[];
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const form = formidable({
      maxFileSize: 10 * 1024 * 1024, // 10MB limit
      filter: ({ mimetype }) => {
        return mimetype === 'text/csv' || mimetype === 'application/vnd.ms-excel';
      }
    });

    const [fields, files] = await form.parse(req);
    const file = Array.isArray(files.file) ? files.file[0] : files.file;

    if (!file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Read the CSV file
    const csvContent = fs.readFileSync(file.filepath, 'utf8');
    
    // Parse CSV
    const parseResult = Papa.parse(csvContent, {
      header: true,
      skipEmptyLines: true
    });

    if (parseResult.errors.length > 0) {
      return res.status(400).json({ 
        error: 'CSV parsing error', 
        details: parseResult.errors 
      });
    }

    const scheduleData = parseResult.data as ScheduleEntry[];
    
    // Validate required columns
    const requiredColumns = ['Date', 'Day'];
    const firstRow = scheduleData[0];
    if (!firstRow || !requiredColumns.every(col => col in firstRow)) {
      return res.status(400).json({ 
        error: 'Invalid CSV format. Required columns: Date, Day' 
      });
    }

    // Analyze the schedule
    const analysis = analyzeSchedule(scheduleData);

    // Clean up uploaded file
    fs.unlinkSync(file.filepath);

    res.status(200).json({
      success: true,
      schedule: scheduleData,
      analysis
    });

  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: 'Failed to process file',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}

function analyzeSchedule(scheduleData: ScheduleEntry[]): ScheduleAnalysis {
  const engineers = new Set<string>();
  const roleStats: { [engineer: string]: any } = {};
  const conflicts: string[] = [];

  // Extract all engineers and initialize stats
  scheduleData.forEach(entry => {
    [entry.Weekend, entry.Chat, entry.OnCall, entry.Appointments, entry.Early]
      .filter(Boolean)
      .forEach(engineer => {
        if (engineer) {
          engineers.add(engineer);
          if (!roleStats[engineer]) {
            roleStats[engineer] = {
              weekends: 0,
              onCall: 0,
              early: 0,
              chat: 0,
              appointments: 0,
              total: 0
            };
          }
        }
      });
  });

  // Calculate role statistics
  scheduleData.forEach(entry => {
    if (entry.Weekend) {
      roleStats[entry.Weekend].weekends++;
      roleStats[entry.Weekend].total++;
    }
    if (entry.OnCall) {
      roleStats[entry.OnCall].onCall++;
      roleStats[entry.OnCall].total++;
    }
    if (entry.Early) {
      roleStats[entry.Early].early++;
      roleStats[entry.Early].total++;
    }
    if (entry.Chat) {
      roleStats[entry.Chat].chat++;
      roleStats[entry.Chat].total++;
    }
    if (entry.Appointments) {
      roleStats[entry.Appointments].appointments++;
      roleStats[entry.Appointments].total++;
    }
  });

  // Check for conflicts (basic validation)
  const weekendsByWeek: { [week: string]: string } = {};
  scheduleData.forEach(entry => {
    const date = new Date(entry.Date);
    if (date.getDay() === 6) { // Saturday
      const weekKey = `${date.getFullYear()}-W${Math.ceil(date.getDate() / 7)}`;
      if (entry.Weekend) {
        if (weekendsByWeek[weekKey] && weekendsByWeek[weekKey] !== entry.Weekend) {
          conflicts.push(`Weekend conflict in ${weekKey}: ${weekendsByWeek[weekKey]} vs ${entry.Weekend}`);
        }
        weekendsByWeek[weekKey] = entry.Weekend;
      }
    }
  });

  // Get date range
  const dates = scheduleData.map(entry => new Date(entry.Date)).sort((a, b) => a.getTime() - b.getTime());
  const dateRange = {
    start: dates[0]?.toISOString().split('T')[0] || '',
    end: dates[dates.length - 1]?.toISOString().split('T')[0] || ''
  };

  return {
    totalEntries: scheduleData.length,
    dateRange,
    engineers: Array.from(engineers).sort(),
    roleStats,
    conflicts
  };
}