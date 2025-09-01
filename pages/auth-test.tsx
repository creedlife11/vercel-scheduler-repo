import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/router"

export default function AuthTest() {
  const { data: session, status } = useSession()
  const router = useRouter()

  if (status === "loading") {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <h1>Loading...</h1>
      </div>
    )
  }

  if (!session) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <h1>Not Authenticated</h1>
        <p>You are not signed in.</p>
        <button 
          onClick={() => router.push("/auth/signin")}
          style={{
            padding: "12px 24px",
            backgroundColor: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "16px"
          }}
        >
          Sign In
        </button>
      </div>
    )
  }

  return (
    <div style={{ padding: "40px", maxWidth: "600px", margin: "0 auto" }}>
      <h1>✅ Authentication Working!</h1>
      
      <div style={{ 
        backgroundColor: "#f0f9ff", 
        padding: "20px", 
        borderRadius: "8px",
        marginBottom: "20px"
      }}>
        <h2>Session Data:</h2>
        <pre style={{ 
          backgroundColor: "white", 
          padding: "15px", 
          borderRadius: "4px",
          overflow: "auto",
          fontSize: "14px"
        }}>
          {JSON.stringify(session, null, 2)}
        </pre>
      </div>

      <div style={{ display: "flex", gap: "12px" }}>
        <button 
          onClick={() => router.push("/")}
          style={{
            padding: "12px 24px",
            backgroundColor: "#10b981",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "16px"
          }}
        >
          Go to Scheduler
        </button>
        
        <button 
          onClick={() => signOut({ callbackUrl: "/auth/signin" })}
          style={{
            padding: "12px 24px",
            backgroundColor: "#dc2626",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "16px"
          }}
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}