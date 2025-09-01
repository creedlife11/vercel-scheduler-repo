import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';
import {
  validateColumnConsistency,
  validateStatusFieldIntegrity,
  validateEngineerFieldIntegrity,
  validateNoWeekendOncall,
  validateRoleAssignmentConsistency,
  validateDateContinuity,
  validateAllInvariants,
  generateValidationReport,
  type ScheduleRecord
} from './utils/invariant-validators';

// Helper function to get a valid Sunday date
function getNextSunday(): string {
  const today = new Date();
  const daysUntilSunday = (7 - today.getDay()) % 7;
  const nextSunday = new Date(today);
  nextSunday.setDate(today.getDate() + daysUntilSunday);
  return nextSunday.toISOString().split('T')[0];
}

// Helper function to fill form and generate schedule
async function generateScheduleAndDownload(page: Page, format: 'csv' | 'xlsx' | 'json' = 'csv'): Promise<string> {
  // Fill form with valid data
  await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
  await page.fill('input[type="date"]', getNextSunday());
  await page.fill('input[type="number"][min="1"]', '8'); // 8 weeks for more comprehensive testing
  
  // Select format
  await page.check(`input[type="radio"][value="${format}"]`);
  
  // Generate schedule
  await page.click('button:has-text("Generate Schedule")');
  await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
  
  // Open artifact panel and download
  await page.click('button:has-text("View Artifacts")');
  await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
  
  const downloadPromise = page.waitForDownload();
  await page.click(`button:has-text("Download ${format.toUpperCase()}")`);
  const download = await downloadPromise;
  
  // Save file and return path
  const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
  await download.saveAs(downloadPath);
  
  return downloadPath;
}

// Parse CSV and validate structure
function validateCSVInvariants(filePath: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim());
    
    if (lines.length < 2) {
      errors.push('CSV must have at least header and one data row');
      return { isValid: false, errors };
    }
    
    // Parse CSV
    const records = parse(content, {
      columns: true,
      skip_empty_lines: true,
      trim: true
    });
    
    const validStatuses = ['WORK', 'OFF', 'LEAVE', ''];
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    
    // Validate each row
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const rowNum = i + 2; // Account for header row
      
      // Check column count consistency
      const line = lines[i + 1]; // Skip header
      const columnCount = line.split(',').length;
      const headerColumnCount = lines[0].split(',').length;
      
      if (columnCount !== headerColumnCount) {
        errors.push(`Row ${rowNum}: Column count mismatch - has ${columnCount}, expected ${headerColumnCount}`);
      }
      
      // Validate status fields (Requirements 2.1, 2.2)
      for (let j = 1; j <= 6; j++) {
        const statusField = `Status ${j}`;
        const statusValue = record[statusField];
        
        if (statusValue && !validStatuses.includes(statusValue)) {
          // Check if status contains engineer name (common bug)
          if (knownEngineers.includes(statusValue)) {
            errors.push(`Row ${rowNum}: Status field "${statusField}" contains engineer name "${statusValue}" instead of valid status`);
          } else {
            errors.push(`Row ${rowNum}: Invalid status "${statusValue}" in field "${statusField}". Must be one of: ${validStatuses.join(', ')}`);
          }
        }
      }
      
      // Validate engineer fields (Requirement 2.3)
      for (let j = 1; j <= 6; j++) {
        const engineerField = `${j}) Engineer`;
        const engineerValue = record[engineerField];
        
        if (engineerValue && engineerValue.trim()) {
          // Check if engineer field contains time string or status (common bugs)
          if (engineerValue.includes(':')) {
            errors.push(`Row ${rowNum}: Engineer field "${engineerField}" contains time string "${engineerValue}"`);
          } else if (validStatuses.includes(engineerValue)) {
            errors.push(`Row ${rowNum}: Engineer field "${engineerField}" contains status "${engineerValue}" instead of engineer name`);
          } else if (!knownEngineers.includes(engineerValue)) {
            errors.push(`Row ${rowNum}: Engineer field "${engineerField}" contains unknown engineer "${engineerValue}"`);
          }
        }
      }
      
      // Validate date format
      if (record.Date && !/^\d{4}-\d{2}-\d{2}$/.test(record.Date)) {
        errors.push(`Row ${rowNum}: Invalid date format "${record.Date}"`);
      }
      
      // Validate day field
      const validDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      if (record.Day && !validDays.includes(record.Day)) {
        errors.push(`Row ${rowNum}: Invalid day "${record.Day}"`);
      }
      
      // Validate WeekIndex is a number
      if (record.WeekIndex && isNaN(parseInt(record.WeekIndex))) {
        errors.push(`Row ${rowNum}: WeekIndex "${record.WeekIndex}" is not a valid number`);
      }
    }
    
  } catch (error) {
    errors.push(`CSV parsing error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors };
}

// Validate scheduling business rules
function validateSchedulingRules(filePath: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const records = parse(content, {
      columns: true,
      skip_empty_lines: true,
      trim: true
    });
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const rowNum = i + 2;
      const date = new Date(record.Date);
      const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
      
      // Rule: No oncall assignments on weekends (Requirement 2.1)
      if ((dayOfWeek === 0 || dayOfWeek === 6) && record.OnCall && record.OnCall.trim()) {
        errors.push(`Row ${rowNum}: OnCall assignment "${record.OnCall}" found on weekend (${record.Day}, ${record.Date})`);
      }
      
      // Rule: Weekend coverage should follow Week A/B pattern
      if (dayOfWeek === 0 || dayOfWeek === 6) {
        const weekIndex = parseInt(record.WeekIndex);
        if (!isNaN(weekIndex)) {
          // Weekend assignments should be consistent within the same week
          const expectedPattern = weekIndex % 2 === 0 ? 'A' : 'B';
          // This is a simplified check - in practice, you'd validate the actual pattern
        }
      }
      
      // Rule: Early shifts should not be assigned on weekends
      if ((dayOfWeek === 0 || dayOfWeek === 6)) {
        if ((record.Early1 && record.Early1.trim()) || (record.Early2 && record.Early2.trim())) {
          // This might be valid depending on business rules, so just log for review
          console.log(`Info: Early shift assigned on weekend: ${record.Date} (${record.Day})`);
        }
      }
      
      // Rule: Validate that assigned engineers are actually working that day
      const assignedRoles = [record.Early1, record.Early2, record.Chat, record.OnCall, record.Appointments].filter(Boolean);
      
      for (const assignedEngineer of assignedRoles) {
        if (assignedEngineer && assignedEngineer.trim()) {
          // Find this engineer's status for this day
          let engineerStatus = '';
          for (let j = 1; j <= 6; j++) {
            const engineerField = `${j}) Engineer`;
            const statusField = `Status ${j}`;
            
            if (record[engineerField] === assignedEngineer) {
              engineerStatus = record[statusField];
              break;
            }
          }
          
          // Engineer should not be assigned to roles if they're on leave
          if (engineerStatus === 'LEAVE') {
            errors.push(`Row ${rowNum}: Engineer "${assignedEngineer}" assigned to role but marked as LEAVE`);
          }
        }
      }
    }
    
  } catch (error) {
    errors.push(`Scheduling rule validation error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors };
}

