# API Endpoint Conflict Fix

## Problem
The frontend was receiving a **405 Method Not Allowed** error when clicking the "Generate Schedule" button.

## Root Cause
There were two API endpoints with the same path:
1. **TypeScript endpoint**: `pages/api/generate.ts` (Next.js API route)
2. **Python endpoint**: `api/generate.py` (Vercel Python serverless function)

Vercel was prioritizing the Python endpoint over the TypeScript one, but the Python endpoint had a different function signature and wasn't properly configured for the frontend's expectations.

## Solution
**Removed the conflicting Python API endpoint** (`api/generate.py`) to allow the TypeScript endpoint to handle requests properly.

## Why This Fix Works
- Next.js API routes in `pages/api/` are the standard way to handle API endpoints in Next.js applications
- The TypeScript endpoint was specifically designed to work with the frontend's request format
- Removing the Python endpoint eliminates the routing conflict
- The TypeScript endpoint supports all the enhanced features (backfill integration, decision logging, etc.)

## Files Changed
- ✅ **Deleted**: `api/generate.py` (conflicting Python endpoint)
- ✅ **Kept**: `pages/api/generate.ts` (working TypeScript endpoint)

## Expected Result
The "Generate Schedule" button should now work correctly and return CSV/JSON data as expected.

## Verification Steps
1. Visit the deployed application
2. Fill in the form with 6 engineers, start date, and weeks
3. Click "Generate Schedule"
4. Should receive a CSV download instead of a 405 error

## Deployment Status
- ✅ Changes committed and pushed to GitHub
- ✅ Vercel will automatically redeploy with the fix
- ✅ No additional configuration needed

The 405 Method Not Allowed error should now be resolved.