import React, { useState, useRef } from 'react';
import { ValidationMessage } from './ValidationMessage';

interface LeaveEntry {
  engineer: string;
  date: string;
  reason: string;
}

interface LeaveManagerProps {
  engineers: string[];
  leave: LeaveEntry[];
  onChange: (leave: LeaveEntry[]) => void;
  startDate?: string;
  weeks?: number;
}

interface ConflictInfo {
  date: string;
  engineer: string;
  reason: string;
  conflictType: 'weekend' | 'overlap' | 'invalid_date';
  message: string;
}

export const LeaveManager: React.FC<LeaveManagerProps> = ({
  engineers,
  leave,
  onChange,
  startDate,
  weeks = 8
}) => {
  const [showForm, setShowForm] = useState(false);
  const [newEntry, setNewEntry] = useState<LeaveEntry>({ engineer: '', date: '', reason: '' });
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([]);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Calculate date range for validation
  const getDateRange = () => {
    if (!startDate) return { start: null, end: null };
    
    const start = new Date(startDate);
    const end = new Date(start);
    end.setDate(start.getDate() + (weeks * 7) - 1);
    
    return { start, end };
  };

  // Validate leave entry for conflicts
  const validateLeaveEntry = (entry: LeaveEntry): ConflictInfo[] => {
    const conflicts: ConflictInfo[] = [];
    const { start, end } = getDateRange();
    
    if (!entry.date || !entry.engineer) return conflicts;
    
    const entryDate = new Date(entry.date);
    
    // Check if date is within schedule range
    if (start && end && (entryDate < start || entryDate > end)) {
      conflicts.push({
        date: entry.date,
        engineer: entry.engineer,
        reason: entry.reason,
        conflictType: 'invalid_date',
        message: `Date ${entry.date} is outside the schedule range (${start.toISOString().split('T')[0]} to ${end.toISOString().split('T')[0]})`
      });
    }
    
    // Check for weekend conflicts (less critical, just a warning)
    const dayOfWeek = entryDate.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      conflicts.push({
        date: entry.date,
        engineer: entry.engineer,
        reason: entry.reason,
        conflictType: 'weekend',
        message: `Leave on ${entry.date} is on a weekend - this may not affect weekday scheduling`
      });
    }
    
    // Check for overlapping leave for same engineer
    const existingLeave = leave.find(l => 
      l.engineer === entry.engineer && 
      l.date === entry.date && 
      l !== entry
    );
    
    if (existingLeave) {
      conflicts.push({
        date: entry.date,
        engineer: entry.engineer,
        reason: entry.reason,
        conflictType: 'overlap',
        message: `${entry.engineer} already has leave on ${entry.date}: ${existingLeave.reason}`
      });
    }
    
    return conflicts;
  };

  // Validate all leave entries
  const validateAllLeave = (leaveEntries: LeaveEntry[]): ConflictInfo[] => {
    const allConflicts: ConflictInfo[] = [];
    
    leaveEntries.forEach(entry => {
      const entryConflicts = validateLeaveEntry(entry);
      allConflicts.push(...entryConflicts);
    });
    
    return allConflicts;
  };

  // Add new leave entry
  const handleAddLeave = () => {
    if (!newEntry.engineer || !newEntry.date) return;
    
    const updatedLeave = [...leave, newEntry];
    const newConflicts = validateAllLeave(updatedLeave);
    
    setConflicts(newConflicts);
    onChange(updatedLeave);
    setNewEntry({ engineer: '', date: '', reason: '' });
    setShowForm(false);
  };

  // Remove leave entry
  const handleRemoveLeave = (index: number) => {
    const updatedLeave = leave.filter((_, i) => i !== index);
    const newConflicts = validateAllLeave(updatedLeave);
    
    setConflicts(newConflicts);
    onChange(updatedLeave);
  };

  // Parse CSV content
  const parseCSV = (content: string): LeaveEntry[] => {
    const lines = content.trim().split('\n');
    const entries: LeaveEntry[] = [];
    
    // Skip header if present
    const startIndex = lines[0]?.toLowerCase().includes('engineer') ? 1 : 0;
    
    for (let i = startIndex; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      
      // Simple CSV parsing (handles basic cases)
      const parts = line.split(',').map(part => part.trim().replace(/^["']|["']$/g, ''));
      
      if (parts.length >= 2) {
        entries.push({
          engineer: parts[0] || '',
          date: parts[1] || '',
          reason: parts[2] || 'Imported leave'
        });
      }
    }
    
    return entries;
  };

  // Handle file import
  const handleFileImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setImportError(null);
    
    try {
      let content: string;
      
      if (file.name.endsWith('.csv')) {
        content = await file.text();
        const importedEntries = parseCSV(content);
        
        if (importedEntries.length === 0) {
          throw new Error('No valid leave entries found in CSV file');
        }
        
        const updatedLeave = [...leave, ...importedEntries];
        const newConflicts = validateAllLeave(updatedLeave);
        
        setConflicts(newConflicts);
        onChange(updatedLeave);
        
      } else if (file.name.endsWith('.xlsx')) {
        // For XLSX, we'd need a library like xlsx or exceljs
        // For now, show an error message suggesting CSV format
        throw new Error('XLSX import not yet implemented. Please use CSV format or add entries manually.');
        
      } else {
        throw new Error('Unsupported file format. Please use CSV or XLSX files.');
      }
      
    } catch (error: any) {
      setImportError(error.message || 'Failed to import file');
    }
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Generate sample CSV for download
  const handleDownloadSample = () => {
    const sampleCSV = `Engineer,Date,Reason
Engineer A,2025-01-15,Vacation
Engineer B,2025-01-22,Sick Leave
Engineer C,2025-02-01,Personal Day`;
    
    const blob = new Blob([sampleCSV], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'leave-template.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="leave-manager">
      <div className="leave-header">
        <h3>Leave Management</h3>
        <div className="leave-actions">
          <button 
            className="btn-secondary"
            onClick={handleDownloadSample}
          >
            📄 Download Template
          </button>
          <button 
            className="btn-secondary"
            onClick={() => fileInputRef.current?.click()}
          >
            📁 Import CSV
          </button>
          <button 
            className="btn-primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ Add Leave'}
          </button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFileImport}
        style={{ display: 'none' }}
      />

      {importError && (
        <ValidationMessage errors={[importError]} />
      )}

      {conflicts.length > 0 && (
        <div className="conflicts-section">
          <h4>⚠️ Conflicts Detected</h4>
          <ValidationMessage 
            errors={conflicts.filter(c => c.conflictType !== 'weekend').map(c => c.message)}
            warnings={conflicts.filter(c => c.conflictType === 'weekend').map(c => c.message)}
          />
        </div>
      )}

      {showForm && (
        <div className="leave-form">
          <h4>Add Leave Entry</h4>
          <div className="form-grid">
            <div>
              <label>Engineer</label>
              <select
                value={newEntry.engineer}
                onChange={(e) => setNewEntry({ ...newEntry, engineer: e.target.value })}
              >
                <option value="">Select Engineer</option>
                {engineers.map(eng => (
                  <option key={eng} value={eng}>{eng}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Date</label>
              <input
                type="date"
                value={newEntry.date}
                onChange={(e) => setNewEntry({ ...newEntry, date: e.target.value })}
              />
            </div>
            <div>
              <label>Reason</label>
              <input
                type="text"
                placeholder="e.g., Vacation, Sick Leave"
                value={newEntry.reason}
                onChange={(e) => setNewEntry({ ...newEntry, reason: e.target.value })}
              />
            </div>
          </div>
          <div className="form-actions">
            <button 
              className="btn-primary"
              onClick={handleAddLeave}
              disabled={!newEntry.engineer || !newEntry.date}
            >
              Add Leave
            </button>
            <button 
              className="btn-secondary"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {leave.length > 0 && (
        <div className="leave-list">
          <h4>Current Leave Entries ({leave.length})</h4>
          <div className="leave-table">
            <div className="table-header">
              <span>Engineer</span>
              <span>Date</span>
              <span>Reason</span>
              <span>Actions</span>
            </div>
            {leave.map((entry, index) => (
              <div key={index} className="table-row">
                <span>{entry.engineer}</span>
                <span>{entry.date}</span>
                <span>{entry.reason || 'No reason provided'}</span>
                <button 
                  className="btn-danger-small"
                  onClick={() => handleRemoveLeave(index)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        .leave-manager {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          background: #f9fafb;
        }

        .leave-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .leave-header h3 {
          margin: 0;
          color: #111827;
        }

        .leave-actions {
          display: flex;
          gap: 8px;
        }

        .btn-primary {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn-primary:hover {
          background: #2563eb;
        }

        .btn-primary:disabled {
          background: #9ca3af;
          cursor: not-allowed;
        }

        .btn-secondary {
          background: #6b7280;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn-secondary:hover {
          background: #4b5563;
        }

        .btn-danger-small {
          background: #dc2626;
          color: white;
          border: none;
          padding: 4px 8px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }

        .btn-danger-small:hover {
          background: #b91c1c;
        }

        .conflicts-section {
          margin: 16px 0;
          padding: 12px;
          background: #fef3c7;
          border: 1px solid #f59e0b;
          border-radius: 6px;
        }

        .conflicts-section h4 {
          margin: 0 0 8px 0;
          color: #92400e;
        }

        .leave-form {
          margin: 16px 0;
          padding: 16px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
        }

        .leave-form h4 {
          margin: 0 0 12px 0;
          color: #111827;
        }

        .form-grid {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }

        .form-grid label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
          color: #374151;
        }

        .form-grid input,
        .form-grid select {
          width: 100%;
          padding: 8px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
        }

        .form-actions {
          display: flex;
          gap: 8px;
        }

        .leave-list {
          margin-top: 16px;
        }

        .leave-list h4 {
          margin: 0 0 12px 0;
          color: #111827;
        }

        .leave-table {
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          overflow: hidden;
        }

        .table-header {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr auto;
          gap: 12px;
          padding: 12px;
          background: #f3f4f6;
          font-weight: 600;
          color: #374151;
          border-bottom: 1px solid #d1d5db;
        }

        .table-row {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr auto;
          gap: 12px;
          padding: 12px;
          border-bottom: 1px solid #e5e7eb;
          align-items: center;
        }

        .table-row:last-child {
          border-bottom: none;
        }

        .table-row:hover {
          background: #f9fafb;
        }

        @media (max-width: 768px) {
          .leave-header {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
          }

          .leave-actions {
            justify-content: center;
          }

          .form-grid {
            grid-template-columns: 1fr;
          }

          .table-header,
          .table-row {
            grid-template-columns: 1fr;
            gap: 4px;
          }

          .table-header span,
          .table-row span {
            padding: 4px 0;
          }
        }
      `}</style>
    </div>
  );
};