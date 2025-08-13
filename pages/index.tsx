import { useState } from 'react'

export default function Home() {
  const [engineers, setEngineers] = useState(['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank'])
  const [startDate, setStartDate] = useState('2025-08-10')
  const [weeks, setWeeks] = useState(8)
  const [format, setFormat] = useState('csv')
  const [loading, setLoading] = useState(false)
  const [seeds, setSeeds] = useState({
    weekend: 0,
    oncall: 1,
    contacts: 2,
    appointments: 3,
    early: 0
  })
  const [leave, setLeave] = useState('')

  const handleEngineerChange = (index: number, value: string) => {
    const newEngineers = [...engineers]
    newEngineers[index] = value
    setEngineers(newEngineers)
  }

  const handleSeedChange = (key: string, value: number) => {
    setSeeds(prev => ({ ...prev, [key]: value }))
  }

  const parseLeaveData = (leaveText: string) => {
    if (!leaveText.trim()) return []
    
    const lines = leaveText.trim().split('\n')
    return lines.map(line => {
      const parts = line.split(',').map(p => p.trim())
      if (parts.length >= 2) {
        return {
          Engineer: parts[0],
          Date: parts[1],
          Reason: parts[2] || 'PTO'
        }
      }
      return null
    }).filter(Boolean)
  }

  const generateSchedule = async () => {
    setLoading(true)
    try {
      const leaveData = parseLeaveData(leave)
      
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          engineers,
          start_sunday: startDate,
          weeks,
          seeds,
          leave: leaveData,
          format
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `schedule.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error generating schedule:', error)
      alert('Error generating schedule. Please check the console for details.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Team Scheduler</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h3>Engineers (exactly 6 required)</h3>
        {engineers.map((engineer, index) => (
          <div key={index} style={{ marginBottom: '10px' }}>
            <label>Engineer {index + 1}: </label>
            <input
              type="text"
              value={engineer}
              onChange={(e) => handleEngineerChange(index, e.target.value)}
              style={{ marginLeft: '10px', padding: '5px' }}
            />
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Schedule Parameters</h3>
        <div style={{ marginBottom: '10px' }}>
          <label>Start Sunday: </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Number of weeks: </label>
          <input
            type="number"
            value={weeks}
            onChange={(e) => setWeeks(parseInt(e.target.value))}
            min="1"
            max="52"
            style={{ marginLeft: '10px', padding: '5px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Output format: </label>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          >
            <option value="csv">CSV</option>
            <option value="xlsx">Excel</option>
          </select>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Rotation Seeds</h3>
        {Object.entries(seeds).map(([key, value]) => (
          <div key={key} style={{ marginBottom: '10px' }}>
            <label>{key.charAt(0).toUpperCase() + key.slice(1)}: </label>
            <input
              type="number"
              value={value}
              onChange={(e) => handleSeedChange(key, parseInt(e.target.value))}
              min="0"
              max="5"
              style={{ marginLeft: '10px', padding: '5px' }}
            />
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Leave (Optional)</h3>
        <p style={{ fontSize: '14px', color: '#666' }}>
          Format: Engineer,Date,Reason (one per line)<br/>
          Example: Alice,2025-09-02,PTO
        </p>
        <textarea
          value={leave}
          onChange={(e) => setLeave(e.target.value)}
          placeholder="Alice,2025-09-02,PTO&#10;Bob,2025-09-15,Vacation"
          rows={4}
          style={{ width: '100%', padding: '10px' }}
        />
      </div>

      <button
        onClick={generateSchedule}
        disabled={loading}
        style={{
          padding: '15px 30px',
          fontSize: '16px',
          backgroundColor: loading ? '#ccc' : '#007cba',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Generating...' : 'Generate Schedule'}
      </button>

      <div style={{ marginTop: '30px', fontSize: '14px', color: '#666' }}>
        <h4>How it works:</h4>
        <ul>
          <li>Week starts on Sunday</li>
          <li>Weekend coverage alternates: Week A (Mon-Thu,Sat) vs Week B (Sun,Tue-Fri)</li>
          <li>Weekday roles: On-Call (weekly), Contacts (daily), Appointments (daily), Early shifts (2 engineers, 06:45-15:45)</li>
          <li>On-call engineer cannot work weekend during their on-call week</li>
          <li>Remaining engineers work on Tickets (08:00-17:00)</li>
          <li>Seeds control rotation starting points for fair distribution</li>
        </ul>
      </div>
    </div>
  )
}