/**
 * Invariant Validation Utilities for E2E Tests
 * 
 * This module provides comprehensive validation functions for testing
 * scheduling invariants as specified in requirements 2.1, 2.2, and 2.3.
 */

export interface ValidationResult {
  isValid: boolean;
  violations: string[];
  warnings?: string[];
  stats?: any;
}

export interface ScheduleRecord {
  Date: string;
  Day: string;
  WeekIndex: string;
  Early1: string;
  Early2: string;
  Chat: string;
  OnCall: string;
  Appointments: string;
  [key: string]: string; // For engineer and status fields
}

/**
 * Validates that CSV has consistent column count across all rows
 * Requirement: 2.1 - CSV column count consistency
 */
export function validateColumnConsistency(csvContent: string): ValidationResult {
  const violations: string[] = [];
  const lines = csvContent.split('\n').filter(line => line.trim());
  
  if (lines.length < 2) {
    return {
      isValid: false,
      violations: ['CSV must have at least header and one data row']
    };
  }
  
  const headerColumnCount = lines[0].split(',').length;
  
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    const columnCount = line.split(',').length;
    if (columnCount !== headerColumnCount) {
      violations.push(`Row ${i + 1}: Has ${columnCount} columns, expected ${headerColumnCount}`);
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    stats: {
      totalRows: lines.length - 1,
      headerColumns: headerColumnCount
    }
  };
}

/**
 * Validates that status fields never contain engineer names
 * Requirement: 2.2 - Status field integrity
 */
export function validateStatusFieldIntegrity(records: ScheduleRecord[], knownEngineers: string[]): ValidationResult {
  const violations: string[] = [];
  const warnings: string[] = [];
  const validStatuses = new Set(['WORK', 'OFF', 'LEAVE', '']);
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2; // Account for header
    
    for (let j = 1; j <= 6; j++) {
      const statusField = `Status ${j}`;
      const statusValue = record[statusField];
      
      if (statusValue && statusValue.trim()) {
        // Critical violation: Status contains engineer name
        if (knownEngineers.includes(statusValue)) {
          violations.push(`Row ${rowNum}: Status field "${statusField}" contains engineer name "${statusValue}"`);
        }
        // Critical violation: Invalid status value
        else if (!validStatuses.has(statusValue)) {
          violations.push(`Row ${rowNum}: Invalid status "${statusValue}" in field "${statusField}"`);
        }
      }
    }
  }
  
  // Collect status distribution stats
  const statusCounts: { [status: string]: number } = {};
  for (const record of records) {
    for (let j = 1; j <= 6; j++) {
      const status = record[`Status ${j}`];
      if (status && status.trim()) {
        statusCounts[status] = (statusCounts[status] || 0) + 1;
      }
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    warnings,
    stats: { statusDistribution: statusCounts }
  };
}

/**
 * Validates that engineer fields never contain time strings or status values
 * Requirement: 2.3 - Engineer field integrity
 */
export function validateEngineerFieldIntegrity(records: ScheduleRecord[], knownEngineers: string[]): ValidationResult {
  const violations: string[] = [];
  const warnings: string[] = [];
  const validStatuses = new Set(['WORK', 'OFF', 'LEAVE', '']);
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2; // Account for header
    
    for (let j = 1; j <= 6; j++) {
      const engineerField = `${j}) Engineer`;
      const engineerValue = record[engineerField];
      
      if (engineerValue && engineerValue.trim()) {
        // Critical violation: Engineer field contains time string
        if (engineerValue.includes(':')) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains time string "${engineerValue}"`);
        }
        // Critical violation: Engineer field contains status
        else if (validStatuses.has(engineerValue)) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains status "${engineerValue}"`);
        }
        // Critical violation: Unknown engineer
        else if (!knownEngineers.includes(engineerValue)) {
          violations.push(`Row ${rowNum}: Engineer field "${engineerField}" contains unknown engineer "${engineerValue}"`);
        }
      }
    }
  }
  
  // Collect engineer appearance stats
  const engineerCounts: { [engineer: string]: number } = {};
  for (const record of records) {
    for (let j = 1; j <= 6; j++) {
      const engineer = record[`${j}) Engineer`];
      if (engineer && engineer.trim()) {
        engineerCounts[engineer] = (engineerCounts[engineer] || 0) + 1;
      }
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    warnings,
    stats: { engineerAppearances: engineerCounts }
  };
}

/**
 * Validates that no oncall assignments occur on weekends
 * Business Rule: OnCall should not be assigned on Saturday or Sunday
 */
