import React, { useState, useEffect } from 'react';
import { validateEngineersInput } from '../validation';
import { ValidationMessage } from './ValidationMessage';

interface EngineerInputProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  className?: string;
}

export const EngineerInput: React.FC<EngineerInputProps> = ({
  value,
  onChange,
  label = "Engineer Names (comma-separated)",
  placeholder = "Engineer A, Engineer B, Engineer C, Engineer D, Engineer E, Engineer F",
  className = ""
}) => {
  const [validation, setValidation] = useState<{ isValid: boolean; errors: string[]; warnings: string[] }>({ isValid: true, errors: [], warnings: [] });
  const [engineerCount, setEngineerCount] = useState(0);

  useEffect(() => {
    if (value.trim()) {
      const result = validateEngineersInput(value);
      setValidation(result);
      
      // Count current engineers for display
      const engineers = value.split(',').map(s => s.trim()).filter(Boolean);
      setEngineerCount(engineers.length);
    } else {
      setValidation({ isValid: true, errors: [], warnings: [] });
      setEngineerCount(0);
    }
  }, [value]);

  // const handlePaste = (_e: React.ClipboardEvent) => {
  //   // Allow normal paste behavior, validation will handle the result
  // };

  const getCounterColor = () => {
    if (engineerCount === 6) return '#059669'; // green
    if (engineerCount > 6) return '#dc2626'; // red
    return '#6b7280'; // gray
  };

  const getCounterText = () => {
    if (engineerCount === 0) return 'Enter 6 engineers';
    if (engineerCount === 6) return '✓ Perfect!';
    if (engineerCount < 6) return `${engineerCount}/6 engineers (need ${6 - engineerCount} more)`;
    return `${engineerCount}/6 engineers (${engineerCount - 6} too many)`;
  };

  return (
    <div className={`engineer-input ${className}`}>
      <div className="label-row">
        <label>{label}</label>
        <div className="counter" style={{ color: getCounterColor() }}>
          {getCounterText()}
        </div>
      </div>
      
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}

        placeholder={placeholder}
        rows={3}
        className={`textarea ${validation.errors.length > 0 ? 'error' : ''}`}
      />

      <div className="help-text">
        💡 Tip: Names can include letters, spaces, hyphens, apostrophes, and accented characters
      </div>

      <ValidationMessage 
        errors={validation.errors} 
        warnings={validation.warnings}
      />

      <style jsx>{`
        .engineer-input {
          display: flex;
          flex-direction: column;
        }
        
        .label-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;
        }
        
        label {
          font-weight: 500;
        }
        
        .counter {
          font-size: 12px;
          font-weight: 500;
        }
        
        .textarea {
          width: 100%;
          padding: 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
          font-family: inherit;
          resize: vertical;
          min-height: 80px;
        }
        
        .textarea.error {
          border-color: #dc2626;
          background-color: #fef2f2;
        }
        
        .textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }
        
        .help-text {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }
      `}</style>
    </div>
  );
};