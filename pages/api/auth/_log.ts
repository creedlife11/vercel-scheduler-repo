import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  // Just return OK for logging endpoint
  res.status(200).json({ ok: true });
}