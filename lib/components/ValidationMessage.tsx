import React from 'react';

interface ValidationMessageProps {
  errors?: string[];
  warnings?: string[];
  className?: string;
}

export const ValidationMessage: React.FC<ValidationMessageProps> = ({ 
  errors = [], 
  warnings = [], 
  className = '' 
}) => {
  if (errors.length === 0 && warnings.length === 0) {
    return null;
  }

  return (
    <div className={`validation-messages ${className}`}>
      {errors.length > 0 && (
        <div className="errors">
          {errors.map((error, index) => (
            <div key={index} className="error-message">
              ⚠️ {error}
            </div>
          ))}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="warnings">
          {warnings.map((warning, index) => (
            <div key={index} className="warning-message">
              💡 {warning}
            </div>
          ))}
        </div>
      )}
      
      <style jsx>{`
        .validation-messages {
          margin-top: 4px;
          font-size: 14px;
        }
        
        .error-message {
          color: #dc2626;
          margin-bottom: 2px;
        }
        
        .warning-message {
          color: #d97706;
          margin-bottom: 2px;
        }
        
        .errors + .warnings {
          margin-top: 8px;
        }
      `}</style>
    </div>
  );
};