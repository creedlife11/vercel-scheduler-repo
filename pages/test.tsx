import React, { useState } from 'react';
import { EngineerInput } from '../lib/components/EngineerInput';
import { SmartDatePicker } from '../lib/components/SmartDatePicker';
import { WeeksInput } from '../lib/components/WeeksInput';

export default function TestPage() {
  const [engineers, setEngineers] = useState<string[]>([]);
  const [startSunday, setStartSunday] = useState<string>('');
  const [weeks, setWeeks] = useState<number>(4);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          engineers,
          start_sunday: startSunday,
          weeks,
          format: 'json'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Generation failed:', error);
      alert('Failed to generate schedule: ' + error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f9fafb', 
      padding: '48px 16px',
      fontFamily: 'Inter, system-ui, Arial'
    }}>
      <div style={{ maxWidth: '1024px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ fontSize: 30, fontWeight: 'bold', color: '#111827', margin: 0 }}>
            Enhanced Team Scheduler - Test Page
          </h1>
          <p style={{ marginTop: 8, color: '#6b7280' }}>
            Testing the scheduler functionality without authentication
          </p>
        </div>

        <div style={{ 
          backgroundColor: 'white', 
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)', 
          borderRadius: 8, 
          padding: 24 
        }}>
          <div style={{ marginBottom: 24 }}>
            <label style={{ 
              display: 'block', 
              fontSize: 14, 
              fontWeight: 500, 
              color: '#374151', 
              marginBottom: 8 
            }}>
              Engineers
            </label>
            <EngineerInput
              value={engineers}
              onChange={setEngineers}
              placeholder="Enter engineer names (comma-separated)"
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ 
              display: 'block', 
              fontSize: 14, 
              fontWeight: 500, 
              color: '#374151', 
              marginBottom: 8 
            }}>
              Start Date (Sunday)
            </label>
            <SmartDatePicker
              value={startSunday}
              onChange={setStartSunday}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ 
              display: 'block', 
              fontSize: 14, 
              fontWeight: 500, 
              color: '#374151', 
              marginBottom: 8 
            }}>
              Number of Weeks
            </label>
            <WeeksInput
              value={weeks}
              onChange={setWeeks}
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating || engineers.length === 0 || !startSunday}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              padding: '8px 16px',
              border: 'none',
              borderRadius: 6,
              boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
              fontSize: 14,
              fontWeight: 500,
              color: 'white',
              backgroundColor: isGenerating || engineers.length === 0 || !startSunday ? '#9ca3af' : '#2563eb',
              cursor: isGenerating || engineers.length === 0 || !startSunday ? 'not-allowed' : 'pointer'
            }}
          >
            {isGenerating ? 'Generating...' : 'Generate Schedule'}
          </button>

          {result && (
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 18, fontWeight: 500, color: '#111827', marginBottom: 8 }}>
                Generated Schedule
              </h3>
              <pre style={{ 
                backgroundColor: '#f3f4f6', 
                padding: 16, 
                borderRadius: 6, 
                overflow: 'auto', 
                fontSize: 14,
                whiteSpace: 'pre-wrap'
              }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}