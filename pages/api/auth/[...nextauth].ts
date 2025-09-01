import NextAuth, { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import GoogleProvider from "next-auth/providers/google"



export const authOptions: NextAuthOptions = {
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
          }
        }

        // Additional demo users for testing
        if (credentials.email === "admin@example.com" && credentials.password === "admin123") {
          return {
            id: "admin-user",
            email: credentials.email,
            name: "Admin User",
            role: "ADMIN",
            teams: [{ id: "admin-team", name: "Admin Team", role: "ADMIN" }]
          }
        }

        if (credentials.email === "user@example.com" && credentials.password === "user123") {
          return {
            id: "regular-user",
            email: credentials.email,
            name: "Regular User",
            role: "USER",
            teams: [{ id: "user-team", name: "User Team", role: "MEMBER" }]
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
        token.role = (user as any).role
        token.teams = (user as any).teams
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