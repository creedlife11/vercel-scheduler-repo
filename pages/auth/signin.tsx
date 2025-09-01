import { GetServerSideProps } from "next"
import { getServerSession } from "next-auth/next"
import { authOptions } from "../api/auth/[...nextauth]"
import { signIn, getProviders } from "next-auth/react"
import { useState } from "react"

interface SignInProps {
  providers: any
}

export default function SignIn({ providers }: SignInProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleCredentialsSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      })

      console.log('Sign in result:', result);
      
      if (result?.error) {
        setError("Invalid credentials")
      } else if (result?.ok) {
        // Successful login, redirect to home
        window.location.href = "/"
      } else {
        setError("Sign in failed")
      }
    } catch (err) {
      setError("Sign in failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ 
      maxWidth: 400, 
      margin: "100px auto", 
      padding: 40, 
      fontFamily: "Inter, system-ui, Arial",
      border: "1px solid #e5e7eb",
      borderRadius: 8,
      backgroundColor: "white"
    }}>
      <h1 style={{ textAlign: "center", marginBottom: 30 }}>Sign In</h1>
      
      {providers?.google && (
        <div style={{ marginBottom: 20 }}>
          <button
            onClick={() => signIn("google", { callbackUrl: "/" })}
            style={{
              width: "100%",
              padding: "12px 20px",
              backgroundColor: "#4285f4",
              color: "white",
              border: "none",
              borderRadius: 6,
              fontSize: 16,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
        </div>
      )}

      <div style={{ 
        textAlign: "center", 
        margin: "20px 0", 
        color: "#6b7280",
        position: "relative"
      }}>
        <span style={{ 
          backgroundColor: "white", 
          padding: "0 10px",
          position: "relative",
          zIndex: 1
        }}>
          or
        </span>
        <div style={{
          position: "absolute",
          top: "50%",
          left: 0,
          right: 0,
          height: 1,
          backgroundColor: "#e5e7eb",
          zIndex: 0
        }} />
      </div>

      <form onSubmit={handleCredentialsSignIn}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontSize: 14, fontWeight: 500 }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              width: "100%",
              padding: "8px 12px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              fontSize: 14
            }}
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "block", marginBottom: 4, fontSize: 14, fontWeight: 500 }}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              width: "100%",
              padding: "8px 12px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              fontSize: 14
            }}
          />
        </div>

        {error && (
          <div style={{ 
            color: "#dc2626", 
            fontSize: 14, 
            marginBottom: 16,
            textAlign: "center"
          }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px 20px",
            backgroundColor: loading ? "#9ca3af" : "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 6,
            fontSize: 16,
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <div style={{ 
        textAlign: "center", 
        marginTop: 20, 
        fontSize: 12, 
        color: "#6b7280" 
      }}>
        Demo credentials: any email with password &quot;demo123&quot;
      </div>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = async (context) => {
  const session = await getServerSession(context.req, context.res, authOptions)

  // If user is already signed in, redirect to home
  if (session) {
    return {
      redirect: {
        destination: "/",
        permanent: false,
      },
    }
  }

  const providers = await getProviders()

  return {
    props: {
      providers: providers ?? {},
    },
  }
}