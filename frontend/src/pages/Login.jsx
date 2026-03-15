import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { useStore } from "../store/useStore"
import { checkHealth } from "../api/plottwist"

function deriveUserId(uname) {
    let hash = 0
    for (let i = 0; i < uname.length; i++)
        hash = (hash * 31 + uname.charCodeAt(i)) & 0xffff
    return hash % 69000
}

export default function Login() {
    const [mode, setMode] = useState("login")
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [error, setError] = useState("")
    const [loading, setLoading] = useState(false)
    const { login, signup, onboardingDone } = useStore()
    const navigate = useNavigate()

    async function handleSubmit() {
        if (!username.trim()) return setError("Username required")
        if (password.length < 4) return setError("Password must be 4+ characters")
        setLoading(true)
        setError("")
        try {
            await checkHealth()
            const { login, register, accounts } = useStore.getState()
            const uname = username.toLowerCase().trim()
            const existing = accounts?.[uname]

            if (mode === "signup") {
                if (existing) return setError("Username taken — log in instead")
                register(username.trim(), password)
                navigate("/onboarding")
            } else {
                const result = login(username.trim(), password)
                if (result === "no_account") return setError("Account not found — sign up first")
                if (result === "wrong_password") return setError("Wrong password")
                const { onboardingDone } = useStore.getState()
                navigate(onboardingDone ? "/" : "/onboarding")
            }
        } catch {
            setError("Can't reach CineSync API — is it running on :8000?")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            minHeight: "100vh", display: "flex",
            alignItems: "center", justifyContent: "center",
            padding: 24, position: "relative", overflow: "hidden",
        }}>
            {/* Background glow */}
            <div style={{
                position: "absolute", top: "40%", left: "50%",
                transform: "translate(-50%,-50%)",
                width: 500, height: 500, borderRadius: "50%",
                background: "radial-gradient(circle, rgba(210,255,0,0.05) 0%, transparent 70%)",
                pointerEvents: "none",
            }} />

            <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                style={{ width: "100%", maxWidth: 420 }}>



                {/* Mode toggle */}
                <div style={{
                    display: "flex", marginBottom: 44,
                    borderBottom: "1px solid #181818"
                }}>
                    {["login", "signup"].map(m => (
                        <button key={m} onClick={() => { setMode(m); setError("") }}
                            style={{
                                flex: 1, background: "none", border: "none",
                                borderBottom: `2px solid ${mode === m ? "#d2ff00" : "transparent"}`,
                                color: mode === m ? "#d2ff00" : "#333",
                                padding: "12px 0", fontSize: 11, fontWeight: 700,
                                letterSpacing: 3, textTransform: "uppercase",
                                cursor: "pointer", fontFamily: "Inter, sans-serif",
                                marginBottom: -1, transition: "all 0.2s",
                            }}>
                            {m}
                        </button>
                    ))}
                </div>

                {/* Username */}
                <div style={{ marginBottom: 28 }}>
                    <input
                        type="text" value={username} placeholder="Username"
                        onChange={e => setUsername(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSubmit()}
                        style={{
                            width: "100%", background: "transparent",
                            border: "none", borderBottom: "1px solid #1e1e1e",
                            color: "#f0f0f0", fontSize: 22, fontWeight: 700,
                            padding: "12px 0", outline: "none",
                            fontFamily: "Inter, sans-serif",
                            transition: "border-color 0.2s",
                        }}
                        onFocus={e => e.target.style.borderBottomColor = "#d2ff00"}
                        onBlur={e => e.target.style.borderBottomColor = "#1e1e1e"}
                    />
                </div>

                {/* Password */}
                <div style={{ marginBottom: 36 }}>
                    <input
                        type="password" value={password} placeholder="Password"
                        onChange={e => setPassword(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSubmit()}
                        style={{
                            width: "100%", background: "transparent",
                            border: "none", borderBottom: "1px solid #1e1e1e",
                            color: "#f0f0f0", fontSize: 22, fontWeight: 700,
                            padding: "12px 0", outline: "none",
                            fontFamily: "Inter, sans-serif",
                            transition: "border-color 0.2s",
                        }}
                        onFocus={e => e.target.style.borderBottomColor = "#d2ff00"}
                        onBlur={e => e.target.style.borderBottomColor = "#1e1e1e"}
                    />
                </div>

                {mode === "signup" && (
                    <p style={{
                        fontSize: 11, color: "#2a2a2a", marginBottom: 24,
                        lineHeight: 1.7, letterSpacing: 0.5
                    }}>
                        No email needed. Your taste profile is generated
                        automatically from your username.
                    </p>
                )}

                {error && (
                    <p style={{
                        fontSize: 12, color: "#ff003c",
                        marginBottom: 20, letterSpacing: 1
                    }}>
                        ⚠ {error}
                    </p>
                )}

                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={handleSubmit} disabled={loading}
                    style={{
                        width: "100%",
                        background: loading ? "#111" : "#d2ff00",
                        color: "#000", border: "none", padding: "20px",
                        fontSize: 12, fontWeight: 900, letterSpacing: 3,
                        textTransform: "uppercase", cursor: "pointer",
                        fontFamily: "Inter, sans-serif",
                        boxShadow: loading ? "none" : "0 0 40px rgba(210,255,0,0.2)",
                        transition: "all 0.2s",
                    }}>
                    {loading
                        ? "Connecting..."
                        : mode === "login" ? "Enter →" : "Create Account →"}
                </motion.button>
            </motion.div>
        </div>
    )
}