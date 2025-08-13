# Team Scheduler on Vercel (Python API + Next.js UI)

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

If you want me to pre-fill your team names or customize the UI, say the word.
