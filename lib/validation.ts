/**
 * TypeScript Zod schemas for frontend validation.
 * Provides real-time validation for all form inputs with comprehensive error handling.
 */

import { z } from 'zod';

// Helper functions for validation
const isValidEngineerName = (name: string): boolean => {
  const trimmed = name.trim();
  // Allow letters, spaces, hyphens, apostrophes, and basic diacritics
  return /^[a-zA-ZÀ-ÿ\s\-'\.]+$/.test(trimmed) && trimmed.length > 0;
};

const isSunday = (dateStr: string): boolean => {
  try {
    const date = new Date(dateStr);
    return !isNaN(date.getTime()) && date.getDay() === 0; // Sunday = 0 in JavaScript
  } catch {
    return false;
  }
};

const uniqueEngineers = (engineers: string[]): boolean => {
  const normalized = engineers.map(name => name.trim().toLowerCase());
  return new Set(normalized).size === normalized.length;
};

const normalizeEngineerName = (name: string): string => {
  return name.trim().replace(/\s+/g, ' '); // Normalize whitespace
};

const detectSimilarNames = (engineers: string[]): string[] => {
  const warnings: string[] = [];
  const normalized = engineers.map(name => normalizeEngineerName(name).toLowerCase());
  
  for (let i = 0; i < normalized.length; i++) {
    for (let j = i + 1; j < normalized.length; j++) {
      const name1 = normalized[i];
      const name2 = normalized[j];
      
      // Check for case-only differences
      if (name1 === name2) {
        warnings.push(`"${engineers[i]}" and "${engineers[j]}" are identical when normalized`);
      }
      // Check for very similar names (simple Levenshtein distance)
      else if (calculateSimilarity(name1, name2) > 0.8) {
        warnings.push(`"${engineers[i]}" and "${engineers[j]}" are very similar - possible duplicates?`);
      }
    }
  }
  
  return warnings;
};

const calculateSimilarity = (str1: string, str2: string): number => {
  const longer = str1.length > str2.length ? str1 : str2;
  const shorter = str1.length > str2.length ? str2 : str1;
  
  if (longer.length === 0) return 1.0;
  
  const editDistance = levenshteinDistance(longer, shorter);
  return (longer.length - editDistance) / longer.length;
};

const levenshteinDistance = (str1: string, str2: string): number => {
  const matrix = Array(str2.length + 1).fill(null).map(() => Array(str1.length + 1).fill(null));
  
  for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
  for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;
  
  for (let j = 1; j <= str2.length; j++) {
    for (let i = 1; i <= str1.length; i++) {
      const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
      matrix[j][i] = Math.min(
        matrix[j][i - 1] + 1,     // deletion
        matrix[j - 1][i] + 1,     // insertion
        matrix[j - 1][i - 1] + indicator // substitution
      );
    }
  }
  
  return matrix[str2.length][str1.length];
};

// Core validation schemas

export const LeaveEntrySchema = z.object({
  engineer: z.string()
    .min(1, "Engineer name is required")
    .max(100, "Engineer name too long")
    .refine(isValidEngineerName, "Engineer name contains invalid characters"),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Date must be in YYYY-MM-DD format"),
  reason: z.string().max(200, "Reason too long").optional().default("")
});

export const SeedsSchema = z.object({
  weekend: z.number().int().min(0).max(5).default(0),
  chat: z.number().int().min(0).max(5).default(0),
  oncall: z.number().int().min(0).max(5).default(1),
  appointments: z.number().int().min(0).max(5).default(2),
  early: z.number().int().min(0).max(5).default(0)
});

export const ScheduleRequestSchema = z.object({
  engineers: z.array(z.string().min(1, "Engineer name cannot be empty"))
    .length(6, "Exactly 6 engineers are required")
    .refine(
      (engineers) => engineers.every(name => isValidEngineerName(name.trim())),
      "All engineer names must contain only letters, spaces, hyphens, apostrophes, and basic diacritics"
    )
    .refine(
      uniqueEngineers,
      "Engineer names must be unique (case-insensitive)"
    )
    .transform(engineers => engineers.map(name => normalizeEngineerName(name))),
  
  start_sunday: z.string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Date must be in YYYY-MM-DD format")
    .refine(isSunday, "Start date must be a Sunday"),
  
  weeks: z.number()
    .int("Weeks must be a whole number")
    .min(1, "At least 1 week required")
    .max(52, "Maximum 52 weeks allowed"),
  
  seeds: SeedsSchema.default({}),
  
  leave: z.array(LeaveEntrySchema).default([]),
  
  format: z.enum(['csv', 'xlsx', 'json']).default('csv')
});

export const EngineerStatusSchema = z.object({
  name: z.string().min(1, "Engineer name is required"),
  status: z.enum(["WORK", "OFF", "LEAVE", ""]).default(""),
  shift: z.string().default("")
});

export const ScheduleRowSchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format"),
  day: z.enum(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
  week_index: z.number().int().min(0),
  early1: z.string().default(""),
  early2: z.string().default(""),
  chat: z.string().default(""),
  oncall: z.string().default(""),
  appointments: z.string().default(""),
  engineers: z.array(EngineerStatusSchema)
});

// Utility functions for form validation

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  data?: any;
}

