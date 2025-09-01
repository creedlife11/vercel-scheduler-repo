import React, { useState, useEffect } from 'react';
import { validateWeeksInput } from '../validation';
import { ValidationMessage } from './ValidationMessage';

interface WeeksInputProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
  className?: string;
}

export const WeeksInput: React.FC<WeeksInputProps> = ({
  value,
  onChange,
  label = "Weeks",
  className = ""
}) => {
  const [validation, setValidation] = useState({ isValid: true, errors: [], warnings: [] });

  useEffect(() => {
    const result = validateWeeksInput(value);
    setValidation(result);
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value) || 1;
    onChange(newValue);
  };

  const quickSetWeeks = (weeks: number) => {
    onChange(weeks);
  };

  return (
    <div className={`weeks-input ${className}`}>
      <label>{label}</label>
      
      <div className="input-container">
        <input
          type="number"
          min={1}
          max={52}
          value={value}
          onChange={handleChange}
          className={`number-input ${validation.errors.length > 0 ? 'error' : ''}`}
        />
        
        <div className="quick-buttons">
          <button
            type="button"
            onClick={() => quickSetWeeks(4)}
            className={`quick-btn ${value === 4 ? 'active' : ''}`}
          >
            1 Month
          </button>
          <button
            type="button"
            onClick={() => quickSetWeeks(8)}
            className={`quick-btn ${value === 8 ? 'active' : ''}`}
          >
            2 Months
          </button>
          <button
            type="button"
            onClick={() => quickSetWeeks(13)}
            className={`quick-btn ${value === 13 ? 'active' : ''}`}
          >
            Quarter
          </button>
        </div>
      </div>

      <ValidationMessage 
        errors={validation.errors} 
        warnings={validation.warnings}
      />

      <style jsx>{`
        .weeks-input {
          display: flex;
          flex-direction: column;
        }
        
        .input-container {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .number-input {
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
          width: 100%;
        }
        
        .number-input.error {
          border-color: #dc2626;
          background-color: #fef2f2;
        }
        
        .number-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }
        
        .quick-buttons {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }
        
        .quick-btn {
          padding: 4px 8px;
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 12px;
          cursor: pointer;
          white-space: nowrap;
        }
        
        .quick-btn:hover {
          background: #e5e7eb;
        }
        
        .quick-btn.active {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
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