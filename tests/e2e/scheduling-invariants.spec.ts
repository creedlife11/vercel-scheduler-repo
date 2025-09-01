import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';

// Helper function to get a valid Sunday date
function getNextSunday(): string {
  const today = new Date();
  const daysUntilSunday = (7 - today.getDay()) % 7;
  const nextSunday = new Date(today);
  nextSunday.setDate(today.getDate() + daysUntilSunday);
  return nextSunday.toISOString().split('T')[0];
}

// Helper function to generate schedule and return CSV content
async function generateScheduleCSV(page: Page, weeks: number = 8, engineers?: string[]): Promise<string> {
  const engineerList = engineers || ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
  
  await page.fill('textarea[placeholder*="Engineer"]', engineerList.join(', '));
  await page.fill('input[type="date"]', getNextSunday());
  await page.fill('input[type="number"][min="1"]', weeks.toString());
  
  await page.check('input[type="radio"][value="csv"]');
  
  await page.click('button:has-text("Generate Schedule")');
  await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
  
  await page.click('button:has-text("View Artifacts")');
  await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
  
  const downloadPromise = page.waitForDownload();
  await page.click('button:has-text("Download CSV")');
  const download = await downloadPromise;
  
  const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
  await download.saveAs(downloadPath);
  
  const content = fs.readFileSync(downloadPath, 'utf-8');
  fs.unlinkSync(downloadPath); // Clean up immediately
  
  return content;
}

// Parse CSV and return structured data
function parseScheduleCSV(content: string): any[] {
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true
  });
}

// Validate that no oncall assignments occur on weekends (Requirement 2.1)
function validateNoWeekendOncall(records: any[]): { isValid: boolean; violations: string[] } {
  const violations: string[] = [];
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const date = new Date(record.Date);
    const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
    
    // Check if it's a weekend day and has oncall assignment
    if ((dayOfWeek === 0 || dayOfWeek === 6) && record.OnCall && record.OnCall.trim()) {
      violations.push(`${record.Date} (${record.Day}): OnCall="${record.OnCall}"`);
    }
  }
  
  return { isValid: violations.length === 0, violations };
}

// Validate status field integrity (Requirement 2.2)
function validateStatusFieldIntegrity(records: any[], knownEngineers: string[]): { isValid: boolean; violations: string[] } {
  const violations: string[] = [];
  const validStatuses = ['WORK', 'OFF', 'LEAVE', ''];
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2; // Account for header
    
    for (let j = 1; j <= 6; j++) {
      const statusField = `Status ${j}`;
      const statusValue = record[statusField];
      
      if (statusValue && statusValue.trim()) {
        // Check if status contains engineer name (common bug)
        if (knownEngineers.includes(statusValue)) {
          violations.push(`Row ${rowNum}: Status field "${statusField}" contains engineer name "${statusValue}"`);
        }
        // Check if status is invalid
        else if (!validStatuses.includes(statusValue)) {
          violations.push(`Row ${rowNum}: Invalid status "${statusValue}" in field "${statusField}"`);
        }
      }
    }
  }
  
  return { isValid: violations.length === 0, violations };
}

