# Team Scheduler - Advanced Engineering Team Scheduling System

A comprehensive team scheduling application built with Next.js frontend and Python serverless backend, designed to manage complex engineering team rotations with intelligent role assignments and conflict avoidance.

## 🚀 Features

- **Smart Role Assignment**: Automated assignment of On-Call, Contacts, Appointments, Early Shifts, and Tickets
- **Conflict Prevention**: On-call engineers automatically excluded from weekend work during their on-call week
- **Fair Rotation**: Configurable seed-based rotation system ensures equitable workload distribution
- **Leave Management**: Full support for time-off requests with automatic schedule adjustments
- **Multiple Export Formats**: CSV and Excel export capabilities
- **Responsive UI**: Clean, intuitive interface for schedule configuration

## 📋 Requirements

- **Team Size**: 5-8 engineers supported (optimal: 6-7)
- **Schedule Pattern**: Week starts on Sunday with alternating weekend coverage
- **Roles Covered**: On-Call (weekly), Contacts (daily), Appointments (daily), Early Shifts (1-2 engineers), Tickets (remaining)
- **Smart Scaling**: Role assignments automatically adjust based on team size

## 🛠️ Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Vercel account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/creedlife11/vercel-scheduler-repo.git
   cd vercel-scheduler-repo
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open application**
   Navigate to `http://localhost:3000`

### Deployment to Vercel

1. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel auto-detects Next.js and Python configuration

2. **Deploy**
   - Click "Deploy"
   - Vercel handles both frontend and serverless function deployment automatically

## 📡 API Documentation

### Endpoint: `POST /api/generate`

Generates a team schedule based on provided parameters.

#### Request Body
```json
{
  "engineers": ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank"],
  "start_sunday": "2025-08-10",
  "weeks": 8,
  "seeds": {
    "weekend": 0,
    "oncall": 1,
    "contacts": 2,
    "appointments": 3,
    "early": 0
  },
  "leave": [
    {
      "Engineer": "Alice",
      "Date": "2025-09-02",
      "Reason": "PTO"
    }
  ],
  "format": "csv"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `engineers` | Array[String] | Yes | 5-8 engineer names |
| `start_sunday` | String | Yes | Start date in YYYY-MM-DD format (must be Sunday) |
| `weeks` | Number | Yes | Number of weeks to schedule (1-52) |
| `seeds` | Object | No | Rotation starting points for fair distribution |
| `leave` | Array[Object] | No | Leave requests with Engineer, Date, Reason |
| `format` | String | No | Export format: "csv" or "json" (default: "csv") |
| `include_fairness` | Boolean | No | Include fairness analysis in CSV output |

#### Response

**Success (200)**
- Content-Type: `text/csv` or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Body: Generated schedule file

**Error Responses**
- `400`: Invalid input (missing engineers, wrong date format, etc.)
- `500`: Internal server error

#### Example Response Structure (CSV)
```csv
Date,Day,WeekIndex,OnCall,Contacts,Appointments,Early1,Early2,Tickets,1) Engineer,Status 1,Assignment 1,Shift 1,...
2025-08-10,Sun,0,,,,,,,Alice,WORK,Weekend Coverage,Weekend,...
2025-08-11,Mon,0,Bob,Carol,Dan,Eve,Frank,Alice,Alice,WORK,Tickets,08:00-17:00,...

# Warnings:
# Team size (5) is below optimal. Consider adding more engineers for better coverage.
# Fairness Summary:
# oncall_days: green (delta: 1, gini: 0.067)
```

#### Example Response Structure (JSON)
```json
{
  "schedule": [...],
  "metadata": {
    "team_size": 6,
    "role_config": {"oncall": 1, "early_shifts": 2, "contacts": 1, "appointments": 1, "min_tickets": 2},
    "warnings": [],
    "fairness": {
      "oncall_days": {"badge": "green", "delta": 1, "gini": 0.067, "counts": {...}},
      "early_shifts": {"badge": "green", "delta": 0, "gini": 0.000, "counts": {...}}
    },
    "generated_at": "2025-01-20T10:30:00Z",
    "request_id": "abc123"
  }
}
```

## 🔧 Configuration

### Rotation Seeds
Seeds control the starting position for each role rotation, ensuring fair distribution:

- **weekend**: Weekend coverage rotation starting point
- **oncall**: Weekly on-call assignment starting point  
- **contacts**: Daily contacts rotation starting point
- **appointments**: Daily appointments rotation starting point
- **early**: Early shift rotation starting point

### Scheduling Rules

1. **Weekend Coverage Pattern**:
   - **Week A**: Monday, Tuesday, Wednesday, Thursday, Saturday
   - **Week B**: Sunday, Tuesday, Wednesday, Thursday, Friday

2. **Weekday Assignments**:
   - **On-Call**: One engineer per week (Monday-Friday, 06:45-15:45)
   - **Early Shift 2**: One additional engineer per week (Monday-Friday, 06:45-15:45)
   - **Contacts**: One engineer per day (rotating, 08:00-17:00)
   - **Appointments**: One engineer per day (rotating, 08:00-17:00)
   - **Tickets**: Remaining engineers (08:00-17:00)

3. **Constraints**:
   - On-call engineers cannot work weekends during their on-call week
   - Engineers on leave are automatically excluded from all assignments
   - Fair rotation ensures balanced workload distribution

## 🧪 Testing

### Running Tests Locally
```bash
# Install test dependencies
npm install --dev

# Run unit tests
npm test

# Run with coverage
npm run test:coverage
```

## 🐛 Troubleshooting

### Common Issues

**"Exactly 6 engineers are required"**
- Ensure you have exactly 6 unique engineer names
- Check for empty strings or duplicate names

**"Invalid date format"**
- Use YYYY-MM-DD format
- Ensure start date is a Sunday
- Verify date is valid (not in the past, reasonable range)

**Schedule generation fails**
- Check that leave dates are in YYYY-MM-DD format
- Ensure seeds are numeric values
- Verify weeks parameter is between 1-52

**API returns 500 error**
- Check browser console for detailed error messages
- Verify all required fields are filled
- Try with default values first

### Getting Help

1. Check the browser console for detailed error messages
2. Verify your input matches the API documentation format
3. Try generating a schedule with minimal data first
4. Check that your start date is actually a Sunday

## 📁 Project Structure

```
├── api/
│   └── generate.py          # Python serverless function
├── pages/
│   └── index.tsx           # Main UI component
├── package.json            # Node.js dependencies
├── requirements.txt        # Python dependencies
├── tsconfig.json          # TypeScript configuration
└── README.md              # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🔄 Version History

- **v1.0**: Initial release with basic scheduling
- **v2.0**: Enhanced role assignments and conflict prevention
- **v2.1**: Improved error handling and validation
