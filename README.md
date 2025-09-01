# Team Scheduler on Vercel (Python API + Next.js UI)

![CI/CD Pipeline](https://github.com/your-username/your-repo/workflows/CI/CD%20Pipeline/badge.svg)

This repo deploys a **Python serverless function** on Vercel to generate your team schedule (CSV/Excel) and a tiny **Next.js UI** to call it.

## Deploy (GitHub + Vercel)
1. Create a new GitHub repo and push this folder.
2. In Vercel, **New Project → Import** your GitHub repo.
3. Vercel auto-detects Next.js for the frontend and installs Python deps for the function.
4. Click **Deploy**.

### Local dev
```bash
# Frontend
npm install
npm run dev
# open http://localhost:3000

# Test Python function locally (optional, requires vercel CLI or any WSGI runner)
```

## API
`POST /api/generate`

### JSON body
```json
{
  "engineers": ["Alice","Bob","Carol","Dan","Eve","Frank"],
  "start_sunday": "2025-08-10",
  "weeks": 8,
  "seeds": {"weekend":0,"chat":0,"oncall":1,"appointments":2,"early":0},
  "leave": [{"Engineer":"Alice","Date":"2025-09-02","Reason":"PTO"}],
  "format": "csv"   // or "xlsx"
}
```

### Response
- `text/csv` with `schedule.csv` or
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` with `schedule.xlsx`

## Files
- `api/generate.py` – Python serverless function
- `schedule_core.py` – scheduling logic (shared)
- `requirements.txt` – Python deps (pandas, openpyxl)
- `vercel.json` – set Python runtime and limits
- `pages/index.tsx` – minimal UI
- `package.json` – Next.js front-end

## Notes
- Exactly **6 engineers** are required.
- Week starts on **Sunday**.
- Weekend coverage pattern:
  - **Week A**: Mon, Tue, Wed, Thu, **Sat**
  - **Week B** (following week): **Sun**, Tue, Wed, Thu, Fri
- Weekday roles: **Chat, OnCall, Appointments**; plus **two Early shifts** (06:45–15:45).
- Others default to 08:00–17:00 on weekdays; "Weekend" on weekends.

## Development & Testing

### CI/CD Pipeline
This project uses a dual-lane CI/CD pipeline with comprehensive testing:

**Python Test Lane:**
- pytest with 90% coverage requirement for scheduling core
- ruff for linting and code formatting
- mypy for type checking
- Security scanning with Trivy

**Node.js Test Lane:**
- Jest for unit testing with coverage reporting
- TypeScript type checking
- ESLint for code quality
- Playwright for E2E testing

### Running Tests Locally

**Python tests:**
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Lint code
ruff check .
ruff format .

# Type check
mypy .
```

**Node.js tests:**
```bash
# Install dependencies
npm install

# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Lint code
npm run lint

# Type check
npm run type-check

# Run E2E tests
npm run test:e2e
```

### Coverage Requirements
- Python scheduling core: ≥90% coverage
- TypeScript/React components: ≥80% coverage
- All tests must pass before deployment

## Documentation

### User Guides
- [API Documentation](docs/API.md) - Complete API reference
- [Known Limitations](docs/LIMITATIONS.md) - Current system constraints

### Deployment and Operations
- [Deployment Guide](docs/DEPLOYMENT.md) - Complete deployment instructions
- [Feature Flag Configuration](docs/FEATURE_FLAGS.md) - Feature flag management
- [Operations Runbook](docs/OPERATIONS.md) - Day-to-day operational procedures
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

### Development
- [OpenAPI Specification](docs/openapi.yaml) - Machine-readable API spec

## Enhanced Features

This application includes comprehensive enhancements for enterprise use:

### Core Enhancements
- **Enhanced Schedule Generation**: Comprehensive decision logging and fairness analysis
- **JSON-First Export System**: Single source of truth for all export formats (CSV, XLSX, JSON)
- **Dual Validation**: Frontend (Zod) and backend (Pydantic) validation with real-time feedback
- **Invariant Checking**: Automatic validation of scheduling rules and data integrity

### User Experience
- **Artifact Panel**: Tabbed interface for viewing CSV, XLSX, JSON, fairness reports, and decision logs
- **Leave Management**: CSV/XLSX import with conflict detection and preview
- **Preset Manager**: Save and load common configuration sets
- **Smart Date Picker**: Automatic Sunday detection and snapping

### Enterprise Features
- **Authentication System**: NextAuth.js integration with role-based access control
- **Team Storage**: Team-scoped artifact storage and sharing
- **Rate Limiting**: Configurable request limits and security controls
- **Performance Monitoring**: Comprehensive timing and memory usage tracking
- **Structured Logging**: JSON-formatted logs with request ID tracking

### Reliability and Operations
- **Feature Flag System**: Gradual rollout capabilities with Vercel Edge Config
- **Health Endpoints**: `/api/healthz`, `/api/readyz`, and `/api/metrics` for monitoring
- **Security Headers**: Comprehensive security controls and CORS configuration
- **Deployment Automation**: Environment-specific configuration and validation

If you want me to pre-fill your team names or customize the UI, say the word.
