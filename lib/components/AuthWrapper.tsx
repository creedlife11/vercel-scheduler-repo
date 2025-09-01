import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/router"
import { useEffect, ReactNode } from "react"

interface AuthWrapperProps {
  children: ReactNode
  requireAuth?: boolean
  requiredRole?: "VIEWER" | "EDITOR" | "ADMIN"
}

export function AuthWrapper({ 
  children, 
  requireAuth = true, 
  requiredRole 
}: AuthWrapperProps) {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === "loading") return // Still loading

    if (requireAuth && !session) {
      router.push("/auth/signin")
      return
    }

    if (requiredRole && session?.user?.role) {
      const roleHierarchy = { "VIEWER": 0, "EDITOR": 1, "ADMIN": 2 }
      const userLevel = roleHierarchy[session.user.role as keyof typeof roleHierarchy] ?? 0
      const requiredLevel = roleHierarchy[requiredRole]

      if (userLevel < requiredLevel) {
        router.push("/auth/error?error=Forbidden")
        return
      }
    }
  }, [session, status, requireAuth, requiredRole, router])

  if (status === "loading") {
    return (
      <div style={{ 
        display: "flex", 
        justifyContent: "center", 
        alignItems: "center", 
        height: "100vh",
        fontFamily: "Inter, system-ui, Arial"
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  if (requireAuth && !session) {
    return null // Will redirect to sign in
  }

  return (
    <div>
      {session && (
        <header style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 20px",
          borderBottom: "1px solid #e5e7eb",
          backgroundColor: "white",
          fontFamily: "Inter, system-ui, Arial"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>Team Scheduler</h2>
            {session.user.teams && session.user.teams.length > 0 && (
              <select style={{
                padding: "4px 8px",
                border: "1px solid #d1d5db",
                borderRadius: 4,
                fontSize: 14
              }}>
                {session.user.teams.map(team => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 14, color: "#6b7280" }}>
              {session.user.name || session.user.email}
            </span>
            <span style={{ 
              fontSize: 12, 
              padding: "2px 6px", 
              backgroundColor: "#f3f4f6", 
              borderRadius: 4,
              color: "#374151"
            }}>
              {session.user.role}
            </span>
            <button
              onClick={() => signOut({ callbackUrl: "/auth/signin" })}
              style={{
                padding: "6px 12px",
                backgroundColor: "#ef4444",
                color: "white",
                border: "none",
                borderRadius: 4,
                fontSize: 14,
                cursor: "pointer"
              }}
            >
              Sign Out
            </button>
          </div>
        </header>
      )}
      
      <main>
        {children}
      </main>
    </div>
  )
}