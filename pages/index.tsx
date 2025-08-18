import { useState } from 'react'

interface ValidationError {
  field: string;
  message: string;
}

export default function Home() {
  const [engineers, setEngineers] = useState(['Alice', 'Bob', 'Carol', 'Dan', 'Eve', 'Frank'])
  const [startDate, setStartDate] = useState('2025-08-10')
  const [weeks, setWeeks] = useState(8)
  const [format, setFormat] = useState('csv')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<ValidationError[]>([])
  const [apiError, setApiError] = useState<string>('')
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

  const validateForm = (): ValidationError[] => {
    const validationErrors: ValidationError[] = []
    
    // Validate engineers
    if (engineers.length !== 6) {
      validationErrors.push({ field: 'engineers', message: 'Exactly 6 engineers are required' })
    }
    
    engineers.forEach((engineer, index) => {
      if (!engineer.trim()) {
        validationErrors.push({ field: 'engineers', message: `Engineer ${index + 1} cannot be empty` })
      } else if (engineer.trim().length > 50) {
        validationErrors.push({ field: 'engineers', message: `Engineer ${index + 1} name too long (max 50 characters)` })
      }
    })
    
    // Check for duplicate engineers
    const uniqueEngineers = new Set(engineers.map(e => e.trim().toLowerCase()))
    if (uniqueEngineers.size !== engineers.length) {
      validationErrors.push({ field: 'engineers', message: 'Engineer names must be unique' })
    }
    
    // Validate start date
    if (!startDate) {
      validationErrors.push({ field: 'startDate', message: 'Start date is required' })
    } else {
      const date = new Date(startDate)
      if (isNaN(date.getTime())) {
        validationErrors.push({ field: 'startDate', message: 'Invalid date format' })
      } else if (date.getDay() !== 0) {
        validationErrors.push({ field: 'startDate', message: 'Start date must be a Sunday' })
      }
    }
    
    // Validate weeks
    if (weeks < 1 || weeks > 52) {
      validationErrors.push({ field: 'weeks', message: 'Weeks must be between 1 and 52' })
    }
    
    // Validate seeds
    Object.entries(seeds).forEach(([key, value]) => {
      if (value < 0 || value > 5) {
        validationErrors.push({ field: 'seeds', message: `${key} seed must be between 0 and 5` })
      }
    })
    
    return validationErrors
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
    // Clear previous errors
    setErrors([])
    setApiError('')
    
    // Validate form
    const validationErrors = validateForm()
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }
    
    setLoading(true)
    try {
      const leaveData = parseLeaveData(leave)
      
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          engineers: engineers.map(e => e.trim()),
          start_sunday: startDate,
          weeks,
          seeds,
          leave: leaveData,
          format
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          code: 'UNKNOWN_ERROR',
          message: 'Unknown error occurred',
          requestId: 'unknown'
        }))
        
        // Handle new error format
        const errorMessage = errorData.message || errorData.error || `HTTP error! status: ${response.status}`
        const errorDetails = errorData.details ? `\n\nDetails:\n${errorData.details.join('\n')}` : ''
        const requestId = errorData.requestId ? `\n\nRequest ID: ${errorData.requestId}` : ''
        
        throw new Error(`${errorMessage}${errorDetails}${requestId}`)
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
      setApiError(error instanceof Error ? error.message : 'Unknown error occurred')
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

      {/* Error Display */}
      {errors.length > 0 && (
        <div style={{ 
          marginBottom: '20px', 
          padding: '15px', 
          backgroundColor: '#fee', 
          border: '1px solid #fcc',
          borderRadius: '5px'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#c33' }}>Validation Errors:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {errors.map((error, index) => (
              <li key={index} style={{ color: '#c33' }}>{error.message}</li>
            ))}
          </ul>
        </div>
      )}

      {apiError && (
        <div style={{ 
          marginBottom: '20px', 
          padding: '15px', 
          backgroundColor: '#fee', 
          border: '1px solid #fcc',
          borderRadius: '5px'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#c33' }}>Error:</h4>
          <p style={{ margin: 0, color: '#c33' }}>{apiError}</p>
        </div>
      )}

      <button
        onClick={generateSchedule}
        disabled={loading}
        style={{
          padding: '15px 30px',
          fontSize: '16px',
          backgroundColor: loading ? '#ccc' : (errors.length > 0 ? '#f39c12' : '#007cba'),
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
          <li>Weekday roles: On-Call (weekly, 06:45-15:45), Early Shift 2 (weekly, 06:45-15:45), Contacts (daily), Appointments (daily)</li>
          <li>On-call and Early Shift 2 engineers cannot work weekend during their assigned week</li>
          <li>Remaining engineers work on Tickets (08:00-17:00)</li>
          <li>Seeds control rotation starting points for fair distribution</li>
        </ul>
      </div>
    </div>
  )
}