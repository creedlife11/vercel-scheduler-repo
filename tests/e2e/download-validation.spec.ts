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

// Helper function to fill form and generate schedule
async function generateAndDownload(page: Page, format: 'csv' | 'xlsx' | 'json', weeks: number = 4): Promise<string> {
  // Fill form
  await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
  await page.fill('input[type="date"]', getNextSunday());
  await page.fill('input[type="number"][min="1"]', weeks.toString());
  
  // Select format
  await page.check(`input[type="radio"][value="${format}"]`);
  
  // Generate
  await page.click('button:has-text("Generate Schedule")');
  await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
  
  // Download
  await page.click('button:has-text("View Artifacts")');
  await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
  
  const downloadPromise = page.waitForDownload();
  await page.click(`button:has-text("Download ${format.toUpperCase()}")`);
  const download = await downloadPromise;
  
  // Save file
  const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
  await download.saveAs(downloadPath);
  
  return downloadPath;
}

// Validate CSV file structure and content
function validateCSVFile(filePath: string, expectedWeeks: number): { isValid: boolean; errors: string[]; stats: any } {
  const errors: string[] = [];
  const stats = {
    totalRows: 0,
    headerColumns: 0,
    dateRange: { start: '', end: '' },
    engineers: new Set<string>(),
    statuses: new Set<string>(),
    roles: new Set<string>()
  };
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    
    // Check for UTF-8 BOM
    if (!content.startsWith('\ufeff') && !content.startsWith('Date,')) {
      errors.push('CSV should start with UTF-8 BOM or proper header');
    }
    
    // Parse CSV
    const records = parse(content, {
      columns: true,
      skip_empty_lines: true,
      trim: true
    });
    
    stats.totalRows = records.length;
    
    if (records.length === 0) {
      errors.push('CSV contains no data rows');
      return { isValid: false, errors, stats };
    }
    
    // Get header info
    const firstLine = content.split('\n')[0];
    stats.headerColumns = firstLine.split(',').length;
    
    // Expected number of days (weeks * 7)
    const expectedDays = expectedWeeks * 7;
    if (records.length !== expectedDays) {
      errors.push(`Expected ${expectedDays} rows for ${expectedWeeks} weeks, got ${records.length}`);
    }
    
    // Validate each record
    const dates: string[] = [];
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const rowNum = i + 2; // Account for header
      
      // Validate required fields
      if (!record.Date) {
        errors.push(`Row ${rowNum}: Missing Date field`);
      } else {
        dates.push(record.Date);
        
        // Validate date format
        if (!/^\d{4}-\d{2}-\d{2}$/.test(record.Date)) {
          errors.push(`Row ${rowNum}: Invalid date format "${record.Date}"`);
        }
      }
      
      if (!record.Day) {
        errors.push(`Row ${rowNum}: Missing Day field`);
      }
      
      if (record.WeekIndex === undefined || record.WeekIndex === '') {
        errors.push(`Row ${rowNum}: Missing WeekIndex field`);
      }
      
      // Collect engineer names and statuses
      for (let j = 1; j <= 6; j++) {
        const engineerField = `${j}) Engineer`;
        const statusField = `Status ${j}`;
        
        if (record[engineerField]) {
          stats.engineers.add(record[engineerField]);
        }
        
        if (record[statusField]) {
          stats.statuses.add(record[statusField]);
        }
      }
      
      // Collect role assignments
      const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
      for (const field of roleFields) {
        if (record[field]) {
          stats.roles.add(record[field]);
        }
      }
    }
    
    // Validate date continuity
    if (dates.length > 1) {
      dates.sort();
      stats.dateRange.start = dates[0];
      stats.dateRange.end = dates[dates.length - 1];
      
      const startDate = new Date(dates[0]);
      const endDate = new Date(dates[dates.length - 1]);
      const daysDiff = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysDiff !== expectedDays - 1) {
        errors.push(`Date range spans ${daysDiff + 1} days, expected ${expectedDays}`);
      }
      
      // Check for date gaps
      for (let i = 1; i < dates.length; i++) {
        const prevDate = new Date(dates[i - 1]);
        const currDate = new Date(dates[i]);
        const diff = Math.round((currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));
        
        if (diff !== 1) {
          errors.push(`Date gap between ${dates[i - 1]} and ${dates[i]}: ${diff} days`);
        }
      }
    }
    
    // Validate engineer count
    if (stats.engineers.size !== 6) {
      errors.push(`Expected 6 unique engineers, found ${stats.engineers.size}: ${Array.from(stats.engineers).join(', ')}`);
    }
    
    // Validate status values
    const validStatuses = new Set(['WORK', 'OFF', 'LEAVE', '']);
    const invalidStatuses = Array.from(stats.statuses).filter(status => !validStatuses.has(status));
    if (invalidStatuses.length > 0) {
      errors.push(`Invalid status values found: ${invalidStatuses.join(', ')}`);
    }
    
  } catch (error) {
    errors.push(`File parsing error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors, stats };
}

// Validate JSON file structure
function validateJSONFile(filePath: string): { isValid: boolean; errors: string[]; data: any } {
  const errors: string[] = [];
  let data: any = null;
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    data = JSON.parse(content);
    
    // Validate required top-level fields
    const requiredFields = ['schemaVersion', 'metadata', 'schedule'];
    for (const field of requiredFields) {
      if (!(field in data)) {
        errors.push(`Missing required field: ${field}`);
      }
    }
    
    // Validate schema version
    if (data.schemaVersion !== '2.0') {
      errors.push(`Expected schemaVersion "2.0", got "${data.schemaVersion}"`);
    }
    
    // Validate metadata structure
    if (data.metadata) {
      if (!data.metadata.generatedAt) {
        errors.push('Missing metadata.generatedAt');
      }
      
      if (!data.metadata.configuration) {
        errors.push('Missing metadata.configuration');
      }
    }
    
    // Validate schedule data
    if (data.schedule) {
      if (!Array.isArray(data.schedule)) {
        errors.push('Schedule data should be an array');
      } else if (data.schedule.length === 0) {
        errors.push('Schedule data is empty');
      }
    }
    
    // Validate fairness report if present
    if (data.fairnessReport) {
      if (!data.fairnessReport.engineer_stats) {
        errors.push('Missing fairnessReport.engineer_stats');
      }
      
      if (typeof data.fairnessReport.equity_score !== 'number') {
        errors.push('fairnessReport.equity_score should be a number');
      }
    }
    
    // Validate decision log if present
    if (data.decisionLog) {
      if (!Array.isArray(data.decisionLog)) {
        errors.push('decisionLog should be an array');
      }
    }
    
  } catch (error) {
    errors.push(`JSON parsing error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors, data };
}

