import NextAuth, { NextAuthOptions, User } from "next-auth"
import { PrismaAdapter } from "@next-auth/prisma-adapter"
import { prisma } from "../../../lib/prisma"
import CredentialsProvider from "next-auth/providers/credentials"
import GoogleProvider from "next-auth/providers/google"

// Extend the built-in User type
declare module "next-auth" {
  interface User {
    role?: string
    teams?: { id: string; name: string; role: string }[]
  }
}

export const authOptions: NextAuthOptions = {
  // Only use PrismaAdapter if database is available
  ...(process.env.DATABASE_URL ? { adapter: PrismaAdapter(prisma) } : {}),
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        // Demo authentication - replace with proper authentication in production
        if (credentials.email === "demo@example.com" && credentials.password === "demo123") {
          return {
            id: "demo-user",
            email: credentials.email,
            name: "Demo User",
            role: "ADMIN",
            teams: [{ id: "demo-team", name: "Demo Team", role: "ADMIN" }]
          } as User
        }

        // For production with database
        if (process.env.DATABASE_URL && process.env.DATABASE_URL !== "file:./dev.db") {
          try {
            const user = await prisma.user.findUnique({
              where: { email: credentials.email },
              include: { teamMemberships: { include: { team: true } } }
            })

            if (user && credentials.password === "demo123") { // Replace with proper password verification
              return {
                id: user.id,
                email: user.email,
                name: user.name,
                role: user.role,
                teams: user.teamMemberships.map((tm: any) => ({
                  id: tm.team.id,
                  name: tm.team.name,
                  role: tm.role || 'MEMBER'
                }))
              } as User
            }
          } catch (error) {
            console.error('Database auth error:', error)
          }
        }

        return null
      }
    })
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = user.role
        token.teams = user.teams
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        (session.user as any).id = token.sub!
        ;(session.user as any).role = token.role as string
        ;(session.user as any).teams = token.teams as any[]
      }
      return session
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
}

export default NextAuth(authOptions)