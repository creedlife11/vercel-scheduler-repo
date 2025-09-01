# End-to-End Test Suite

This directory contains comprehensive E2E tests for the Team Scheduler application using Playwright.

## Test Files

### 1. `scheduler.spec.ts` - Main Application Workflow Tests
- **Complete user workflow testing**: Form filling, schedule generation, file downloads
- **Form validation testing**: Real-time validation, error states, edge cases
- **Download functionality**: CSV, XLSX, and JSON file generation and validation
- **UI interaction testing**: Button states, loading indicators, artifact panel
- **Leave management**: Adding leave entries and conflict detection
- **Preset management**: Applying configuration presets
- **Error handling**: Invalid inputs, network errors, graceful degradation

### 2. `invariant-validation.spec.ts` - Data Integrity Tests
- **CSV column consistency**: Validates every row has exact expected column count
- **Status field integrity**: Ensures status fields only contain valid values (WORK, OFF, LEAVE, "")
- **Engineer field integrity**: Ensures engineer fields never contain time strings or status values
- **Weekend oncall validation**: Verifies no oncall assignments on weekends
- **Engineer name consistency**: Validates consistent engineer names across all references
- **Date/day consistency**: Ensures date fields match day-of-week calculations
- **Week index progression**: Validates proper week numbering and progression

### 3. `visual-regression.spec.ts` - UI Component Tests
- **Layout rendering**: Main page structure and component positioning
- **Form validation states**: Empty, partial, error, and valid form states
- **Seeds configuration**: Input interactions and visual feedback
- **Format selection**: Radio button states and visual indicators
- **Loading states**: Generation progress and button state changes
- **Artifact panel**: Tabbed interface and content display
- **Responsive design**: Mobile, tablet, and desktop viewport testing
- **Error state rendering**: Visual representation of validation errors
- **Authentication wrapper**: Auth-related UI components

### 4. `download-validation.spec.ts` - File Format Tests
- **CSV structure validation**: RFC 4180 compliance, UTF-8 encoding, proper headers
- **XLSX file validation**: Binary format verification, file size checks
- **JSON schema validation**: Schema version, metadata structure, data integrity
- **Cross-format consistency**: Ensures same data across different export formats
- **Week count handling**: Validates different schedule durations (1-52 weeks)
- **Filename generation**: Descriptive filenames with dates and configuration
- **Special character handling**: Unicode names, accents, apostrophes
- **File encoding**: UTF-8 BOM validation for CSV files

## Test Requirements Coverage

### Requirement 2.1: CSV Column Count Consistency
- ✅ `invariant-validation.spec.ts` - "should validate CSV column count consistency across all rows"
- ✅ `download-validation.spec.ts` - "should generate valid CSV file with correct structure"

### Requirement 2.2: Status Field Integrity  
- ✅ `invariant-validation.spec.ts` - "should ensure status fields never contain engineer names"
- ✅ Tests validate status ∈ {WORK, OFF, LEAVE, ""} and never engineer names

### Requirement 2.3: Engineer Field Integrity
- ✅ `invariant-validation.spec.ts` - "should ensure engineer fields never contain time strings or statuses"
- ✅ Tests verify engineer columns contain only known engineer names

### Requirement 2.5: E2E Testing Infrastructure
- ✅ `scheduler.spec.ts` - Complete user workflow coverage
- ✅ `download-validation.spec.ts` - File download and parsing validation
- ✅ `visual-regression.spec.ts` - UI component testing

## Running the Tests

### Prerequisites
```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### Test Execution
```bash
# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test tests/e2e/scheduler.spec.ts

# Run tests in headed mode (with browser UI)
npx playwright test --headed

# Run tests with debug mode
npx playwright test --debug

# Generate test report
npx playwright test --reporter=html
```

### Test Configuration
Tests are configured in `playwright.config.ts` with:
- **Base URL**: http://localhost:3000
- **Browsers**: Chromium, Firefox, WebKit
- **Viewport**: 1280x720 for visual tests
- **Retries**: 2 retries on CI, 0 locally
- **Timeout**: 30 seconds for generation operations
- **Screenshots**: On failure and for visual regression tests

## Test Data and Fixtures

### Default Test Data
- **Engineers**: Alice Smith, Bob Jones, Carol Davis, David Wilson, Eve Brown, Frank Miller
- **Schedule Duration**: 4 weeks (configurable per test)
- **Start Date**: Next Sunday from test execution date
- **Seeds**: Default rotation values (weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0)

### File Validation Helpers
- `validateCSVStructure()`: Comprehensive CSV format validation
- `validateSchedulingRules()`: Business rule validation (no weekend oncall, etc.)
- `validateJSONFile()`: JSON schema and metadata validation
- `parseCSV()`: RFC 4180 compliant CSV parsing

### Visual Regression
- Screenshots stored in `test-results/` directory
- Baseline images in `tests/e2e/scheduler.spec.ts-snapshots/`
- Automatic comparison with 2-pixel threshold
- Cross-browser visual consistency validation

## Debugging Failed Tests

### Common Issues
1. **Timing Issues**: Use `page.waitForTimeout()` or `expect().toBeVisible()` with timeout
2. **Download Failures**: Ensure artifact panel is fully loaded before clicking download
3. **Visual Differences**: Check for browser-specific rendering differences
4. **CSV Parsing Errors**: Verify UTF-8 encoding and proper escaping

### Debug Commands
```bash
# Run single test with debug
npx playwright test tests/e2e/scheduler.spec.ts:10 --debug

# Generate trace for failed test
npx playwright test --trace on

# View test report
npx playwright show-report
```

## CI/CD Integration

Tests are integrated into the CI pipeline via `.github/workflows/ci.yml`:
- Runs after successful Python and Node.js test suites
- Uses headless browsers in CI environment
- Generates HTML reports on failure
- Uploads test artifacts for debugging

### Environment Variables
- `CI=true`: Enables CI-specific configuration
- `PLAYWRIGHT_BROWSERS_PATH`: Custom browser installation path
- `BASE_URL`: Override default application URL for testing

## Test Maintenance

### Adding New Tests
1. Follow existing test patterns and naming conventions
2. Use helper functions for common operations (form filling, file validation)
3. Add appropriate data-testid attributes to new UI components
4. Include both positive and negative test cases
5. Update this README with new test descriptions

### Updating Existing Tests
1. Maintain backward compatibility with existing assertions
2. Update visual regression baselines when UI changes are intentional
3. Ensure test data remains realistic and representative
4. Keep test execution time reasonable (< 30 seconds per test)

### Performance Considerations
- Tests run in parallel by default
- Use `test.describe.serial()` for tests that must run sequentially
- Minimize file I/O operations in test loops
- Clean up downloaded files after validation
- Use appropriate timeouts for different operations

This comprehensive E2E test suite ensures the scheduler application maintains data integrity, provides excellent user experience, and generates reliable output files across all supported formats.