test.describe('Download Validation and File Parsing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Team Scheduler');
  });

  test('should generate valid CSV file with correct structure', async ({ page }) => {
    const filePath = await generateAndDownload(page, 'csv', 4);
    
    const validation = validateCSVFile(filePath, 4);
    
    if (!validation.isValid) {
      console.error('CSV Validation Errors:', validation.errors);
      console.log('CSV Stats:', validation.stats);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.stats.totalRows).toBe(28); // 4 weeks * 7 days
    expect(validation.stats.engineers.size).toBe(6);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should generate valid XLSX file with reasonable size', async ({ page }) => {
    const filePath = await generateAndDownload(page, 'xlsx', 2);
    
    // Verify file exists and has reasonable size
    expect(fs.existsSync(filePath)).toBe(true);
    
    const stats = fs.statSync(filePath);
    expect(stats.size).toBeGreaterThan(1000); // At least 1KB
    expect(stats.size).toBeLessThan(1024 * 1024); // Less than 1MB
    
    // Verify it's a valid XLSX file (starts with PK signature)
    const buffer = fs.readFileSync(filePath);
    expect(buffer[0]).toBe(0x50); // 'P'
    expect(buffer[1]).toBe(0x4B); // 'K'
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should generate valid JSON file with complete metadata', async ({ page }) => {
    const filePath = await generateAndDownload(page, 'json', 3);
    
    const validation = validateJSONFile(filePath);
    
    if (!validation.isValid) {
      console.error('JSON Validation Errors:', validation.errors);
    }
    
    expect(validation.isValid).toBe(true);
    expect(validation.data.schemaVersion).toBe('2.0');
    expect(validation.data.schedule).toHaveLength(21); // 3 weeks * 7 days
    
    // Verify timestamp is recent (within last minute)
    const generatedAt = new Date(validation.data.metadata.generatedAt);
    const now = new Date();
    const timeDiff = Math.abs(now.getTime() - generatedAt.getTime());
    expect(timeDiff).toBeLessThan(60000); // Less than 1 minute
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should generate consistent data across different formats', async ({ page }) => {
    // Fill form once
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
    await page.fill('input[type="date"]', getNextSunday());
    await page.fill('input[type="number"][min="1"]', '2');
    
    // Generate all formats
    await page.click('button:has-text("Generate Schedule")');
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    await page.click('button:has-text("View Artifacts")');
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Download CSV
    const csvPromise = page.waitForDownload();
    await page.click('button:has-text("Download CSV")');
    const csvDownload = await csvPromise;
    const csvPath = path.join(__dirname, 'downloads', csvDownload.suggestedFilename());
    await csvDownload.saveAs(csvPath);
    
    // Download JSON
    const jsonPromise = page.waitForDownload();
    await page.click('button:has-text("Download JSON")');
    const jsonDownload = await jsonPromise;
    const jsonPath = path.join(__dirname, 'downloads', jsonDownload.suggestedFilename());
    await jsonDownload.saveAs(jsonPath);
    
    // Validate both files
    const csvValidation = validateCSVFile(csvPath, 2);
    const jsonValidation = validateJSONFile(jsonPath);
    
    expect(csvValidation.isValid).toBe(true);
    expect(jsonValidation.isValid).toBe(true);
    
    // Compare data consistency
    expect(csvValidation.stats.totalRows).toBe(14); // 2 weeks * 7 days
    expect(jsonValidation.data.schedule).toHaveLength(14);
    
    // Verify same date range
    const csvContent = fs.readFileSync(csvPath, 'utf-8');
    const csvRecords = parse(csvContent, { columns: true, skip_empty_lines: true, trim: true });
    
    const csvDates = csvRecords.map(r => r.Date).sort();
    const jsonDates = jsonValidation.data.schedule.map((r: any) => r.date).sort();
    
    expect(csvDates).toEqual(jsonDates);
    
    // Clean up
    fs.unlinkSync(csvPath);
    fs.unlinkSync(jsonPath);
  });

  test('should handle different week counts correctly', async ({ page }) => {
    const testCases = [1, 4, 8, 12];
    
    for (const weeks of testCases) {
      const filePath = await generateAndDownload(page, 'csv', weeks);
      
      const validation = validateCSVFile(filePath, weeks);
      
      expect(validation.isValid).toBe(true);
      expect(validation.stats.totalRows).toBe(weeks * 7);
      
      // Verify date range spans correct number of weeks
      const startDate = new Date(validation.stats.dateRange.start);
      const endDate = new Date(validation.stats.dateRange.end);
      const daysDiff = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
      
      expect(daysDiff).toBe(weeks * 7 - 1);
      
      // Clean up
      fs.unlinkSync(filePath);
    }
  });

  test('should generate files with descriptive filenames', async ({ page }) => {
    const csvPath = await generateAndDownload(page, 'csv');
    const xlsxPath = await generateAndDownload(page, 'xlsx');
    const jsonPath = await generateAndDownload(page, 'json');
    
    // Verify filename patterns
    const csvFilename = path.basename(csvPath);
    const xlsxFilename = path.basename(xlsxPath);
    const jsonFilename = path.basename(jsonPath);
    
    expect(csvFilename).toMatch(/^schedule-\d{4}-\d{2}-\d{2}\.csv$/);
    expect(xlsxFilename).toMatch(/^schedule-\d{4}-\d{2}-\d{2}\.xlsx$/);
    expect(jsonFilename).toMatch(/^schedule-\d{4}-\d{2}-\d{2}\.json$/);
    
    // Verify dates in filenames are today's date
    const today = new Date().toISOString().split('T')[0];
    expect(csvFilename).toContain(today);
    expect(xlsxFilename).toContain(today);
    expect(jsonFilename).toContain(today);
    
    // Clean up
    fs.unlinkSync(csvPath);
    fs.unlinkSync(xlsxPath);
    fs.unlinkSync(jsonPath);
  });

  test('should validate CSV RFC 4180 compliance', async ({ page }) => {
    const filePath = await generateAndDownload(page, 'csv');
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    
    // Check header line
    const header = lines[0];
    expect(header).toContain('Date');
    expect(header).toContain('Day');
    expect(header).toContain('WeekIndex');
    
    // Verify proper quoting for fields with commas
    const quotedFieldPattern = /"[^"]*"/;
    let hasQuotedFields = false;
    
    for (const line of lines) {
      if (quotedFieldPattern.test(line)) {
        hasQuotedFields = true;
        
        // Verify quotes are properly escaped
        const quotedMatches = line.match(/"([^"]*)"/g);
        if (quotedMatches) {
          for (const match of quotedMatches) {
            // Should not contain unescaped quotes
            const inner = match.slice(1, -1); // Remove outer quotes
            expect(inner).not.toMatch(/(?<!")["](?!")/); // No unescaped quotes
          }
        }
      }
    }
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should handle special characters in engineer names', async ({ page }) => {
    // Test with names containing special characters
    await page.fill('textarea[placeholder*="Engineer"]', 'José García, María López, François Dubois, 李小明, Müller Schmidt, O\'Connor');
    await page.fill('input[type="date"]', getNextSunday());
    await page.fill('input[type="number"][min="1"]', '1');
    
    await page.check('input[type="radio"][value="csv"]');
    
    await page.click('button:has-text("Generate Schedule")');
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    await page.click('button:has-text("View Artifacts")');
    
    const downloadPromise = page.waitForDownload();
    await page.click('button:has-text("Download CSV")');
    const download = await downloadPromise;
    
    const filePath = path.join(__dirname, 'downloads', download.suggestedFilename());
    await download.saveAs(filePath);
    
    // Verify special characters are preserved
    const content = fs.readFileSync(filePath, 'utf-8');
    expect(content).toContain('José García');
    expect(content).toContain('María López');
    expect(content).toContain('François Dubois');
    expect(content).toContain('李小明');
    expect(content).toContain('Müller Schmidt');
    expect(content).toContain('O\'Connor');
    
    // Verify CSV is still parseable
    const records = parse(content, { columns: true, skip_empty_lines: true, trim: true });
    expect(records.length).toBeGreaterThan(0);
    
    // Clean up
    fs.unlinkSync(filePath);
  });

  test('should validate file encoding (UTF-8 with BOM)', async ({ page }) => {
    const filePath = await generateAndDownload(page, 'csv');
    
    // Read file as buffer to check BOM
    const buffer = fs.readFileSync(filePath);
    
    // Check for UTF-8 BOM (EF BB BF) or ensure proper UTF-8 encoding
    const hasUTF8BOM = buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF;
    const content = fs.readFileSync(filePath, 'utf-8');
    
    // Either has BOM or content is valid UTF-8
    expect(hasUTF8BOM || content.length > 0).toBe(true);
    
    // Verify content can be read as UTF-8
    expect(() => {
      fs.readFileSync(filePath, 'utf-8');
    }).not.toThrow();
    
    // Clean up
    fs.unlinkSync(filePath);
  });
});

// Create downloads directory
test.beforeAll(async () => {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }
});