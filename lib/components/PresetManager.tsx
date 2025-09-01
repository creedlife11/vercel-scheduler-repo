import React, { useState, useEffect } from 'react';
import { ValidationMessage } from './ValidationMessage';

interface PresetConfig {
  id: string;
  name: string;
  description: string;
  seeds: {
    weekend: number;
    chat: number;
    oncall: number;
    appointments: number;
    early: number;
  };
  weeks: number;
  created: string;
  isDefault?: boolean;
}

interface PresetManagerProps {
  currentSeeds: {
    weekend: number;
    chat: number;
    oncall: number;
    appointments: number;
    early: number;
  };
  currentWeeks: number;
  onApplyPreset: (seeds: any, weeks: number) => void;
}

const DEFAULT_PRESETS: PresetConfig[] = [
  {
    id: 'ops-default',
    name: 'Ops Default',
    description: 'Standard operations rotation with balanced coverage',
    seeds: { weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0 },
    weeks: 8,
    created: '2025-01-01',
    isDefault: true
  },
  {
    id: 'holiday-light',
    name: 'Holiday Light',
    description: 'Reduced rotation for holiday periods with minimal shifts',
    seeds: { weekend: 2, chat: 1, oncall: 0, appointments: 1, early: 3 },
    weeks: 4,
    created: '2025-01-01',
    isDefault: true
  },
  {
    id: 'eu-rotation',
    name: 'EU Rotation',
    description: 'European timezone focused rotation with early shift emphasis',
    seeds: { weekend: 1, chat: 2, oncall: 3, appointments: 0, early: 1 },
    weeks: 12,
    created: '2025-01-01',
    isDefault: true
  }
];

