import NextAuth from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      email: string
      name?: string
      role: string
      teams: Array<{
        id: string
        name: string
        role: string
      }>
    }
  }

  interface User {
    role: string
    teams: Array<{
      id: string
      name: string
      role: string
    }>
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role: string
    teams: Array<{
      id: string
      name: string
      role: string
    }>
  }
}