import { useRouter } from "next/router"
import Link from "next/link"

const errors: Record<string, string> = {
  Signin: "Try signing in with a different account.",
  OAuthSignin: "Try signing in with a different account.",
  OAuthCallback: "Try signing in with a different account.",
  OAuthCreateAccount: "Try signing in with a different account.",
  EmailCreateAccount: "Try signing in with a different account.",
  Callback: "Try signing in with a different account.",
  OAuthAccountNotLinked: "To confirm your identity, sign in with the same account you used originally.",
  EmailSignin: "The e-mail could not be sent.",
  CredentialsSignin: "Sign in failed. Check the details you provided are correct.",
  SessionRequired: "Please sign in to access this page.",
  default: "Unable to sign in.",
}

export default function ErrorPage() {
  const router = useRouter()
  const { error } = router.query

  const errorMessage = error && typeof error === "string" 
    ? errors[error] ?? errors.default
    : errors.default

  return (
    <div style={{ 
      maxWidth: 400, 
      margin: "100px auto", 
      padding: 40, 
      fontFamily: "Inter, system-ui, Arial",
      textAlign: "center"
    }}>
      <h1 style={{ color: "#dc2626", marginBottom: 20 }}>Authentication Error</h1>
      <p style={{ marginBottom: 30, color: "#6b7280" }}>{errorMessage}</p>
      <Link 
        href="/auth/signin"
        style={{
          display: "inline-block",
          padding: "12px 20px",
          backgroundColor: "#3b82f6",
          color: "white",
          textDecoration: "none",
          borderRadius: 6,
          fontSize: 16
        }}
      >
        Try Again
      </Link>
    </div>
  )
}