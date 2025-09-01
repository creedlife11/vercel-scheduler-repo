import React, { useState } from 'react';

interface ArtifactData {
  csv?: string;
  xlsx?: Blob;
  json?: object;
  fairnessReport?: object;
  decisionLog?: object[];
}

interface ArtifactPanelProps {
  data: ArtifactData | null;
  isVisible: boolean;
  onClose: () => void;
  onDownload?: (format: 'csv' | 'xlsx' | 'json') => void;
}

type TabType = 'csv' | 'xlsx' | 'json' | 'fairness' | 'decisions';

export const ArtifactPanel: React.FC<ArtifactPanelProps> = ({ 
  data, 
  isVisible, 
  onClose,
  onDownload 
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('csv');
  const [copySuccess, setCopySuccess] = useState<string | null>(null);

  if (!isVisible || !data) {
    return null;
  }

  const handleCopyToClipboard = async (content: string, format: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopySuccess(format);
      setTimeout(() => setCopySuccess(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'csv':
        return (
          <div className="tab-content">
            <div className="content-header">
              <h4>CSV Preview</h4>
              <div className="header-actions">
                {data.csv && (
                  <>
                    <button 
                      className="copy-btn"
                      onClick={() => handleCopyToClipboard(data.csv!, 'CSV')}
                    >
                      {copySuccess === 'CSV' ? '✓ Copied!' : '📋 Copy'}
                    </button>
                    {onDownload && (
                      <button 
                        className="download-btn"
                        onClick={() => onDownload('csv')}
                      >
                        Download CSV
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
            <pre className="content-preview">
              {data.csv || 'No CSV data available'}
            </pre>
          </div>
        );

      case 'xlsx':
        return (
          <div className="tab-content">
            <div className="content-header">
              <h4>Excel File</h4>
              <div className="header-actions">
                {data.xlsx && onDownload && (
                  <button 
                    className="download-btn"
                    onClick={() => onDownload('xlsx')}
                  >
                    Download XLSX
                  </button>
                )}
              </div>
            </div>
            <div className="xlsx-info">
              {data.xlsx ? (
                <div>
                  <p>📊 Excel file ready for download</p>
                  <p>Size: {(data.xlsx.size / 1024).toFixed(1)} KB</p>
                  <p>Contains multiple sheets with schedule data, fairness report, and decision log</p>
                </div>
              ) : (
                <p>No Excel data available</p>
              )}
            </div>
          </div>
        );

      case 'json':
        return (
          <div className="tab-content">
            <div className="content-header">
              <h4>JSON Data</h4>
              <div className="header-actions">
                {data.json && (
                  <>
                    <button 
                      className="copy-btn"
                      onClick={() => handleCopyToClipboard(JSON.stringify(data.json, null, 2), 'JSON')}
                    >
                      {copySuccess === 'JSON' ? '✓ Copied!' : '📋 Copy'}
                    </button>
                    {onDownload && (
                      <button 
                        className="download-btn"
                        onClick={() => onDownload('json')}
                      >
                        Download JSON
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
            <pre className="content-preview">
              {data.json ? JSON.stringify(data.json, null, 2) : 'No JSON data available'}
            </pre>
          </div>
        );

      case 'fairness':
        return (
          <div className="tab-content">
            <div className="content-header">
              <h4>Fairness Report</h4>
              {data.fairnessReport && (
                <button 
                  className="copy-btn"
                  onClick={() => handleCopyToClipboard(JSON.stringify(data.fairnessReport, null, 2), 'Fairness Report')}
                >
                  {copySuccess === 'Fairness Report' ? '✓ Copied!' : '📋 Copy'}
                </button>
              )}
            </div>
            <div className="fairness-content" data-testid="fairness-report">
              {data.fairnessReport ? (
                <pre className="content-preview">
                  {JSON.stringify(data.fairnessReport, null, 2)}
                </pre>
              ) : (
                <p>No fairness report available</p>
              )}
            </div>
          </div>
        );

      case 'decisions':
        return (
          <div className="tab-content">
            <div className="content-header">
              <h4>Decision Log</h4>
              {data.decisionLog && (
                <button 
                  className="copy-btn"
                  onClick={() => handleCopyToClipboard(JSON.stringify(data.decisionLog, null, 2), 'Decision Log')}
                >
                  {copySuccess === 'Decision Log' ? '✓ Copied!' : '📋 Copy'}
                </button>
              )}
            </div>
            <div className="decisions-content" data-testid="decision-log">
              {data.decisionLog && data.decisionLog.length > 0 ? (
                <pre className="content-preview">
                  {JSON.stringify(data.decisionLog, null, 2)}
                </pre>
              ) : (
                <p>No decision log available</p>
              )}
            </div>
          </div>
        );

      default:
        return <div>Select a tab to view content</div>;
    }
  };

  const tabs = [
    { id: 'csv' as TabType, label: 'CSV', icon: '📄' },
    { id: 'xlsx' as TabType, label: 'Excel', icon: '📊' },
    { id: 'json' as TabType, label: 'JSON', icon: '🔧' },
    { id: 'fairness' as TabType, label: 'Fairness', icon: '⚖️' },
    { id: 'decisions' as TabType, label: 'Decisions', icon: '📝' }
  ];

  return (
    <div className="artifact-panel-overlay">
      <div className="artifact-panel" data-testid="artifact-panel">
        <div className="panel-header">
          <h3>Generated Artifacts</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="tab-bar">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>
          ))}
        </div>

        <div className="panel-content">
          {renderTabContent()}
        </div>
      </div>

      <style jsx>{`
        .artifact-panel-overlay {
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

        .artifact-panel {
          background: white;
          border-radius: 12px;
          width: 90vw;
          max-width: 1000px;
          height: 80vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px 24px;
          border-bottom: 1px solid #e5e7eb;
        }

        .panel-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 20px;
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
          color: #6b7280;
        }

        .close-btn:hover {
          background: #f3f4f6;
          color: #374151;
        }

        .tab-bar {
          display: flex;
          border-bottom: 1px solid #e5e7eb;
          background: #f9fafb;
        }

        .tab {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 20px;
          border: none;
          background: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          color: #6b7280;
          border-bottom: 2px solid transparent;
          transition: all 0.2s;
        }

        .tab:hover {
          color: #374151;
          background: #f3f4f6;
        }

        .tab.active {
          color: #3b82f6;
          border-bottom-color: #3b82f6;
          background: white;
        }

        .tab-icon {
          font-size: 16px;
        }

        .panel-content {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        .tab-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .content-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
          border-bottom: 1px solid #e5e7eb;
          background: #f9fafb;
        }

        .header-actions {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .content-header h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #111827;
        }

        .copy-btn {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .copy-btn:hover {
          background: #2563eb;
        }

        .download-btn {
          background: #10b981;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .download-btn:hover {
          background: #059669;
        }

        .content-preview {
          flex: 1;
          padding: 20px 24px;
          margin: 0;
          overflow: auto;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 12px;
          line-height: 1.5;
          background: #f8fafc;
          white-space: pre-wrap;
          word-wrap: break-word;
        }

        .xlsx-info {
          padding: 20px 24px;
        }

        .xlsx-info p {
          margin: 8px 0;
          color: #374151;
        }

        .fairness-content,
        .decisions-content {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        @media (max-width: 768px) {
          .artifact-panel {
            width: 95vw;
            height: 90vh;
          }
          
          .tab {
            padding: 10px 12px;
            font-size: 12px;
          }
          
          .tab-label {
            display: none;
          }
          
          .content-preview {
            font-size: 11px;
            padding: 16px;
          }
        }
      `}</style>
    </div>
  );
};