test.describe('Schedule Invariant Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Team Scheduler');
  });

  test('should validate CSV column count consistency across all rows', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    const content = fs.readFileSync(filePath, 'utf-8');
    
    const validation = validateColumnConsistency(content);
    
    if (!validation.isValid) {
      console.error('CSV Column Consistency Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should ensure status fields never contain engineer names', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const validation = validateStatusFieldIntegrity(records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Status Field Integrity Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should ensure engineer fields never contain time strings or statuses', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const validation = validateEngineerFieldIntegrity(records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Engineer Field Integrity Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate no oncall assignments on weekends', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const validation = validateNoWeekendOncall(records);
    
    if (!validation.isValid) {
      console.error('Weekend OnCall Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate engineer name consistency across all references', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    const inconsistencyViolations: string[] = [];
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      
      // Check all role assignment fields
      const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
      
      for (const roleField of roleFields) {
        const assignedEngineer = record[roleField];
        
        if (assignedEngineer && assignedEngineer.trim()) {
          if (!knownEngineers.includes(assignedEngineer)) {
            inconsistencyViolations.push(`Row ${i + 2}: Unknown engineer "${assignedEngineer}" in ${roleField}`);
          }
        }
      }
      
      // Check engineer list fields
      for (let j = 1; j <= 6; j++) {
        const engineerField = `${j}) Engineer`;
        const engineerValue = record[engineerField];
        
        if (engineerValue && engineerValue.trim() && !knownEngineers.includes(engineerValue)) {
          inconsistencyViolations.push(`Row ${i + 2}: Unknown engineer "${engineerValue}" in ${engineerField}`);
        }
      }
    }
    
    expect(inconsistencyViolations).toHaveLength(0);
    if (inconsistencyViolations.length > 0) {
      console.error('Engineer Name Inconsistencies:', inconsistencyViolations);
    }
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate date and day consistency', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const dateConsistencyViolations: string[] = [];
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      
      if (record.Date && record.Day) {
        const date = new Date(record.Date);
        const expectedDay = dayNames[date.getDay()];
        
        if (record.Day !== expectedDay) {
          dateConsistencyViolations.push(`Row ${i + 2}: Date ${record.Date} should be ${expectedDay}, but Day field shows ${record.Day}`);
        }
      }
    }
    
    expect(dateConsistencyViolations).toHaveLength(0);
    if (dateConsistencyViolations.length > 0) {
      console.error('Date/Day Consistency Violations:', dateConsistencyViolations);
    }
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate week index progression and date continuity', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const validation = validateDateContinuity(records);
    
    if (!validation.isValid) {
      console.error('Date Continuity Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate role assignment consistency', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    
    const validation = validateRoleAssignmentConsistency(records);
    
    if (!validation.isValid) {
      console.error('Role Assignment Consistency Violations:', validation.violations);
      console.log('Validation Report:', generateValidationReport(validation));
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should pass comprehensive invariant validation', async ({ page }) => {
    const filePath = await generateScheduleAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const records: ScheduleRecord[] = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    
    const validation = validateAllInvariants(content, records, knownEngineers);
    
    if (!validation.isValid) {
      console.error('Comprehensive Validation Failed');
      console.log('Full Validation Report:', generateValidationReport(validation));
    }
    
    // Log warnings even if validation passes
    if (validation.warnings && validation.warnings.length > 0) {
      console.log('Validation Warnings:', validation.warnings);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.violations).toHaveLength(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });
});

// Create downloads directory if it doesn't exist
test.beforeAll(async () => {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }
});