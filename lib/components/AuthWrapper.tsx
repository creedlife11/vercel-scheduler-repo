import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/router"
import { useEffect, useState, ReactNode } from "react"

interface AuthWrapperProps {
  children: ReactNode
  requireAuth?: boolean
  requiredRole?: "VIEWER" | "EDITOR" | "ADMIN"
  allowBypass?: boolean
}

export function AuthWrapper({ 
  children, 
  requireAuth = true, 
  requiredRole,
  allowBypass = false
}: AuthWrapperProps) {
  const { data: session, status } = useSession()
  const router = useRouter()
  
  // Debug logging
  console.log('AuthWrapper - Status:', status, 'Session:', session)
  
  // Check for bypass parameter
  const [bypassAuth, setBypassAuth] = useState(false);
  
  useEffect(() => {
    if (allowBypass && typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('bypass') === 'true') {
        setBypassAuth(true);
        console.log('Authentication bypassed via URL parameter');
      }
    }
  }, [allowBypass]);

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

  if (requireAuth && !session && !bypassAuth) {
    return null // Will redirect to sign in
  }

  return (
    <div>
      {bypassAuth && (
        <div style={{
          padding: "8px 16px",
          backgroundColor: "#fef3c7",
          borderBottom: "1px solid #f59e0b",
          textAlign: "center",
          fontSize: 14,
          color: "#92400e"
        }}>
          ⚠️ Authentication bypassed for testing
        </div>
      )}
      {(session || bypassAuth) && (
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
            {session?.user?.teams && session.user.teams.length > 0 && (
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
              {bypassAuth ? "Test User" : (session?.user?.name || session?.user?.email)}
            </span>
            <span style={{ 
              fontSize: 12, 
              padding: "2px 6px", 
              backgroundColor: "#f3f4f6", 
              borderRadius: 4,
              color: "#374151"
            }}>
              {bypassAuth ? "TEST" : session?.user?.role}
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