import { test, expect, Page, Download } from '@playwright/test';
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

// Helper function to fill form with valid data
async function fillValidForm(page: Page) {
  // Fill engineers
  await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
  
  // Set start date to next Sunday
  const nextSunday = getNextSunday();
  await page.fill('input[type="date"]', nextSunday);
  
  // Set weeks
  await page.fill('input[type="number"][min="1"]', '4');
  
  // Wait for validation to complete
  await page.waitForTimeout(500);
}

// Helper function to parse CSV content
function parseCSV(content: string): any[] {
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true
  });
}

// Helper function to validate CSV structure
function validateCSVStructure(content: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  try {
    const lines = content.split('\n').filter(line => line.trim());
    
    if (lines.length < 2) {
      errors.push('CSV must have at least header and one data row');
      return { isValid: false, errors };
    }
    
    // Check header structure
    const header = lines[0];
    const expectedColumns = ['Date', 'Day', 'WeekIndex', 'Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
    const engineerColumns = ['1) Engineer', 'Status 1', 'Shift 1', '2) Engineer', 'Status 2', 'Shift 2', 
                           '3) Engineer', 'Status 3', 'Shift 3', '4) Engineer', 'Status 4', 'Shift 4',
                           '5) Engineer', 'Status 5', 'Shift 5', '6) Engineer', 'Status 6', 'Shift 6'];
    
    const headerColumns = header.split(',').map(col => col.trim().replace(/"/g, ''));
    
    // Validate basic columns exist
    for (const col of expectedColumns) {
      if (!headerColumns.some(h => h.includes(col))) {
        errors.push(`Missing expected column: ${col}`);
      }
    }
    
    // Check each data row has consistent column count
    const expectedColumnCount = headerColumns.length;
    for (let i = 1; i < lines.length; i++) {
      const row = lines[i];
      if (!row.trim()) continue;
      
      const columns = row.split(',');
      if (columns.length !== expectedColumnCount) {
        errors.push(`Row ${i + 1} has ${columns.length} columns, expected ${expectedColumnCount}`);
      }
    }
    
    // Parse and validate data
    const records = parseCSV(content);
    const validStatuses = ['WORK', 'OFF', 'LEAVE', ''];
    const knownEngineers = ['Alice Smith', 'Bob Jones', 'Carol Davis', 'David Wilson', 'Eve Brown', 'Frank Miller'];
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      
      // Validate status fields
      for (let j = 1; j <= 6; j++) {
        const statusField = `Status ${j}`;
        if (record[statusField] && !validStatuses.includes(record[statusField])) {
          // Check if status field contains engineer name (common bug)
          if (knownEngineers.includes(record[statusField])) {
            errors.push(`Row ${i + 2}: Status field contains engineer name "${record[statusField]}" instead of status`);
          } else {
            errors.push(`Row ${i + 2}: Invalid status "${record[statusField]}", must be one of: ${validStatuses.join(', ')}`);
          }
        }
      }
      
      // Validate engineer fields
      for (let j = 1; j <= 6; j++) {
        const engineerField = `${j}) Engineer`;
        if (record[engineerField] && !knownEngineers.includes(record[engineerField])) {
          // Check if engineer field contains time string (common bug)
          if (record[engineerField].includes(':') || ['WORK', 'OFF', 'LEAVE'].includes(record[engineerField])) {
            errors.push(`Row ${i + 2}: Engineer field contains invalid value "${record[engineerField]}"`);
          }
        }
      }
      
      // Validate date format
      if (record.Date && !/^\d{4}-\d{2}-\d{2}$/.test(record.Date)) {
        errors.push(`Row ${i + 2}: Invalid date format "${record.Date}"`);
      }
      
      // Validate day field
      const validDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      if (record.Day && !validDays.includes(record.Day)) {
        errors.push(`Row ${i + 2}: Invalid day "${record.Day}"`);
      }
    }
    
  } catch (error) {
    errors.push(`CSV parsing error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors };
}

// Helper function to validate scheduling invariants
function validateSchedulingInvariants(content: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  try {
    const records = parseCSV(content);
    
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const date = new Date(record.Date);
      const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
      
      // Check no oncall assignments on weekends (Saturday = 6, Sunday = 0)
      if ((dayOfWeek === 0 || dayOfWeek === 6) && record.OnCall && record.OnCall.trim()) {
        errors.push(`Row ${i + 2}: OnCall assignment "${record.OnCall}" found on weekend (${record.Day})`);
      }
      
      // Validate weekend coverage patterns (should alternate Week A/B)
      if (dayOfWeek === 0 || dayOfWeek === 6) {
        const weekIndex = parseInt(record.WeekIndex);
        if (isNaN(weekIndex)) {
          errors.push(`Row ${i + 2}: Invalid WeekIndex "${record.WeekIndex}" for weekend day`);
        }
      }
    }
    
  } catch (error) {
    errors.push(`Invariant validation error: ${error.message}`);
  }
  
  return { isValid: errors.length === 0, errors };
}

test.describe('Scheduler Application E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Wait for the page to load completely
    await expect(page.locator('h1')).toContainText('Team Scheduler');
  });

  test('should load the main page with all form elements', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/scheduler/i);
    
    // Check main heading
    await expect(page.locator('h1')).toContainText('Team Scheduler');
    
    // Check form elements exist
    await expect(page.locator('textarea[placeholder*="Engineer"]')).toBeVisible();
    await expect(page.locator('input[type="date"]')).toBeVisible();
    await expect(page.locator('input[type="number"][min="1"]')).toBeVisible();
    
    // Check seeds inputs
    const seedLabels = ['weekend', 'chat', 'oncall', 'appointments', 'early'];
    for (const label of seedLabels) {
      await expect(page.locator(`label:has-text("${label}")`)).toBeVisible();
    }
    
    // Check format radio buttons
    await expect(page.locator('input[type="radio"][name="fmt"]')).toHaveCount(3);
    
    // Check generate button
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeVisible();
  });

  test('should validate form inputs in real-time', async ({ page }) => {
    // Initially button should be disabled due to empty form
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    
    // Fill engineers with invalid count (only 3 engineers)
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Bob, Carol');
    await page.waitForTimeout(500); // Wait for validation
    
    // Button should still be disabled
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    
    // Fill with valid engineers
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
    
    // Set invalid date (not Sunday)
    const today = new Date();
    const notSunday = new Date(today);
    notSunday.setDate(today.getDate() + (today.getDay() === 1 ? 0 : 1)); // Make it Monday
    await page.fill('input[type="date"]', notSunday.toISOString().split('T')[0]);
    
    await page.waitForTimeout(500);
    
    // Button should still be disabled due to non-Sunday date
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    
    // Set valid Sunday date
    const nextSunday = getNextSunday();
    await page.fill('input[type="date"]', nextSunday);
    
    // Set valid weeks
    await page.fill('input[type="number"][min="1"]', '4');
    
    await page.waitForTimeout(500);
    
    // Now button should be enabled
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeEnabled();
  });

  test('should generate and download CSV schedule', async ({ page }) => {
    await fillValidForm(page);
    
    // Select CSV format
    await page.check('input[type="radio"][value="csv"]');
    
    // Wait for download
    const downloadPromise = page.waitForDownload();
    
    // Click generate button
    await page.click('button:has-text("Generate Schedule")');
    
    // Wait for generation to complete
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Click View Artifacts to open panel
    await page.click('button:has-text("View Artifacts")');
    
    // Wait for artifact panel to open
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Click CSV download button in artifact panel
    await page.click('button:has-text("Download CSV")');
    
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toMatch(/schedule-\d{4}-\d{2}-\d{2}\.csv/);
    
    // Save and validate file content
    const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
    await download.saveAs(downloadPath);
    
    const content = fs.readFileSync(downloadPath, 'utf-8');
    
    // Validate CSV structure
    const structureValidation = validateCSVStructure(content);
    expect(structureValidation.isValid).toBe(true);
    if (!structureValidation.isValid) {
      console.error('CSV Structure Errors:', structureValidation.errors);
    }
    
    // Validate scheduling invariants
    const invariantValidation = validateSchedulingInvariants(content);
    expect(invariantValidation.isValid).toBe(true);
    if (!invariantValidation.isValid) {
      console.error('Scheduling Invariant Errors:', invariantValidation.errors);
    }
    
    // Clean up
    fs.unlinkSync(downloadPath);
  });

  test('should generate and download XLSX schedule', async ({ page }) => {
    await fillValidForm(page);
    
    // Select XLSX format
    await page.check('input[type="radio"][value="xlsx"]');
    
    // Click generate button
    await page.click('button:has-text("Generate Schedule")');
    
    // Wait for generation to complete
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Click View Artifacts
    await page.click('button:has-text("View Artifacts")');
    
    // Wait for artifact panel
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Wait for download
    const downloadPromise = page.waitForDownload();
    
    // Click XLSX download button
    await page.click('button:has-text("Download XLSX")');
    
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toMatch(/schedule-\d{4}-\d{2}-\d{2}\.xlsx/);
    
    // Verify file size is reasonable (XLSX should be larger than empty)
    const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
    await download.saveAs(downloadPath);
    
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(1000); // XLSX should be at least 1KB
    
    // Clean up
    fs.unlinkSync(downloadPath);
  });

  test('should generate and download JSON schedule with metadata', async ({ page }) => {
    await fillValidForm(page);
    
    // Select JSON format
    await page.check('input[type="radio"][value="json"]');
    
    // Click generate button
    await page.click('button:has-text("Generate Schedule")');
    
    // Wait for generation to complete
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Click View Artifacts
    await page.click('button:has-text("View Artifacts")');
    
    // Wait for artifact panel
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Wait for download
    const downloadPromise = page.waitForDownload();
    
    // Click JSON download button
    await page.click('button:has-text("Download JSON")');
    
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toMatch(/schedule-\d{4}-\d{2}-\d{2}\.json/);
    
    // Save and validate JSON content
    const downloadPath = path.join(__dirname, 'downloads', download.suggestedFilename());
    await download.saveAs(downloadPath);
    
    const content = fs.readFileSync(downloadPath, 'utf-8');
    const jsonData = JSON.parse(content);
    
    // Validate JSON structure
    expect(jsonData).toHaveProperty('schemaVersion');
    expect(jsonData).toHaveProperty('metadata');
    expect(jsonData).toHaveProperty('schedule');
    expect(jsonData.schemaVersion).toBe('2.0');
    
    // Validate metadata
    expect(jsonData.metadata).toHaveProperty('generatedAt');
    expect(jsonData.metadata).toHaveProperty('configuration');
    
    // Validate schedule data exists
    expect(Array.isArray(jsonData.schedule)).toBe(true);
    expect(jsonData.schedule.length).toBeGreaterThan(0);
    
    // Clean up
    fs.unlinkSync(downloadPath);
  });

  test('should handle leave management workflow', async ({ page }) => {
    await fillValidForm(page);
    
    // Open leave manager (if it exists as a separate section)
    const leaveSection = page.locator('h3:has-text("Leave")');
    if (await leaveSection.isVisible()) {
      // Add a leave entry
      await page.click('button:has-text("Add Leave")');
      
      // Fill leave form
      await page.selectOption('select[name="engineer"]', 'Alice Smith');
      
      // Set leave date to a date within the schedule period
      const nextSunday = new Date(getNextSunday());
      nextSunday.setDate(nextSunday.getDate() + 7); // One week after start
      await page.fill('input[type="date"][name="leaveDate"]', nextSunday.toISOString().split('T')[0]);
      
      await page.fill('input[name="reason"]', 'Vacation');
      
      // Save leave entry
      await page.click('button:has-text("Save Leave")');
    }
    
    // Generate schedule with leave
    await page.click('button:has-text("Generate Schedule")');
    
    // Wait for generation
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Verify schedule was generated successfully
    await page.click('button:has-text("View Artifacts")');
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
  });

  test('should display fairness report and decision log', async ({ page }) => {
    await fillValidForm(page);
    
    // Generate schedule
    await page.click('button:has-text("Generate Schedule")');
    
    // Wait for generation
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Open artifact panel
    await page.click('button:has-text("View Artifacts")');
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Check for fairness report tab
    const fairnessTab = page.locator('button:has-text("Fairness")');
    if (await fairnessTab.isVisible()) {
      await fairnessTab.click();
      
      // Verify fairness report content
      await expect(page.locator('[data-testid="fairness-report"]')).toBeVisible();
    }
    
    // Check for decision log tab
    const decisionTab = page.locator('button:has-text("Decisions")');
    if (await decisionTab.isVisible()) {
      await decisionTab.click();
      
      // Verify decision log content
      await expect(page.locator('[data-testid="decision-log"]')).toBeVisible();
    }
  });

  test('should handle preset management', async ({ page }) => {
    // Check if preset manager is visible
    const presetSection = page.locator('h3:has-text("Preset")');
    if (await presetSection.isVisible()) {
      // Try to apply a default preset
      const defaultPreset = page.locator('button:has-text("Ops-Default")');
      if (await defaultPreset.isVisible()) {
        await defaultPreset.click();
        
        // Verify seeds were updated
        await page.waitForTimeout(500);
        
        // Check that some seed values changed from defaults
        const weekendSeed = await page.inputValue('input[type="number"]:near(label:has-text("weekend"))');
        expect(weekendSeed).toBeDefined();
      }
    }
  });

  test('should handle error scenarios gracefully', async ({ page }) => {
    // Test with invalid engineer count
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Bob'); // Only 2 engineers
    await page.fill('input[type="date"]', getNextSunday());
    await page.fill('input[type="number"][min="1"]', '4');
    
    await page.waitForTimeout(500);
    
    // Button should be disabled
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    
    // Test with duplicate engineer names
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Alice, Bob, Carol, David, Eve');
    await page.waitForTimeout(500);
    
    // Should show validation error or keep button disabled
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    
    // Test with invalid date (non-Sunday)
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() + (today.getDay() === 1 ? 0 : 8 - today.getDay() + 1));
    await page.fill('input[type="date"]', monday.toISOString().split('T')[0]);
    
    await page.waitForTimeout(500);
    
    // Button should be disabled for non-Sunday
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
  });

  test('should maintain UI responsiveness during generation', async ({ page }) => {
    await fillValidForm(page);
    
    // Click generate
    await page.click('button:has-text("Generate Schedule")');
    
    // Verify button shows loading state
    await expect(page.locator('button:has-text("Generating...")')).toBeVisible();
    
    // Verify button is disabled during generation
    await expect(page.locator('button:has-text("Generating...")')).toBeDisabled();
    
    // Wait for completion
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible();
  });
});

// Create downloads directory if it doesn't exist
test.beforeAll(async () => {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    fs.mkdirSync(downloadsDir, { recursive: true });
  }
});

// Clean up downloads directory after tests
test.afterAll(async () => {
  const downloadsDir = path.join(__dirname, 'downloads');
  if (fs.existsSync(downloadsDir)) {
    const files = fs.readdirSync(downloadsDir);
    for (const file of files) {
      fs.unlinkSync(path.join(downloadsDir, file));
    }
  }
});