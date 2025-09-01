import NextAuth, { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import GoogleProvider from "next-auth/providers/google"



export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "dummy",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "dummy",
    }),
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        console.log('Authorize called with:', credentials?.email);
        
        if (!credentials?.email || !credentials?.password) {
          console.log('Missing credentials');
          return null
        }

        // Demo authentication - replace with proper authentication in production
        if (credentials.email === "demo@example.com" && credentials.password === "demo123") {
          console.log('Demo user authenticated');
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
            role: "VIEWER",
            teams: [{ id: "user-team", name: "User Team", role: "MEMBER" }]
          }
        }

        if (credentials.email === "editor@example.com" && credentials.password === "editor123") {
          return {
            id: "editor-user",
            email: credentials.email,
            name: "Editor User",
            role: "EDITOR",
            teams: [{ id: "editor-team", name: "Editor Team", role: "EDITOR" }]
          }
        }

        console.log('Authentication failed for:', credentials?.email);
        return null
      }
    })
  ],
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET || "fallback-secret-for-development",
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        console.log('JWT callback - user:', user);
        token.role = (user as any).role
        token.teams = (user as any).teams
      }
      return token
    },
    async session({ session, token }) {
      if (token && session.user) {
        console.log('Session callback - token:', token);
        (session.user as any).id = token.sub!
        ;(session.user as any).role = token.role as string
        ;(session.user as any).teams = token.teams as any[]
      }
      console.log('Session callback - final session:', session);
      return session
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
}

export default NextAuth(authOptions)