import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Return a mock session for now
  res.status(200).json({
    user: {
      id: 'demo-user',
      email: 'demo@example.com',
      name: 'Demo User',
      role: 'ADMIN'
    },
    expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
  });
}