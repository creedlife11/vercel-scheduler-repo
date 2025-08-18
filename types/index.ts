// TypeScript interfaces for the scheduler application

export interface Engineer {
  name: string;
}

export interface LeaveRequest {
  Engineer: string;
  Date: string; // YYYY-MM-DD format
  Reason: string;
}

export interface RotationSeeds {
  weekend: number;
  oncall: number;
  contacts: number;
  appointments: number;
  early: number;
}

export interface ScheduleRequest {
  engineers: string[];
  start_sunday: string; // YYYY-MM-DD format
  weeks: number;
  seeds: RotationSeeds;
  leave: LeaveRequest[];
  format: 'csv' | 'xlsx';
}

export interface DayAssignment {
  Date: string;
  Day: string;
  WeekIndex: number;
  OnCall: string;
  Contacts: string;
  Appointments: string;
  Early1: string;
  Early2: string;
  Tickets: string;
  [key: string]: string | number; // For engineer status columns
}

export interface ApiError {
  error: string;
  details?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// Validation constants
export const VALIDATION_RULES = {
  REQUIRED_ENGINEERS: 6,
  MIN_WEEKS: 1,
  MAX_WEEKS: 52,
  MIN_SEED: 0,
  MAX_SEED: 5,
  MAX_ENGINEER_NAME_LENGTH: 50,
  DATE_FORMAT: /^\d{4}-\d{2}-\d{2}$/,
} as const;

// Utility type for schedule generation status
export type ScheduleStatus = 'idle' | 'generating' | 'success' | 'error';