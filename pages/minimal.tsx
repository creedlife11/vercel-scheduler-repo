export default function MinimalPage() {
  return (
    <div style={{ 
      padding: '40px', 
      fontFamily: 'Arial, sans-serif',
      maxWidth: '600px',
      margin: '0 auto'
    }}>
      <h1>Enhanced Team Scheduler - Minimal Test</h1>
      <p>If you can see this page, the deployment is working!</p>
      
      <div style={{ 
        padding: '20px', 
        backgroundColor: '#f0f9ff', 
        borderRadius: '8px',
        marginTop: '20px'
      }}>
        <h3>✅ Deployment Status: SUCCESS</h3>
        <p>The Enhanced Team Scheduler is deployed and ready.</p>
        
        <h4>Next Steps:</h4>
        <ul>
          <li>Test the simple health API: <code>/api/simple-health</code></li>
          <li>Try the full scheduler: <code>/simple</code></li>
          <li>Test schedule generation: <code>/api/generate</code></li>
        </ul>
      </div>
      
      <div style={{ marginTop: '30px' }}>
        <button 
          onClick={() => {
            fetch('/api/simple-health')
              .then(res => res.json())
              .then(data => alert('API Test: ' + JSON.stringify(data, null, 2)))
              .catch(err => alert('API Error: ' + err.message));
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Test API Connection
        </button>
      </div>
    </div>
  );
}