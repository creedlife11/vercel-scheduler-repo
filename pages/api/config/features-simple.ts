import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const features = {
      enableArtifactPanel: true,
      enableLeaveManagement: true,
      enablePresetManager: true,
      maxWeeksAllowed: 52,
      enableFairnessReporting: true,
      enableDecisionLogging: true,
      enableAdvancedValidation: true
    };

    res.status(200).json({
      features,
      environment: process.env.VERCEL_ENV || 'development',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to load features',
      timestamp: new Date().toISOString()
    });
  }
}