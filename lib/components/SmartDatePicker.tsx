import React, { useState, useEffect } from 'react';
import { validateDateInput, snapToSunday, snapToNextSunday } from '../validation';
import { ValidationMessage } from './ValidationMessage';

interface SmartDatePickerProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  className?: string;
}

export const SmartDatePicker: React.FC<SmartDatePickerProps> = ({
  value,
  onChange,
  placeholder = "YYYY-MM-DD",
  label = "Start Sunday",
  className = ""
}) => {
  const [validation, setValidation] = useState({ isValid: true, errors: [], warnings: [] });
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    if (value) {
      const result = validateDateInput(value);
      setValidation(result);
      setShowSuggestions(result.warnings.length > 0);
    } else {
      setValidation({ isValid: true, errors: [], warnings: [] });
      setShowSuggestions(false);
    }
  }, [value]);

  const handleSnapToPrevious = () => {
    if (value) {
      const snapped = snapToSunday(value);
      onChange(snapped);
      setShowSuggestions(false);
    }
  };

  const handleSnapToNext = () => {
    if (value) {
      const snapped = snapToNextSunday(value);
      onChange(snapped);
      setShowSuggestions(false);
    }
  };

  const getTodaysSunday = () => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const sunday = new Date(today);
    
    if (dayOfWeek === 0) {
      // Today is Sunday
      return today.toISOString().split('T')[0];
    } else {
      // Find next Sunday
      sunday.setDate(today.getDate() + (7 - dayOfWeek));
      return sunday.toISOString().split('T')[0];
    }
  };

  const handleUseThisSunday = () => {
    const thisSunday = getTodaysSunday();
    onChange(thisSunday);
    setShowSuggestions(false);
  };

  return (
    <div className={`smart-date-picker ${className}`}>
      <label>{label}</label>
      <div className="input-container">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`date-input ${validation.errors.length > 0 ? 'error' : ''}`}
        />
        
        {!value && (
          <button
            type="button"
            onClick={handleUseThisSunday}
            className="quick-action-btn"
            title="Use this Sunday"
          >
            📅 This Sunday
          </button>
        )}
      </div>

      <ValidationMessage 
        errors={validation.errors} 
        warnings={validation.warnings}
      />

      {showSuggestions && validation.warnings.length > 0 && (
        <div className="suggestions">
          <div className="suggestion-text">Not a Sunday? Quick fix:</div>
          <div className="suggestion-buttons">
            <button
              type="button"
              onClick={handleSnapToPrevious}
              className="suggestion-btn"
            >
              ← Previous Sunday ({snapToSunday(value)})
            </button>
            <button
              type="button"
              onClick={handleSnapToNext}
              className="suggestion-btn"
            >
              Next Sunday ({snapToNextSunday(value)}) →
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .smart-date-picker {
          display: flex;
          flex-direction: column;
        }
        
        .input-container {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        
        .date-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
        }
        
        .date-input.error {
          border-color: #dc2626;
          background-color: #fef2f2;
        }
        
        .date-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }
        
        .quick-action-btn {
          padding: 6px 12px;
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 12px;
          cursor: pointer;
          white-space: nowrap;
        }
        
        .quick-action-btn:hover {
          background: #e5e7eb;
        }
        
        .suggestions {
          margin-top: 8px;
          padding: 12px;
          background: #fffbeb;
          border: 1px solid #fbbf24;
          border-radius: 4px;
        }
        
        .suggestion-text {
          font-size: 12px;
          color: #92400e;
          margin-bottom: 8px;
        }
        
        .suggestion-buttons {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        
        .suggestion-btn {
          padding: 6px 12px;
          background: #fbbf24;
          color: white;
          border: none;
          border-radius: 4px;
          font-size: 12px;
          cursor: pointer;
          white-space: nowrap;
        }
        
        .suggestion-btn:hover {
          background: #f59e0b;
        }
        
        label {
          font-weight: 500;
          margin-bottom: 4px;
          display: block;
        }
      `}</style>
    </div>
  );
};