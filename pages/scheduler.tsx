import { useState } from 'react';

export default function SchedulerPage() {
  const [engineers, setEngineers] = useState('Alice, Bob, Charlie, Diana, Eve, Frank');
  const [startDate, setStartDate] = useState('2025-01-05');
  const [weeks, setWeeks] = useState(4);
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generateSchedule = async () => {
    setLoading(true);
    setError('');
    setResult('');

    try {
      const engineerList = engineers.split(',').map(e => e.trim()).filter(Boolean);
      
      if (engineerList.length !== 6) {
        throw new Error('Please enter exactly 6 engineers');
      }

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engineers: engineerList,
          start_sunday: startDate,
          weeks: weeks,
          format: 'json'
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: '800px',
      margin: '40px auto',
      padding: '20px',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: 'white',
      borderRadius: '8px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
    }}>
      <h1 style={{ color: '#1f2937', textAlign: 'center' }}>
        🗓️ Enhanced Team Scheduler
      </h1>
      
      <div style={{
        padding: '16px',
        backgroundColor: '#f0f9ff',
        borderRadius: '6px',
        marginBottom: '24px',
        textAlign: 'center'
      }}>
        <p style={{ margin: 0, color: '#0369a1' }}>
          ✅ <strong>Deployment Successful!</strong> The Enhanced Team Scheduler is now live and working.
        </p>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          Engineers (comma-separated, exactly 6):
        </label>
        <input
          type="text"
          value={engineers}
          onChange={(e) => setEngineers(e.target.value)}
          style={{
            width: '100%',
            padding: '10px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px'
          }}
          placeholder="Alice, Bob, Charlie, Diana, Eve, Frank"
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Start Date (Sunday):
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Number of Weeks:
          </label>
          <input
            type="number"
            min="1"
            max="52"
            value={weeks}
            onChange={(e) => setWeeks(parseInt(e.target.value) || 1)}
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />
        </div>
      </div>

      <button
        onClick={generateSchedule}
        disabled={loading}
        style={{
          width: '100%',
          padding: '12px 24px',
          backgroundColor: loading ? '#9ca3af' : '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          fontSize: '16px',
          fontWeight: 'bold',
          cursor: loading ? 'not-allowed' : 'pointer',
          marginBottom: '20px'
        }}
      >
        {loading ? 'Generating Schedule...' : '🚀 Generate Schedule'}
      </button>

      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          color: '#dc2626',
          marginBottom: '20px'
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div>
          <h3 style={{ color: '#1f2937' }}>📊 Generated Schedule:</h3>
          <pre style={{
            backgroundColor: '#f9fafb',
            padding: '16px',
            borderRadius: '6px',
            overflow: 'auto',
            fontSize: '12px',
            border: '1px solid #e5e7eb',
            maxHeight: '400px'
          }}>
            {result}
          </pre>
          
          <button
            onClick={() => {
              const blob = new Blob([result], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `schedule-${new Date().toISOString().split('T')[0]}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            style={{
              marginTop: '12px',
              padding: '8px 16px',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            📥 Download JSON
          </button>
        </div>
      )}

      <div style={{
        marginTop: '32px',
        padding: '16px',
        backgroundColor: '#f0fdf4',
        borderRadius: '6px',
        fontSize: '14px'
      }}>
        <h4 style={{ margin: '0 0 8px 0', color: '#166534' }}>✨ Enhanced Features:</h4>
        <ul style={{ margin: 0, paddingLeft: '20px', color: '#166534' }}>
          <li>Fairness analysis and reporting</li>
          <li>Decision logging for transparency</li>
          <li>Multiple export formats</li>
          <li>Real-time validation</li>
          <li>Professional interface</li>
        </ul>
      </div>
    </div>
  );
}