export function validateNoWeekendOncall(records: ScheduleRecord[]): ValidationResult {
  const violations: string[] = [];
  const warnings: string[] = [];
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2;
    
    try {
      const date = new Date(record.Date);
      const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
      
      // Check for oncall assignments on weekends
      if ((dayOfWeek === 0 || dayOfWeek === 6) && record.OnCall && record.OnCall.trim()) {
        violations.push(`Row ${rowNum}: OnCall assignment "${record.OnCall}" on weekend (${record.Day}, ${record.Date})`);
      }
      
      // Warning for other role assignments on weekends (might be valid)
      if (dayOfWeek === 0 || dayOfWeek === 6) {
        const weekendRoles = [];
        if (record.Early1 && record.Early1.trim()) weekendRoles.push(`Early1: ${record.Early1}`);
        if (record.Early2 && record.Early2.trim()) weekendRoles.push(`Early2: ${record.Early2}`);
        if (record.Chat && record.Chat.trim()) weekendRoles.push(`Chat: ${record.Chat}`);
        if (record.Appointments && record.Appointments.trim()) weekendRoles.push(`Appointments: ${record.Appointments}`);
        
        if (weekendRoles.length > 0) {
          warnings.push(`Row ${rowNum}: Weekend assignments on ${record.Day}: ${weekendRoles.join(', ')}`);
        }
      }
    } catch (error) {
      violations.push(`Row ${rowNum}: Invalid date format "${record.Date}"`);
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    warnings
  };
}

/**
 * Validates role assignment consistency within each day
 * Ensures assigned engineers are listed and not on leave
 */
export function validateRoleAssignmentConsistency(records: ScheduleRecord[]): ValidationResult {
  const violations: string[] = [];
  const warnings: string[] = [];
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const rowNum = i + 2;
    
    // Get all engineers and their statuses for this day
    const engineerStatuses: { [engineer: string]: string } = {};
    const listedEngineers: string[] = [];
    
    for (let j = 1; j <= 6; j++) {
      const engineer = record[`${j}) Engineer`];
      const status = record[`Status ${j}`];
      
      if (engineer && engineer.trim()) {
        listedEngineers.push(engineer);
        if (status) {
          engineerStatuses[engineer] = status;
        }
      }
    }
    
    // Check all role assignments
    const roleFields = ['Early1', 'Early2', 'Chat', 'OnCall', 'Appointments'];
    
    for (const roleField of roleFields) {
      const assignedEngineer = record[roleField];
      
      if (assignedEngineer && assignedEngineer.trim()) {
        // Violation: Assigned engineer not in daily engineer list
        if (!listedEngineers.includes(assignedEngineer)) {
          violations.push(`Row ${rowNum}: Engineer "${assignedEngineer}" assigned to ${roleField} but not listed in engineer columns`);
        }
        
        // Violation: Engineer on leave assigned to role
        if (engineerStatuses[assignedEngineer] === 'LEAVE') {
          violations.push(`Row ${rowNum}: Engineer "${assignedEngineer}" assigned to ${roleField} but marked as LEAVE`);
        }
        
        // Warning: Engineer marked as OFF assigned to role (might be valid for coverage)
        if (engineerStatuses[assignedEngineer] === 'OFF') {
          warnings.push(`Row ${rowNum}: Engineer "${assignedEngineer}" assigned to ${roleField} but marked as OFF`);
        }
      }
    }
    
    // Check for duplicate role assignments
    const assignments: { [engineer: string]: string[] } = {};
    
    for (const roleField of roleFields) {
      const assignedEngineer = record[roleField];
      if (assignedEngineer && assignedEngineer.trim()) {
        if (!assignments[assignedEngineer]) {
          assignments[assignedEngineer] = [];
        }
        assignments[assignedEngineer].push(roleField);
      }
    }
    
    for (const [engineer, roles] of Object.entries(assignments)) {
      if (roles.length > 1) {
        warnings.push(`Row ${rowNum}: Engineer "${engineer}" assigned to multiple roles: ${roles.join(', ')}`);
      }
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    warnings
  };
}

/**
 * Validates date continuity and week progression
 * Ensures dates are continuous and week indices progress correctly
 */
