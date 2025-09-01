import { NextApiRequest, NextApiResponse } from 'next'

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'enhanced-team-scheduler',
    version: '2.0.0'
  }

  res.status(200).json(health)
}