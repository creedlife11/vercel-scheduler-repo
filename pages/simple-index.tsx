import Link from 'next/link';

export default function SimpleIndex() {
  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: '#f9fafb',
      padding: '20px',
      fontFamily: 'Inter, system-ui, Arial',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ 
        backgroundColor: 'white',
        padding: '48px',
        borderRadius: '12px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        textAlign: 'center',
        maxWidth: '600px'
      }}>
        <h1 style={{ 
          fontSize: '48px', 
          fontWeight: 'bold', 
          color: '#1f2937', 
          margin: '0 0 16px 0' 
        }}>
          🗓️ Team Scheduler
        </h1>
        
        <p style={{ 
          fontSize: '20px',
          color: '#6b7280', 
          margin: '0 0 32px 0',
          lineHeight: '1.6'
        }}>
          Generate fair and balanced team schedules with advanced algorithms
        </p>

        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          gap: '16px',
          alignItems: 'center'
        }}>
          <Link 
            href="/working-scheduler"
            style={{
              display: 'inline-block',
              padding: '16px 32px',
              fontSize: '18px',
              fontWeight: '600',
              backgroundColor: '#3b82f6',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '8px',
              transition: 'all 0.2s',
              minWidth: '200px'
            }}
          >
            🚀 Start Scheduling
          </Link>

          <div style={{ 
            fontSize: '14px',
            color: '#9ca3af',
            marginTop: '16px'
          }}>
            Emergency deployment - fully functional without API dependencies
          </div>
        </div>

        <div style={{ 
          marginTop: '32px',
          padding: '20px',
          backgroundColor: '#f0f9ff',
          borderRadius: '8px',
          border: '2px solid #bae6fd'
        }}>
          <h3 style={{ 
            fontSize: '18px',
            fontWeight: '600',
            color: '#0369a1',
            margin: '0 0 12px 0'
          }}>
            ✅ What Works
          </h3>
          <ul style={{ 
            textAlign: 'left',
            margin: 0,
            paddingLeft: '20px',
            color: '#0369a1',
            lineHeight: '1.6'
          }}>
            <li>Complete schedule generation</li>
            <li>6-engineer rotation system</li>
            <li>Weekend and weekday assignments</li>
            <li>CSV export and download</li>
            <li>No authentication required</li>
            <li>Works offline after loading</li>
          </ul>
        </div>
      </div>
    </div>
  );
}