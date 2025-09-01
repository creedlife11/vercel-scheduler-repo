import { getServerSession } from "next-auth/next"
import { authOptions } from "../pages/api/auth/[...nextauth]"
import { NextApiRequest, NextApiResponse } from "next"
import { prisma } from "./prisma"

export type UserRole = "VIEWER" | "EDITOR" | "ADMIN"

export interface AuthenticatedUser {
  id: string
  email: string
  name?: string
  role: UserRole
  teams: Array<{
    id: string
    name: string
    role: string
  }>
}

export async function getAuthenticatedUser(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<AuthenticatedUser | null> {
  const session = await getServerSession(req, res, authOptions)
  
  if (!session?.user) {
    return null
  }

  return session.user as AuthenticatedUser
}

export function requireAuth(handler: Function) {
  return async (req: NextApiRequest, res: NextApiResponse) => {
    const user = await getAuthenticatedUser(req, res)
    
    if (!user) {
      return res.status(401).json({ 
        error: "Authentication required",
        code: "UNAUTHORIZED"
      })
    }

    // Add user to request object for use in handler
    ;(req as any).user = user
    
    return handler(req, res)
  }
}

export function requireRole(roles: UserRole[]) {
  return (handler: Function) => {
    return requireAuth(async (req: NextApiRequest, res: NextApiResponse) => {
      const user = (req as any).user as AuthenticatedUser
      
      if (!roles.includes(user.role)) {
        return res.status(403).json({
          error: "Insufficient permissions",
          code: "FORBIDDEN",
          required: roles,
          current: user.role
        })
      }
      
      return handler(req, res)
    })
  }
}

export function requireTeamAccess(teamId?: string) {
  return (handler: Function) => {
    return requireAuth(async (req: NextApiRequest, res: NextApiResponse) => {
      const user = (req as any).user as AuthenticatedUser
      
      // Admin users have access to all teams
      if (user.role === "ADMIN") {
        return handler(req, res)
      }
      
      // If no specific team required, just check authentication
      if (!teamId) {
        return handler(req, res)
      }
      
      // Check if user has access to the specific team
      const hasAccess = user.teams.some(team => team.id === teamId)
      
      if (!hasAccess) {
        return res.status(403).json({
          error: "Team access denied",
          code: "TEAM_ACCESS_DENIED",
          teamId
        })
      }
      
      return handler(req, res)
    })
  }
}

export async function logAuditEvent(
  userId: string,
  action: string,
  resource?: string,
  metadata?: any,
  req?: NextApiRequest
) {
  try {
    await prisma.auditLog.create({
      data: {
        userId,
        action,
        resource,
        metadata: metadata ? JSON.stringify(metadata) : null,
        ipAddress: req ? getClientIP(req) : null,
        userAgent: req?.headers['user-agent'] || null
      }
    })
  } catch (error) {
    console.error('Failed to log audit event:', error)
  }
}

function getClientIP(req: NextApiRequest): string {
  const forwarded = req.headers['x-forwarded-for']
  const ip = forwarded 
    ? (Array.isArray(forwarded) ? forwarded[0] : forwarded.split(',')[0])
    : req.connection?.remoteAddress || req.socket?.remoteAddress || 'unknown'
  
  return ip
}