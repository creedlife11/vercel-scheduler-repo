import { NextApiRequest, NextApiResponse } from 'next'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '../auth/[...nextauth]'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = await getServerSession(req, res, authOptions)
  
  if (!session?.user) {
    return res.status(401).json({ error: 'Authentication required' })
  }

  const { params } = req.query
  const [action, ...rest] = Array.isArray(params) ? params : [params]

  try {
    switch (action) {
      case 'list':
        return handleListArtifacts(req, res, session.user)
      case 'get':
        if (!rest[0]) {
          return res.status(400).json({ error: 'Artifact ID required' })
        }
        return handleGetArtifact(req, res, session.user, rest[0])
      case 'delete':
        if (!rest[0]) {
          return res.status(400).json({ error: 'Artifact ID required' })
        }
        return handleDeleteArtifact(req, res, session.user, rest[0])
      default:
        return res.status(404).json({ error: 'Endpoint not found' })
    }
  } catch (error) {
    console.error('Artifacts API error:', error)
    return res.status(500).json({ error: 'Internal server error' })
  }
}

async function handleListArtifacts(req: NextApiRequest, res: NextApiResponse, user: any) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  // Get team ID from query or use user's first team
  const teamId = req.query.team_id as string || user.teams?.[0]?.id

  if (!teamId) {
    return res.status(400).json({ error: 'Team ID required' })
  }

  // Verify user has access to this team
  const hasAccess = user.role === 'ADMIN' || 
    user.teams?.some((team: any) => team.id === teamId)

  if (!hasAccess) {
    return res.status(403).json({ error: 'Team access denied' })
  }

  try {
    // This would call the Python team storage API
    const response = await fetch(`${process.env.NEXTAUTH_URL}/api/team-storage/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, limit: 50 })
    })

    if (!response.ok) {
      throw new Error('Failed to fetch artifacts')
    }

    const artifacts = await response.json()
    return res.status(200).json(artifacts)
  } catch (error) {
    return res.status(500).json({ error: 'Failed to list artifacts' })
  }
}

async function handleGetArtifact(req: NextApiRequest, res: NextApiResponse, user: any, artifactId: string) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  if (!artifactId) {
    return res.status(400).json({ error: 'Artifact ID required' })
  }

  const teamId = req.query.team_id as string || user.teams?.[0]?.id

  if (!teamId) {
    return res.status(400).json({ error: 'Team ID required' })
  }

  // Verify user has access to this team
  const hasAccess = user.role === 'ADMIN' || 
    user.teams?.some((team: any) => team.id === teamId)

  if (!hasAccess) {
    return res.status(403).json({ error: 'Team access denied' })
  }

  try {
    // This would call the Python team storage API
    const response = await fetch(`${process.env.NEXTAUTH_URL}/api/team-storage/get`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, artifact_id: artifactId })
    })

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Artifact not found' })
      }
      throw new Error('Failed to fetch artifact')
    }

    // Stream the artifact data
    const artifactData = await response.arrayBuffer()
    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const filename = response.headers.get('content-disposition')?.match(/filename="([^"]+)"/)?.[1] || 'artifact'

    res.setHeader('Content-Type', contentType)
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`)
    
    return res.status(200).send(Buffer.from(artifactData))
  } catch (error) {
    return res.status(500).json({ error: 'Failed to get artifact' })
  }
}

async function handleDeleteArtifact(req: NextApiRequest, res: NextApiResponse, user: any, artifactId: string) {
  if (req.method !== 'DELETE') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  // Only editors and admins can delete
  if (!['EDITOR', 'ADMIN'].includes(user.role)) {
    return res.status(403).json({ error: 'Insufficient permissions' })
  }

  if (!artifactId) {
    return res.status(400).json({ error: 'Artifact ID required' })
  }

  const teamId = req.query.team_id as string || user.teams?.[0]?.id

  if (!teamId) {
    return res.status(400).json({ error: 'Team ID required' })
  }

  // Verify user has access to this team
  const hasAccess = user.role === 'ADMIN' || 
    user.teams?.some((team: any) => team.id === teamId)

  if (!hasAccess) {
    return res.status(403).json({ error: 'Team access denied' })
  }

  try {
    // This would call the Python team storage API
    const response = await fetch(`${process.env.NEXTAUTH_URL}/api/team-storage/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        team_id: teamId, 
        artifact_id: artifactId,
        user_id: user.id
      })
    })

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Artifact not found' })
      }
      throw new Error('Failed to delete artifact')
    }

    return res.status(200).json({ success: true })
  } catch (error) {
    return res.status(500).json({ error: 'Failed to delete artifact' })
  }
}