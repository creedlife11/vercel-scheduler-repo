import NextAuth, { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"

export const authOptions: NextAuthOptions = {
  providers: [
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

        // Simple demo authentication
        const demoUsers = [
          { id: "1", email: "demo@example.com", password: "demo123", name: "Demo User", role: "ADMIN" },
          { id: "2", email: "editor@example.com", password: "editor123", name: "Editor User", role: "EDITOR" },
          { id: "3", email: "user@example.com", password: "user123", name: "Regular User", role: "VIEWER" }
        ];

        const user = demoUsers.find(u => 
          u.email === credentials.email && u.password === credentials.password
        );

        if (user) {
          return {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
            teams: [{ id: "team-1", name: "Default Team", role: user.role }]
          }
        }

        return null
      }
    })
  ],
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET,
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
  debug: process.env.NODE_ENV === 'development',
}

export default NextAuth(authOptions)