// Validate engineer field integrity (Requirement 2.3)
function validateEngineerFieldIntegrity(records: any[], knownEngineers: string[]): { isValid: boolean; violations: string[] } {
  const violations: string[] = [];
  const validStatuses = ['WORK', 'OFF', 'LEAVE', ''];
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2; // Account for header
    
    for (let j = 1; j <= 6; j++) {
      const engineerField = `${j}) Engineer`;
      const engineerValue = record[engineerField];
      
      if (engineerValue && engineerValue.trim()) {
        // Check if engineer field contains time string
        if (engineerValue.includes(':')) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains time string "${engineerValue}"`);
        }
        // Check if engineer field contains status
        else if (validStatuses.includes(engineerValue)) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains status "${engineerValue}"`);
        }
        // Check if engineer is unknown
        else if (!knownEngineers.includes(engineerValue)) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains unknown engineer "${engineerValue}"`);
        }
      }
    }
  }
  
  return { isValid: violations.length === 0, violations };
}

// Validate weekend coverage patterns (Week A/B alternation)
function validateWeekendCoveragePatterns(records: any[]): { isValid: boolean; violations: string[] } {
  const violations: string[] = [];
  const weekendRecords = records.filter(record => {
    const date = new Date(record.Date);
    const dayOfWeek = date.getDay();
    return dayOfWeek === 0 || dayOfWeek === 6; // Sunday or Saturday
  });
  
  // Group weekend records by week
  const weekendsByWeek: { [key: number]: any[] } = {};
  
  for (const record of weekendRecords) {
    const weekIndex = parseInt(record.WeekIndex);
    if (!isNaN(weekIndex)) {
      if (!weekendsByWeek[weekIndex]) {
        weekendsByWeek[weekIndex] = [];
      }
      weekendsByWeek[weekIndex].push(record);
    }
  }
  
  // Validate that weekend assignments are consistent within each week
  for (const [weekIndex, weekRecords] of Object.entries(weekendsByWeek)) {
    const weekNum = parseInt(weekIndex);
    
    // Check that all weekend days in the same week have consistent assignments
    const weekendEngineers = new Set<string>();
    
    for (const record of weekRecords) {
      // Collect all engineers assigned to weekend roles
      const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
      
      for (const field of roleFields) {
        if (record[field] && record[field].trim()) {
          weekendEngineers.add(record[field]);
        }
      }
    }
    
    // Weekend coverage should follow some pattern (this is a simplified check)
    // In practice, you'd validate against specific business rules
    if (weekendEngineers.size === 0) {
      violations.push(`Week ${weekNum}: No weekend coverage assigned`);
    }
  }
  
  return { isValid: violations.length === 0, violations };
}

// Validate role assignment fairness
function validateRoleAssignmentFairness(records: any[], knownEngineers: string[]): { isValid: boolean; violations: string[]; stats: any } {
  const violations: string[] = [];
  const roleStats: { [engineer: string]: { [role: string]: number } } = {};
  
  // Initialize stats for all engineers
  for (const engineer of knownEngineers) {
    roleStats[engineer] = {
      oncall: 0,
      weekend: 0,
      early: 0,
      chat: 0,
      appointments: 0
    };
  }
  
  // Count role assignments
  for (const record of records) {
    const date = new Date(record.Date);
    const isWeekend = date.getDay() === 0 || date.getDay() === 6;
    
    // Count oncall assignments
    if (record.OnCall && record.OnCall.trim()) {
      const engineer = record.OnCall.trim();
      if (roleStats[engineer]) {
        roleStats[engineer].oncall++;
      }
    }
    
    // Count weekend assignments
    if (isWeekend) {
      const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
      const assignedEngineers = new Set<string>();
      
      for (const field of roleFields) {
        if (record[field] && record[field].trim()) {
          assignedEngineers.add(record[field].trim());
        }
      }
      
      for (const engineer of assignedEngineers) {
        if (roleStats[engineer]) {
          roleStats[engineer].weekend++;
        }
      }
    }
    
    // Count early shift assignments
    if (record.Early1 && record.Early1.trim()) {
      const engineer = record.Early1.trim();
      if (roleStats[engineer]) {
        roleStats[engineer].early++;
      }
    }
    if (record.Early2 && record.Early2.trim()) {
      const engineer = record.Early2.trim();
      if (roleStats[engineer]) {
        roleStats[engineer].early++;
      }
    }
    
    // Count chat assignments
    if (record.Chat && record.Chat.trim()) {
      const engineer = record.Chat.trim();
      if (roleStats[engineer]) {
        roleStats[engineer].chat++;
      }
    }
    
    // Count appointment assignments
    if (record.Appointments && record.Appointments.trim()) {
      const engineer = record.Appointments.trim();
      if (roleStats[engineer]) {
        roleStats[engineer].appointments++;
      }
    }
  }
  
  // Check for extreme imbalances (more than 50% difference from average)
  for (const role of ['oncall', 'weekend', 'early', 'chat', 'appointments']) {
    const counts = knownEngineers.map(eng => roleStats[eng][role]);
    const total = counts.reduce((sum, count) => sum + count, 0);
    const average = total / knownEngineers.length;
    const max = Math.max(...counts);
    const min = Math.min(...counts);
    
    if (total > 0 && (max - min) > average * 0.5) {
      const maxEngineer = knownEngineers.find(eng => roleStats[eng][role] === max);
      const minEngineer = knownEngineers.find(eng => roleStats[eng][role] === min);
      violations.push(`Role "${role}" imbalance: ${maxEngineer}=${max}, ${minEngineer}=${min} (avg=${average.toFixed(1)})`);
    }
  }
  
  return { isValid: violations.length === 0, violations, stats: roleStats };
}

test.describe('Scheduling Invariants Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Team Scheduler');
  });

  test('should enforce no oncall assignments on weekends (Requirement 2.1)', async ({ page }) => {
    const csvContent = await generateScheduleCSV(page, 8);
    const records = parseScheduleCSV(csvContent);
    
    const validation = validateNoWeekendOncall(records);
    
    if (!validation.isValid) {
      console.error('Weekend OnCall Violations:', validation.violations);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
  });

  test('should maintain status field integrity across all rows (Requirement 2.2)', async ({ page }) => {
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const csvContent = await generateScheduleCSV(page, 6, knownEngineers);
    const records = parseScheduleCSV(csvContent);
    
    const validation = validateStatusFieldIntegrity(records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Status Field Violations:', validation.violations);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Additional check: verify all status values are valid
    const allStatusValues = new Set<string>();
    for (const record of records) {
      for (let j = 1; j <= 6; j++) {
        const statusValue = record[`Status ${j}`];
        if (statusValue && statusValue.trim()) {
          allStatusValues.add(statusValue);
        }
      }
    }
    
    const validStatuses = new Set(['WORK', 'OFF', 'LEAVE']);
    for (const status of allStatusValues) {
      expect(validStatuses.has(status)).toBe(true);
    }
  });

  test('should maintain engineer field integrity across all rows (Requirement 2.3)', async ({ page }) => {
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const csvContent = await generateScheduleCSV(page, 6, knownEngineers);
    const records = parseScheduleCSV(csvContent);
    
    const validation = validateEngineerFieldIntegrity(records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Engineer Field Violations:', validation.violations);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Additional check: verify all engineer names are from known list
    const allEngineerValues = new Set<string>();
    for (const record of records) {
      for (let j = 1; j <= 6; j++) {
        const engineerValue = record[`${j}) Engineer`];
        if (engineerValue && engineerValue.trim()) {
          allEngineerValues.add(engineerValue);
        }
      }
    }
    
    for (const engineer of allEngineerValues) {
      expect(knownEngineers).toContain(engineer);
    }
  });

  test('should validate weekend coverage patterns', async ({ page }) => {
    const csvContent = await generateScheduleCSV(page, 8);
    const records = parseScheduleCSV(csvContent);
    
    const validation = validateWeekendCoveragePatterns(records);
    
    if (!validation.isValid) {
      console.error('Weekend Coverage Violations:', validation.violations);
    }
    
    expect(validation.isValid).toBe(true);
    
    // Verify weekend records exist
    const weekendRecords = records.filter(record => {
      const date = new Date(record.Date);
      const dayOfWeek = date.getDay();
      return dayOfWeek === 0 || dayOfWeek === 6;
    });
    
    expect(weekendRecords.length).toBeGreaterThan(0);
    expect(weekendRecords.length).toBe(16); // 8 weeks * 2 weekend days
  });

  test('should maintain reasonable role assignment fairness', async ({ page }) => {
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const csvContent = await generateScheduleCSV(page, 12, knownEngineers); // Longer schedule for better fairness analysis
    const records = parseScheduleCSV(csvContent);
    
    const validation = validateRoleAssignmentFairness(records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Role Assignment Fairness Violations:', validation.violations);
      console.log('Role Assignment Stats:', validation.stats);
    }
    
    // Allow some imbalance but not extreme
    expect(validation.violations.length).toBeLessThanOrEqual(2);
    
    // Verify all engineers get some assignments
    for (const engineer of knownEngineers) {
      const totalAssignments = Object.values(validation.stats[engineer]).reduce((sum: number, count: number) => sum + count, 0);
      expect(totalAssignments).toBeGreaterThan(0);
    }
  });

  test('should validate date continuity and progression', async ({ page }) => {
    const csvContent = await generateScheduleCSV(page, 4);
    const records = parseScheduleCSV(csvContent);
    
    expect(records.length).toBe(28); // 4 weeks * 7 days
    
    // Verify dates are continuous
    const dates = records.map(record => record.Date).sort();
    
    for (let i = 1; i < dates.length; i++) {
      const prevDate = new Date(dates[i - 1]);
      const currDate = new Date(dates[i]);
      const daysDiff = Math.round((currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));
      
      expect(daysDiff).toBe(1); // Each date should be exactly one day after the previous
    }
    
    // Verify week index progression
    let lastWeekIndex = -1;
    for (const record of records) {
      const weekIndex = parseInt(record.WeekIndex);
      expect(weekIndex).toBeGreaterThanOrEqual(lastWeekIndex);
      
      // Week index should only increment on Sundays (except first record)
      const date = new Date(record.Date);
      if (date.getDay() === 0 && lastWeekIndex >= 0) { // Sunday
        expect(weekIndex).toBeGreaterThan(lastWeekIndex);
      }
      
      lastWeekIndex = weekIndex;
    }
  });

  test('should validate engineer assignment consistency within days', async ({ page }) => {
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const csvContent = await generateScheduleCSV(page, 4, knownEngineers);
    const records = parseScheduleCSV(csvContent);
    
    const violations: string[] = [];
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const rowNum = i + 2;
      
      // Get all role assignments for this day
      const roleAssignments = [
        record.Early1,
        record.Early2,
        record.Chat,
        record.OnCall,
        record.Appointments
      ].filter(assignment => assignment && assignment.trim());
      
      // Get all engineers listed for this day
      const listedEngineers = [];
      for (let j = 1; j <= 6; j++) {
        const engineer = record[`${j}) Engineer`];
        if (engineer && engineer.trim()) {
          listedEngineers.push(engineer);
        }
      }
      
      // Verify all assigned engineers are in the engineer list for that day
      for (const assignment of roleAssignments) {
        if (!listedEngineers.includes(assignment)) {
          violations.push(`Row ${rowNum}: Engineer "${assignment}" assigned to role but not listed in engineer columns`);
        }
      }
      
      // Verify no engineer is assigned to multiple conflicting roles
      const assignmentCounts: { [engineer: string]: string[] } = {};
      
      if (record.Early1) assignmentCounts[record.Early1] = (assignmentCounts[record.Early1] || []).concat(['Early1']);
      if (record.Early2) assignmentCounts[record.Early2] = (assignmentCounts[record.Early2] || []).concat(['Early2']);
      if (record.Chat) assignmentCounts[record.Chat] = (assignmentCounts[record.Chat] || []).concat(['Chat']);
      if (record.OnCall) assignmentCounts[record.OnCall] = (assignmentCounts[record.OnCall] || []).concat(['OnCall']);
      if (record.Appointments) assignmentCounts[record.Appointments] = (assignmentCounts[record.Appointments] || []).concat(['Appointments']);
      
      for (const [engineer, roles] of Object.entries(assignmentCounts)) {
        if (roles.length > 1) {
          // Multiple role assignments might be valid depending on business rules
          // For now, just log for review
          console.log(`Row ${rowNum}: Engineer "${engineer}" assigned to multiple roles: ${roles.join(', ')}`);
        }
      }
    }
    
    expect(violations).toHaveLength(0);
    if (violations.length > 0) {
      console.error('Engineer Assignment Consistency Violations:', violations);
    }
  });

  test('should validate leave handling integrity', async ({ page }) => {
    // This test would require adding leave entries and verifying they're respected
    // For now, we'll test the basic structure and add a placeholder
    
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const csvContent = await generateScheduleCSV(page, 2, knownEngineers);
    const records = parseScheduleCSV(csvContent);
    
    const violations: string[] = [];
    
    // Check that engineers marked as LEAVE are not assigned to roles
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const rowNum = i + 2;
      
      // Get engineers on leave for this day
      const engineersOnLeave: string[] = [];
      for (let j = 1; j <= 6; j++) {
        const engineer = record[`${j}) Engineer`];
        const status = record[`Status ${j}`];
        
        if (engineer && status === 'LEAVE') {
          engineersOnLeave.push(engineer);
        }
      }
      
      // Check that engineers on leave are not assigned to roles
      const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
      
      for (const field of roleFields) {
        const assignedEngineer = record[field];
        if (assignedEngineer && engineersOnLeave.includes(assignedEngineer)) {
          violations.push(`Row ${rowNum}: Engineer "${assignedEngineer}" assigned to ${field} but marked as LEAVE`);
        }
      }
    }
    
    expect(violations).toHaveLength(0);
    if (violations.length > 0) {
      console.error('Leave Handling Violations:', violations);
    }
  });
});

// Create downloads directory if it doesn't exist
test.beforeAll(async () => {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }
});