import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  res.status(200).json({
    message: 'API is working',
    method: req.method,
    timestamp: new Date().toISOString()
  });
}