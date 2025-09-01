import { NextApiRequest, NextApiResponse } from 'next'

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  // Check if the application is ready to serve requests
  const readiness = {
    status: 'ready',
    timestamp: new Date().toISOString(),
    service: 'enhanced-team-scheduler',
    checks: {
      environment: process.env.NODE_ENV || 'development',
      nextauth: !!process.env.NEXTAUTH_SECRET,
      features: true
    }
  }

  res.status(200).json(readiness)
}