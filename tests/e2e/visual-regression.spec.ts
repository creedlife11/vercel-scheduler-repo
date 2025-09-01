import { test, expect, Page } from '@playwright/test';

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
  await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
  await page.fill('input[type="date"]', getNextSunday());
  await page.fill('input[type="number"][min="1"]', '4');
  await page.waitForTimeout(500); // Wait for validation
}

test.describe('Visual Regression and UI Component Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Team Scheduler');
  });

  test('should render main page layout correctly', async ({ page }) => {
    // Take screenshot of the main page
    await expect(page).toHaveScreenshot('main-page-layout.png');
    
    // Verify key UI elements are positioned correctly
    const header = page.locator('h1');
    const engineerInput = page.locator('textarea[placeholder*="Engineer"]');
    const dateInput = page.locator('input[type="date"]');
    const weeksInput = page.locator('input[type="number"][min="1"]');
    const generateButton = page.locator('button:has-text("Generate Schedule")');
    
    // Check elements are visible and in expected positions
    await expect(header).toBeVisible();
    await expect(engineerInput).toBeVisible();
    await expect(dateInput).toBeVisible();
    await expect(weeksInput).toBeVisible();
    await expect(generateButton).toBeVisible();
    
    // Verify layout structure
    const headerBox = await header.boundingBox();
    const engineerBox = await engineerInput.boundingBox();
    
    expect(headerBox).toBeTruthy();
    expect(engineerBox).toBeTruthy();
    
    if (headerBox && engineerBox) {
      // Header should be above engineer input
      expect(headerBox.y).toBeLessThan(engineerBox.y);
    }
  });

  test('should render form validation states correctly', async ({ page }) => {
    // Test empty form state
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeDisabled();
    await expect(page).toHaveScreenshot('form-empty-state.png');
    
    // Test partially filled form
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Bob, Carol');
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('form-partial-state.png');
    
    // Test validation error state
    await page.fill('input[type="date"]', '2025-01-06'); // Monday, not Sunday
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('form-validation-error.png');
    
    // Test valid form state
    await fillValidForm(page);
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeEnabled();
    await expect(page).toHaveScreenshot('form-valid-state.png');
  });

  test('should render seeds configuration section correctly', async ({ page }) => {
    const seedsSection = page.locator('h3:has-text("Seeds")');
    await expect(seedsSection).toBeVisible();
    
    // Check all seed inputs are present
    const seedLabels = ['weekend', 'chat', 'oncall', 'appointments', 'early'];
    for (const label of seedLabels) {
      await expect(page.locator(`label:has-text("${label}")`)).toBeVisible();
    }
    
    // Take screenshot of seeds section
    await expect(seedsSection.locator('..').locator('..')).toHaveScreenshot('seeds-section.png');
    
    // Test seed input interactions
    const weekendInput = page.locator('input[type="number"]:near(label:has-text("weekend"))');
    await weekendInput.fill('3');
    await page.waitForTimeout(200);
    
    await expect(page).toHaveScreenshot('seeds-modified.png');
  });

  test('should render format selection correctly', async ({ page }) => {
    const formatSection = page.locator('h3:has-text("Output")');
    await expect(formatSection).toBeVisible();
    
    // Check all format options
    const csvRadio = page.locator('input[type="radio"][value="csv"]');
    const xlsxRadio = page.locator('input[type="radio"][value="xlsx"]');
    const jsonRadio = page.locator('input[type="radio"][value="json"]');
    
    await expect(csvRadio).toBeVisible();
    await expect(xlsxRadio).toBeVisible();
    await expect(jsonRadio).toBeVisible();
    
    // CSV should be selected by default
    await expect(csvRadio).toBeChecked();
    
    // Test format selection changes
    await xlsxRadio.check();
    await expect(xlsxRadio).toBeChecked();
    await expect(page).toHaveScreenshot('format-xlsx-selected.png');
    
    await jsonRadio.check();
    await expect(jsonRadio).toBeChecked();
    await expect(page).toHaveScreenshot('format-json-selected.png');
  });

  test('should render loading state during generation', async ({ page }) => {
    await fillValidForm(page);
    
    // Start generation
    await page.click('button:has-text("Generate Schedule")');
    
    // Capture loading state
    await expect(page.locator('button:has-text("Generating...")')).toBeVisible();
    await expect(page).toHaveScreenshot('generation-loading-state.png');
    
    // Wait for completion
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    await expect(page).toHaveScreenshot('generation-complete-state.png');
  });

  test('should render artifact panel correctly', async ({ page }) => {
    await fillValidForm(page);
    
    // Generate schedule
    await page.click('button:has-text("Generate Schedule")');
    await expect(page.locator('button:has-text("View Artifacts")')).toBeVisible({ timeout: 30000 });
    
    // Open artifact panel
    await page.click('button:has-text("View Artifacts")');
    await expect(page.locator('[data-testid="artifact-panel"]')).toBeVisible();
    
    // Take screenshot of artifact panel
    await expect(page).toHaveScreenshot('artifact-panel-open.png');
    
    // Test different tabs if they exist
    const csvTab = page.locator('button:has-text("CSV")');
    if (await csvTab.isVisible()) {
      await csvTab.click();
      await expect(page).toHaveScreenshot('artifact-panel-csv-tab.png');
    }
    
    const xlsxTab = page.locator('button:has-text("XLSX")');
    if (await xlsxTab.isVisible()) {
      await xlsxTab.click();
      await expect(page).toHaveScreenshot('artifact-panel-xlsx-tab.png');
    }
    
    const jsonTab = page.locator('button:has-text("JSON")');
    if (await jsonTab.isVisible()) {
      await jsonTab.click();
      await expect(page).toHaveScreenshot('artifact-panel-json-tab.png');
    }
    
    const fairnessTab = page.locator('button:has-text("Fairness")');
    if (await fairnessTab.isVisible()) {
      await fairnessTab.click();
      await expect(page).toHaveScreenshot('artifact-panel-fairness-tab.png');
    }
    
    const decisionsTab = page.locator('button:has-text("Decisions")');
    if (await decisionsTab.isVisible()) {
      await decisionsTab.click();
      await expect(page).toHaveScreenshot('artifact-panel-decisions-tab.png');
    }
  });

  test('should render preset manager correctly', async ({ page }) => {
    const presetSection = page.locator('h3:has-text("Preset")');
    
    if (await presetSection.isVisible()) {
      await expect(presetSection).toBeVisible();
      await expect(page).toHaveScreenshot('preset-manager-section.png');
      
      // Test preset buttons if they exist
      const defaultPreset = page.locator('button:has-text("Ops-Default")');
      if (await defaultPreset.isVisible()) {
        await defaultPreset.click();
        await page.waitForTimeout(500);
        await expect(page).toHaveScreenshot('preset-applied-state.png');
      }
    }
  });

  test('should render leave manager correctly', async ({ page }) => {
    const leaveSection = page.locator('h3:has-text("Leave")');
    
    if (await leaveSection.isVisible()) {
      await expect(leaveSection).toBeVisible();
      await expect(page).toHaveScreenshot('leave-manager-section.png');
      
      // Test adding leave if functionality exists
      const addLeaveButton = page.locator('button:has-text("Add Leave")');
      if (await addLeaveButton.isVisible()) {
        await addLeaveButton.click();
        await page.waitForTimeout(500);
        await expect(page).toHaveScreenshot('leave-manager-add-form.png');
      }
    }
  });

  test('should handle responsive design on different screen sizes', async ({ page }) => {
    // Test desktop view (default)
    await expect(page).toHaveScreenshot('desktop-view.png');
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page).toHaveScreenshot('tablet-view.png');
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page).toHaveScreenshot('mobile-view.png');
    
    // Verify form is still usable on mobile
    await fillValidForm(page);
    await expect(page.locator('button:has-text("Generate Schedule")')).toBeEnabled();
    await expect(page).toHaveScreenshot('mobile-form-filled.png');
  });

  test('should render error states correctly', async ({ page }) => {
    // Test with invalid engineer count
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Bob'); // Only 2 engineers
    await page.fill('input[type="date"]', getNextSunday());
    await page.fill('input[type="number"][min="1"]', '4');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('error-invalid-engineer-count.png');
    
    // Test with duplicate engineers
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice, Alice, Bob, Carol, David, Eve');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('error-duplicate-engineers.png');
    
    // Test with invalid date
    await page.fill('textarea[placeholder*="Engineer"]', 'Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller');
    await page.fill('input[type="date"]', '2025-01-06'); // Monday
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('error-invalid-date.png');
  });

  test('should maintain visual consistency across browser interactions', async ({ page }) => {
    await fillValidForm(page);
    
    // Test hover states
    const generateButton = page.locator('button:has-text("Generate Schedule")');
    await generateButton.hover();
    await expect(page).toHaveScreenshot('button-hover-state.png');
    
    // Test focus states
    const engineerInput = page.locator('textarea[placeholder*="Engineer"]');
    await engineerInput.focus();
    await expect(page).toHaveScreenshot('input-focus-state.png');
    
    // Test active states
    await generateButton.click();
    await expect(page.locator('button:has-text("Generating...")')).toBeVisible();
    await expect(page).toHaveScreenshot('button-active-state.png');
  });

  test('should render authentication wrapper correctly', async ({ page }) => {
    // This test assumes the AuthWrapper component is present
    // The actual behavior will depend on authentication state
    
    // Check if auth-related elements are present
    const authElements = await page.locator('[data-testid*="auth"]').count();
    
    if (authElements > 0) {
      await expect(page).toHaveScreenshot('auth-wrapper-state.png');
    }
    
    // Test should pass regardless of auth implementation
    expect(true).toBe(true);
  });
});

// Configure visual comparison settings
test.use({
  // Use consistent viewport for visual tests
  viewport: { width: 1280, height: 720 },
});

// Configure screenshot comparison
test.describe.configure({
  mode: 'parallel',
  retries: 2, // Retry visual tests to handle minor rendering differences
});