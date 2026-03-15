import { useState, useEffect } from "react"
import { Link, useNavigate, useLocation } from "react-router-dom"
import { motion } from "framer-motion"
import { useStore } from "../store/useStore"

export default function Nav() {
    const [scrolled, setScrolled] = useState(false)
    const { user, logout } = useStore()
    const navigate = useNavigate()
    const location = useLocation()

    useEffect(() => {
        const fn = () => setScrolled(window.scrollY > 40)
        window.addEventListener("scroll", fn)
        return () => window.removeEventListener("scroll", fn)
    }, [])

    const link = (label, to) => (
        <Link to={to} style={{
            fontSize: 11, letterSpacing: 2, color: location.pathname === to
                ? "#d2ff00" : "#666",
            textTransform: "uppercase", fontWeight: 600,
            transition: "color 0.2s",
        }}>{label}</Link>
    )

    return (
        <motion.nav style={{
            position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
            padding: "0 48px", height: 64,
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "rgba(5,5,5,0.95)",
            borderBottom: "1px solid #1a1a1a",
            transition: "all 0.3s ease",
        }}>
            <Link to="/" style={{
                fontSize: 14, fontWeight: 900,
                letterSpacing: 3, textTransform: "uppercase"
            }}>
                plot<span style={{ color: "#d2ff00" }}>Twist</span>
            </Link>

            <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
                {user && (<>
                    {link("Home", "/")}
                    {link("Search", "/search")}
                    {link("Watchlist", "/watchlist")}
                    {link("Profile", "/profile")}
                </>)}
            </div>

            {user && (
                <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                    <span style={{ fontSize: 12, color: "#555" }}>
                        {user.username}
                    </span>
                    <button onClick={() => { logout(); navigate("/login") }}
                        style={{
                            fontSize: 11, letterSpacing: 2, color: "#555",
                            background: "none", border: "1px solid #2a2a2a",
                            padding: "6px 16px", cursor: "pointer",
                            textTransform: "uppercase", fontFamily: "Inter, sans-serif",
                            transition: "all 0.2s"
                        }}>
                        Out
                    </button>
                </div>
            )}
        </motion.nav>
    )
}