export const validateEngineersInput = (input: string): ValidationResult => {
  try {
    const engineers = input.split(',').map(s => s.trim()).filter(Boolean);
    
    // Check basic requirements first
    if (engineers.length !== 6) {
      return {
        isValid: false,
        errors: [`Expected exactly 6 engineers, got ${engineers.length}`],
        warnings: []
      };
    }
    
    // Validate each name
    const invalidNames = engineers.filter(name => !isValidEngineerName(name));
    if (invalidNames.length > 0) {
      return {
        isValid: false,
        errors: [`Invalid engineer names: ${invalidNames.join(', ')}`],
        warnings: []
      };
    }
    
    // Check for duplicates
    if (!uniqueEngineers(engineers)) {
      return {
        isValid: false,
        errors: ['Engineer names must be unique (case-insensitive)'],
        warnings: []
      };
    }
    
    // Check for similar names (warnings only)
    const warnings = detectSimilarNames(engineers);
    
    const normalizedEngineers = engineers.map(name => normalizeEngineerName(name));
    
    return {
      isValid: true,
      errors: [],
      warnings,
      data: normalizedEngineers
    };
  } catch (error) {
    return {
      isValid: false,
      errors: ['Failed to parse engineer names'],
      warnings: []
    };
  }
};

export const validateDateInput = (dateStr: string): ValidationResult => {
  try {
    if (!dateStr) {
      return {
        isValid: false,
        errors: ['Date is required'],
        warnings: []
      };
    }
    
    // Check format first
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return {
        isValid: false,
        errors: ['Date must be in YYYY-MM-DD format'],
        warnings: []
      };
    }
    
    // Check if it's a valid date
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return {
        isValid: false,
        errors: ['Invalid date'],
        warnings: []
      };
    }
    
    // Check if it's a Sunday
    const warnings: string[] = [];
    if (!isSunday(dateStr)) {
      const snappedDate = snapToSunday(dateStr);
      warnings.push(`Date is not a Sunday. Suggested: ${snappedDate}`);
    }
    
    return {
      isValid: true,
      errors: [],
      warnings,
      data: dateStr
    };
  } catch {
    return {
      isValid: false,
      errors: ['Invalid date format'],
      warnings: []
    };
  }
};

export const snapToSunday = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    const dayOfWeek = date.getDay();
    
    if (dayOfWeek === 0) {
      return dateStr; // Already Sunday
    }
    
    // Find the previous Sunday
    const daysToSubtract = dayOfWeek;
    const sunday = new Date(date);
    sunday.setDate(date.getDate() - daysToSubtract);
    
    return sunday.toISOString().split('T')[0];
  } catch {
    return dateStr; // Return original if parsing fails
  }
};

export const snapToNextSunday = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    const dayOfWeek = date.getDay();
    
    if (dayOfWeek === 0) {
      return dateStr; // Already Sunday
    }
    
    // Find the next Sunday
    const daysToAdd = 7 - dayOfWeek;
    const sunday = new Date(date);
    sunday.setDate(date.getDate() + daysToAdd);
    
    return sunday.toISOString().split('T')[0];
  } catch {
    return dateStr; // Return original if parsing fails
  }
};

export const validateWeeksInput = (weeks: number, maxWeeks: number = 52): ValidationResult => {
  if (!Number.isInteger(weeks)) {
    return {
      isValid: false,
      errors: ['Weeks must be a whole number'],
      warnings: []
    };
  }
  
  if (weeks < 1) {
    return {
      isValid: false,
      errors: ['At least 1 week is required'],
      warnings: []
    };
  }
  
  if (weeks > maxWeeks) {
    return {
      isValid: false,
      errors: [`Maximum ${maxWeeks} weeks allowed`],
      warnings: []
    };
  }
  
  const warnings: string[] = [];
  if (weeks > 26) {
    warnings.push('Generating more than 26 weeks may take longer to process');
  }
  
  return {
    isValid: true,
    errors: [],
    warnings,
    data: weeks
  };
};

export const validateSeedsInput = (seeds: any): ValidationResult => {
  try {
    const validatedSeeds = SeedsSchema.parse(seeds);
    return {
      isValid: true,
      errors: [],
      warnings: [],
      data: validatedSeeds
    };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        isValid: false,
        errors: error.errors.map(err => `${err.path.join('.')}: ${err.message}`),
        warnings: []
      };
    }
    return {
      isValid: false,
      errors: ['Invalid seeds configuration'],
      warnings: []
    };
  }
};

export const validateCompleteForm = (data: unknown): ValidationResult => {
  try {
    const validatedData = ScheduleRequestSchema.parse(data);
    return {
      isValid: true,
      errors: [],
      warnings: [],
      data: validatedData
    };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        isValid: false,
        errors: error.errors.map(err => `${err.path.join('.')}: ${err.message}`),
        warnings: []
      };
    }
    return {
      isValid: false,
      errors: ['Unknown validation error'],
      warnings: []
    };
  }
};

// Type exports for TypeScript
export type LeaveEntry = z.infer<typeof LeaveEntrySchema>;
export type SeedsConfig = z.infer<typeof SeedsSchema>;
export type ScheduleRequest = z.infer<typeof ScheduleRequestSchema>;
export type EngineerStatus = z.infer<typeof EngineerStatusSchema>;
export type ScheduleRow = z.infer<typeof ScheduleRowSchema>;