export function validateDateContinuity(records: ScheduleRecord[]): ValidationResult {
  const violations: string[] = [];
  const warnings: string[] = [];
  
  if (records.length === 0) {
    return {
      isValid: false,
      violations: ['No records to validate']
    };
  }
  
  // Sort records by date to check continuity
  const sortedRecords = [...records].sort((a, b) => a.Date.localeCompare(b.Date));
  
  // Validate date continuity
  for (let i = 1; i < sortedRecords.length; i++) {
    const prevRecord = sortedRecords[i - 1];
    const currRecord = sortedRecords[i];
    
    try {
      const prevDate = new Date(prevRecord.Date);
      const currDate = new Date(currRecord.Date);
      
      const daysDiff = Math.round((currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysDiff !== 1) {
        if (daysDiff > 1) {
          violations.push(`Date gap: ${prevRecord.Date} to ${currRecord.Date} (${daysDiff} days)`);
        } else if (daysDiff < 1) {
          violations.push(`Date overlap: ${prevRecord.Date} to ${currRecord.Date} (${daysDiff} days)`);
        }
      }
    } catch (error) {
      violations.push(`Invalid date format: ${prevRecord.Date} or ${currRecord.Date}`);
    }
  }
  
  // Validate week index progression
  let lastWeekIndex = -1;
  
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    const weekIndex = parseInt(record.WeekIndex);
    
    if (isNaN(weekIndex)) {
      violations.push(`Row ${i + 2}: Invalid WeekIndex "${record.WeekIndex}"`);
      continue;
    }
    
    if (weekIndex < lastWeekIndex) {
      violations.push(`Row ${i + 2}: WeekIndex decreased from ${lastWeekIndex} to ${weekIndex}`);
    }
    
    // Check that week index increments on Sundays (except first record)
    try {
      const date = new Date(record.Date);
      if (date.getDay() === 0 && i > 0 && weekIndex === lastWeekIndex) {
        warnings.push(`Row ${i + 2}: WeekIndex should increment on Sunday (${record.Date})`);
      }
    } catch (error) {
      // Date validation error already caught above
    }
    
    lastWeekIndex = weekIndex;
  }
  
  // Validate day names match dates
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    
    try {
      const date = new Date(record.Date);
      const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      const expectedDay = dayNames[date.getDay()];
      
      if (record.Day !== expectedDay) {
        violations.push(`Row ${i + 2}: Date ${record.Date} should be ${expectedDay}, but Day field shows ${record.Day}`);
      }
    } catch (error) {
      // Date validation error already caught above
    }
  }
  
  return {
    isValid: violations.length === 0,
    violations,
    warnings,
    stats: {
      totalDays: records.length,
      dateRange: {
        start: sortedRecords[0]?.Date,
        end: sortedRecords[sortedRecords.length - 1]?.Date
      }
    }
  };
}

/**
 * Comprehensive validation that runs all invariant checks
 * Returns aggregated results from all validation functions
 */
export function validateAllInvariants(
  csvContent: string, 
  records: ScheduleRecord[], 
  knownEngineers: string[]
): ValidationResult {
  const allViolations: string[] = [];
  const allWarnings: string[] = [];
  const allStats: any = {};
  
  // Run all validations
  const validations = [
    { name: 'Column Consistency', result: validateColumnConsistency(csvContent) },
    { name: 'Status Field Integrity', result: validateStatusFieldIntegrity(records, knownEngineers) },
    { name: 'Engineer Field Integrity', result: validateEngineerFieldIntegrity(records, knownEngineers) },
    { name: 'No Weekend OnCall', result: validateNoWeekendOncall(records) },
    { name: 'Role Assignment Consistency', result: validateRoleAssignmentConsistency(records) },
    { name: 'Date Continuity', result: validateDateContinuity(records) }
  ];
  
  // Aggregate results
  for (const validation of validations) {
    const { name, result } = validation;
    
    if (result.violations.length > 0) {
      allViolations.push(`${name}: ${result.violations.join('; ')}`);
    }
    
    if (result.warnings && result.warnings.length > 0) {
      allWarnings.push(`${name}: ${result.warnings.join('; ')}`);
    }
    
    if (result.stats) {
      allStats[name] = result.stats;
    }
  }
  
  return {
    isValid: allViolations.length === 0,
    violations: allViolations,
    warnings: allWarnings,
    stats: allStats
  };
}

/**
 * Utility function to generate a summary report of validation results
 */
export function generateValidationReport(result: ValidationResult): string {
  const lines: string[] = [];
  
  lines.push('=== SCHEDULE VALIDATION REPORT ===');
  lines.push(`Status: ${result.isValid ? '✅ PASSED' : '❌ FAILED'}`);
  lines.push('');
  
  if (result.violations.length > 0) {
    lines.push('🚨 VIOLATIONS:');
    for (const violation of result.violations) {
      lines.push(`  - ${violation}`);
    }
    lines.push('');
  }
  
  if (result.warnings && result.warnings.length > 0) {
    lines.push('⚠️  WARNINGS:');
    for (const warning of result.warnings) {
      lines.push(`  - ${warning}`);
    }
    lines.push('');
  }
  
  if (result.stats) {
    lines.push('📊 STATISTICS:');
    lines.push(JSON.stringify(result.stats, null, 2));
  }
  
  return lines.join('\n');
}