export const PresetManager: React.FC<PresetManagerProps> = ({
  currentSeeds,
  currentWeeks,
  onApplyPreset
}) => {
  const [presets, setPresets] = useState<PresetConfig[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetDescription, setNewPresetDescription] = useState('');
  const [importData, setImportData] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Load presets from localStorage on component mount
  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = () => {
    try {
      const stored = localStorage.getItem('scheduler-presets');
      const userPresets = stored ? JSON.parse(stored) : [];
      
      // Combine default presets with user presets
      const allPresets = [...DEFAULT_PRESETS, ...userPresets];
      setPresets(allPresets);
    } catch (error) {
      console.error('Failed to load presets:', error);
      setPresets(DEFAULT_PRESETS);
    }
  };

  const savePresets = (presetsToSave: PresetConfig[]) => {
    try {
      // Only save user presets (not default ones)
      const userPresets = presetsToSave.filter(p => !p.isDefault);
      localStorage.setItem('scheduler-presets', JSON.stringify(userPresets));
    } catch (error) {
      console.error('Failed to save presets:', error);
      throw new Error('Failed to save presets to local storage');
    }
  };

  const handleSavePreset = () => {
    if (!newPresetName.trim()) {
      setError('Preset name is required');
      return;
    }

    // Check for duplicate names
    if (presets.some(p => p.name.toLowerCase() === newPresetName.trim().toLowerCase())) {
      setError('A preset with this name already exists');
      return;
    }

    const newPreset: PresetConfig = {
      id: `user-${Date.now()}`,
      name: newPresetName.trim(),
      description: newPresetDescription.trim() || 'Custom preset',
      seeds: { ...currentSeeds },
      weeks: currentWeeks,
      created: new Date().toISOString().split('T')[0],
      isDefault: false
    };

    try {
      const updatedPresets = [...presets, newPreset];
      setPresets(updatedPresets);
      savePresets(updatedPresets);
      
      setShowSaveDialog(false);
      setNewPresetName('');
      setNewPresetDescription('');
      setError(null);
      setSuccess('Preset saved successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      setError(error.message || 'Failed to save preset');
    }
  };

  const handleDeletePreset = (presetId: string) => {
    const preset = presets.find(p => p.id === presetId);
    if (preset?.isDefault) {
      setError('Cannot delete default presets');
      return;
    }

    if (!confirm('Are you sure you want to delete this preset?')) {
      return;
    }

    try {
      const updatedPresets = presets.filter(p => p.id !== presetId);
      setPresets(updatedPresets);
      savePresets(updatedPresets);
      
      setSuccess('Preset deleted successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      setError(error.message || 'Failed to delete preset');
    }
  };

  const handleApplyPreset = (preset: PresetConfig) => {
    onApplyPreset(preset.seeds, preset.weeks);
    setSuccess(`Applied preset: ${preset.name}`);
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleExportPresets = () => {
    try {
      const userPresets = presets.filter(p => !p.isDefault);
      const exportData = {
        version: '1.0',
        exported: new Date().toISOString(),
        presets: userPresets
      };
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
        type: 'application/json' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `scheduler-presets-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      setSuccess('Presets exported successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      setError(error.message || 'Failed to export presets');
    }
  };

  const handleImportPresets = () => {
    try {
      if (!importData.trim()) {
        setError('Please paste the preset data');
        return;
      }

      const parsed = JSON.parse(importData);
      
      if (!parsed.presets || !Array.isArray(parsed.presets)) {
        throw new Error('Invalid preset format');
      }

      // Validate each preset
      const importedPresets: PresetConfig[] = parsed.presets.map((p: any, index: number) => {
        if (!p.name || !p.seeds) {
          throw new Error(`Invalid preset at position ${index + 1}`);
        }
        
        return {
          id: `imported-${Date.now()}-${index}`,
          name: p.name,
          description: p.description || 'Imported preset',
          seeds: {
            weekend: p.seeds.weekend || 0,
            chat: p.seeds.chat || 0,
            oncall: p.seeds.oncall || 1,
            appointments: p.seeds.appointments || 2,
            early: p.seeds.early || 0
          },
          weeks: p.weeks || 8,
          created: new Date().toISOString().split('T')[0],
          isDefault: false
        };
      });

      // Check for name conflicts
      const conflicts = importedPresets.filter(imported => 
        presets.some(existing => 
          existing.name.toLowerCase() === imported.name.toLowerCase()
        )
      );

      if (conflicts.length > 0) {
        const conflictNames = conflicts.map(p => p.name).join(', ');
        if (!confirm(`The following presets already exist and will be skipped: ${conflictNames}. Continue?`)) {
          return;
        }
      }

      // Filter out conflicts and add unique presets
      const uniquePresets = importedPresets.filter(imported => 
        !presets.some(existing => 
          existing.name.toLowerCase() === imported.name.toLowerCase()
        )
      );

      if (uniquePresets.length === 0) {
        setError('No new presets to import');
        return;
      }

      const updatedPresets = [...presets, ...uniquePresets];
      setPresets(updatedPresets);
      savePresets(updatedPresets);
      
      setShowImportDialog(false);
      setImportData('');
      setError(null);
      setSuccess(`Imported ${uniquePresets.length} preset(s) successfully!`);
      setTimeout(() => setSuccess(null), 3000);
      
    } catch (error: any) {
      setError(error.message || 'Failed to import presets');
    }
  };

  return (
    <div className="preset-manager">
      <div className="preset-header">
        <h3>Configuration Presets</h3>
        <div className="preset-actions">
          <button 
            className="btn-secondary"
            onClick={() => setShowImportDialog(true)}
          >
            📥 Import
          </button>
          <button 
            className="btn-secondary"
            onClick={handleExportPresets}
          >
            📤 Export
          </button>
          <button 
            className="btn-primary"
            onClick={() => setShowSaveDialog(true)}
          >
            💾 Save Current
          </button>
        </div>
      </div>

      {error && <ValidationMessage errors={[error]} />}
      {success && (
        <div className="success-message">
          ✅ {success}
        </div>
      )}

      <div className="presets-grid">
        {presets.map(preset => (
          <div key={preset.id} className="preset-card">
            <div className="preset-info">
              <h4>
                {preset.name}
                {preset.isDefault && <span className="default-badge">Default</span>}
              </h4>
              <p>{preset.description}</p>
              <div className="preset-details">
                <span>Weeks: {preset.weeks}</span>
                <span>Seeds: W:{preset.seeds.weekend} C:{preset.seeds.chat} O:{preset.seeds.oncall} A:{preset.seeds.appointments} E:{preset.seeds.early}</span>
              </div>
            </div>
            <div className="preset-actions-card">
              <button 
                className="btn-apply"
                onClick={() => handleApplyPreset(preset)}
              >
                Apply
              </button>
              {!preset.isDefault && (
                <button 
                  className="btn-delete"
                  onClick={() => handleDeletePreset(preset.id)}
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Save Current Configuration</h3>
            <div className="form-group">
              <label>Preset Name</label>
              <input
                type="text"
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                placeholder="e.g., My Custom Rotation"
                maxLength={50}
              />
            </div>
            <div className="form-group">
              <label>Description (optional)</label>
              <textarea
                value={newPresetDescription}
                onChange={(e) => setNewPresetDescription(e.target.value)}
                placeholder="Describe when to use this preset..."
                maxLength={200}
                rows={3}
              />
            </div>
            <div className="current-config">
              <h4>Current Configuration:</h4>
              <p>Weeks: {currentWeeks}</p>
              <p>Seeds: Weekend:{currentSeeds.weekend}, Chat:{currentSeeds.chat}, OnCall:{currentSeeds.oncall}, Appointments:{currentSeeds.appointments}, Early:{currentSeeds.early}</p>
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={handleSavePreset}>
                Save Preset
              </button>
              <button className="btn-secondary" onClick={() => setShowSaveDialog(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Dialog */}
      {showImportDialog && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Import Presets</h3>
            <div className="form-group">
              <label>Paste Preset Data (JSON)</label>
              <textarea
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder="Paste the exported preset JSON data here..."
                rows={8}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={handleImportPresets}>
                Import Presets
              </button>
              <button className="btn-secondary" onClick={() => setShowImportDialog(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .preset-manager {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          background: #f9fafb;
        }

        .preset-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .preset-header h3 {
          margin: 0;
          color: #111827;
        }

        .preset-actions {
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

        .success-message {
          background: #d1fae5;
          border: 1px solid #10b981;
          color: #065f46;
          padding: 8px 12px;
          border-radius: 6px;
          margin-bottom: 16px;
        }

        .presets-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .preset-card {
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .preset-info h4 {
          margin: 0 0 8px 0;
          color: #111827;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .default-badge {
          background: #fbbf24;
          color: #92400e;
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 500;
        }

        .preset-info p {
          margin: 0 0 12px 0;
          color: #6b7280;
          font-size: 14px;
        }

        .preset-details {
          display: flex;
          flex-direction: column;
          gap: 4px;
          font-size: 12px;
          color: #4b5563;
        }

        .preset-actions-card {
          display: flex;
          gap: 8px;
          margin-top: 12px;
        }

        .btn-apply {
          background: #10b981;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          flex: 1;
        }

        .btn-apply:hover {
          background: #059669;
        }

        .btn-delete {
          background: #dc2626;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }

        .btn-delete:hover {
          background: #b91c1c;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: white;
          border-radius: 8px;
          padding: 24px;
          width: 90vw;
          max-width: 500px;
          max-height: 80vh;
          overflow-y: auto;
        }

        .modal h3 {
          margin: 0 0 20px 0;
          color: #111827;
        }

        .form-group {
          margin-bottom: 16px;
        }

        .form-group label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
          color: #374151;
        }

        .form-group input,
        .form-group textarea {
          width: 100%;
          padding: 8px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
          font-family: inherit;
        }

        .current-config {
          background: #f3f4f6;
          padding: 12px;
          border-radius: 6px;
          margin-bottom: 20px;
        }

        .current-config h4 {
          margin: 0 0 8px 0;
          color: #111827;
        }

        .current-config p {
          margin: 4px 0;
          color: #4b5563;
          font-size: 14px;
        }

        .modal-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
        }

        @media (max-width: 768px) {
          .preset-header {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
          }

          .preset-actions {
            justify-content: center;
          }

          .presets-grid {
            grid-template-columns: 1fr;
          }

          .modal {
            width: 95vw;
            padding: 16px;
          }
        }
      `}</style>
    </div>
  );
};