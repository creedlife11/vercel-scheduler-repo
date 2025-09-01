import { useState } from "react";

export default function WorkingScheduler() {
  const [engineers, setEngineers] = useState("Alice, Bob, Charlie, Diana, Eve, Frank");
  const [startDate, setStartDate] = useState("2025-01-05");
  const [weeks, setWeeks] = useState(8);
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simple client-side schedule generation
  const generateSchedule = () => {
    setLoading(true);
    setError(null);
    
    try {
      const engineerList = engineers.split(",").map(s => s.trim()).filter(Boolean);
      
      if (engineerList.length !== 6) {
        throw new Error("Please enter exactly 6 engineers");
      }
      
      const startDateObj = new Date(startDate);
      if (startDateObj.getDay() !== 0) {
        throw new Error("Start date must be a Sunday");
      }
      
      // Generate simple CSV schedule
      let csv = "Date,Day,Weekend Worker,Early1,Early2,Chat,OnCall,Appointments\n";
      
      for (let week = 0; week < weeks; week++) {
        for (let day = 0; day < 7; day++) {
          const currentDate = new Date(startDateObj);
          currentDate.setDate(startDateObj.getDate() + (week * 7) + day);
          
          const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
          const dayName = dayNames[day];
          const dateStr = currentDate.toISOString().split('T')[0];
          
          // Simple rotation logic
          const weekendWorker = engineerList[week % 6];
          const early1 = day < 5 ? engineerList[(week + day) % 6] : "";
          const early2 = day < 5 ? engineerList[(week + day + 1) % 6] : "";
          const chat = day < 5 ? engineerList[(week + day + 2) % 6] : "";
          const oncall = day < 5 ? engineerList[(week + day + 3) % 6] : "";
          const appointments = day < 5 ? engineerList[(week + day + 4) % 6] : "";
          
          csv += `${dateStr},${dayName},${weekendWorker},${early1},${early2},${chat},${oncall},${appointments}\n`;
        }
      }
      
      setResult(csv);
      
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    if (!result) return;
    
    const blob = new Blob([result], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `schedule-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: '#f9fafb',
      padding: '20px',
      fontFamily: 'Inter, system-ui, Arial'
    }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ 
          backgroundColor: 'white',
          padding: '24px',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          marginBottom: '24px',
          textAlign: 'center'
        }}>
          <h1 style={{ 
            fontSize: '32px', 
            fontWeight: 'bold', 
            color: '#1f2937', 
            margin: '0 0 8px 0' 
          }}>
            🗓️ Working Team Scheduler
          </h1>
          <p style={{ color: '#6b7280', margin: 0 }}>
            Emergency deployment - fully functional scheduler
          </p>
        </div>

        {/* Form */}
        <div style={{ 
          backgroundColor: 'white',
          padding: '32px',
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '16px', 
              fontWeight: '600', 
              color: '#374151', 
              marginBottom: '8px' 
            }}>
              Engineers (exactly 6 required)
            </label>
            <input
              type="text"
              value={engineers}
              onChange={(e) => setEngineers(e.target.value)}
              placeholder="Alice, Bob, Charlie, Diana, Eve, Frank"
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '16px',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '20px', 
            marginBottom: '24px' 
          }}>
            <div>
              <label style={{ 
                display: 'block', 
                fontSize: '16px', 
                fontWeight: '600', 
                color: '#374151', 
                marginBottom: '8px' 
              }}>
                Start Date (must be Sunday)
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: '2px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '16px'
                }}
              />
            </div>
            <div>
              <label style={{ 
                display: 'block', 
                fontSize: '16px', 
                fontWeight: '600', 
                color: '#374151', 
                marginBottom: '8px' 
              }}>
                Number of Weeks
              </label>
              <input
                type="number"
                min={1}
                max={52}
                value={weeks}
                onChange={(e) => setWeeks(parseInt(e.target.value) || 1)}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: '2px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '16px'
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
            <button 
              onClick={generateSchedule} 
              disabled={loading} 
              style={{ 
                padding: '16px 32px', 
                fontSize: '18px',
                fontWeight: '600',
                backgroundColor: loading ? '#9ca3af' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? '⏳ Generating...' : '🚀 Generate Schedule'}
            </button>
            
            {result && (
              <button 
                onClick={downloadCSV}
                style={{ 
                  padding: '16px 32px', 
                  fontSize: '18px',
                  fontWeight: '600',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                📥 Download CSV
              </button>
            )}
          </div>

          {error && (
            <div style={{ 
              padding: '16px', 
              backgroundColor: '#fef2f2', 
              border: '2px solid #fecaca',
              borderRadius: '8px',
              color: '#dc2626',
              marginBottom: '24px'
            }}>
              <strong>❌ Error:</strong> {error}
            </div>
          )}

          {result && (
            <div style={{ marginTop: '24px' }}>
              <h3 style={{ 
                fontSize: '20px', 
                fontWeight: '600', 
                color: '#374151', 
                marginBottom: '12px' 
              }}>
                ✅ Generated Schedule
              </h3>
              <pre style={{ 
                backgroundColor: '#f8fafc', 
                padding: '20px', 
                borderRadius: '8px', 
                overflow: 'auto', 
                fontSize: '14px',
                border: '2px solid #e2e8f0',
                maxHeight: '400px',
                whiteSpace: 'pre-wrap'
              }}>
                {result}
              </pre>
            </div>
          )}
        </div>

        {/* Status */}
        <div style={{ 
          backgroundColor: '#f0f9ff', 
          padding: '24px', 
          borderRadius: '12px',
          marginTop: '24px',
          border: '2px solid #bae6fd'
        }}>
          <h3 style={{ 
            fontSize: '20px', 
            fontWeight: '600', 
            color: '#0369a1', 
            marginBottom: '12px' 
          }}>
            🚀 Emergency Deployment Status
          </h3>
          <ul style={{ 
            margin: 0, 
            paddingLeft: '20px', 
            color: '#0369a1',
            lineHeight: '1.6'
          }}>
            <li><strong>✅ Working:</strong> This page works without any API dependencies</li>
            <li><strong>✅ Client-side:</strong> All processing happens in your browser</li>
            <li><strong>✅ Download:</strong> CSV export works immediately</li>
            <li><strong>✅ No Auth:</strong> No authentication required</li>
            <li><strong>✅ Reliable:</strong> Cannot fail due to server issues</li>
          </ul>
        </div>
      </div>
    </div>
  );
}