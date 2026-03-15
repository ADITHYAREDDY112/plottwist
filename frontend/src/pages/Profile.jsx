import { motion } from "framer-motion"
import { useNavigate } from "react-router-dom"
import { useStore } from "../store/useStore"

const ARC_COLORS = {
    tense_release: "#d2ff00", uplifting: "#4caf82",
    cathartic: "#9b7fe8", thought_provoking: "#5bc4f0",
    bittersweet: "#e87d4b", draining: "#c0392b", neutral_fun: "#888",
}

export default function Profile() {
    const { user, watchlist, ratings, logout } = useStore()
    const navigate = useNavigate()

    const ratingEntries = Object.entries(ratings)
    const avgRating = ratingEntries.length
        ? (ratingEntries.reduce((s, [, v]) => s + v, 0) / ratingEntries.length).toFixed(1)
        : "—"

    // Arc breakdown from watchlist
    const arcCounts = watchlist.reduce((acc, m) => {
        acc[m.arc] = (acc[m.arc] || 0) + 1
        return acc
    }, {})
    const topArc = Object.entries(arcCounts).sort((a, b) => b[1] - a[1])[0]?.[0]

    const stats = [
        { label: "User ID", value: user?.userId },
        { label: "Watchlist", value: watchlist.length },
        { label: "Rated", value: ratingEntries.length },
        { label: "Avg Rating", value: avgRating },
    ]

    return (
        <div style={{ padding: "100px 48px 48px", maxWidth: 800 }}>
            <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>

                <p style={{
                    fontSize: 11, letterSpacing: 4, color: "#555",
                    textTransform: "uppercase", marginBottom: 16
                }}>
                    Your profile
                </p>
                <h2 style={{
                    fontSize: "clamp(32px, 6vw, 72px)", fontWeight: 900,
                    letterSpacing: -2, textTransform: "uppercase",
                    marginBottom: 56
                }}>
                    {user?.username}
                </h2>

                {/* Stats */}
                <div style={{
                    display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                    gap: 2, marginBottom: 56
                }}>
                    {stats.map(s => (
                        <div key={s.label}
                            style={{ background: "#111", padding: "24px 20px" }}>
                            <div style={{
                                fontSize: 11, color: "#555", letterSpacing: 2,
                                textTransform: "uppercase", marginBottom: 8
                            }}>
                                {s.label}
                            </div>
                            <div style={{
                                fontSize: 28, fontWeight: 900,
                                color: "#d2ff00", letterSpacing: -1
                            }}>
                                {s.value}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Emotional fingerprint */}
                {topArc && (
                    <div style={{ marginBottom: 56 }}>
                        <p style={{
                            fontSize: 11, letterSpacing: 4, color: "#555",
                            textTransform: "uppercase", marginBottom: 24
                        }}>
                            Emotional Fingerprint
                        </p>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            {Object.entries(arcCounts)
                                .sort((a, b) => b[1] - a[1])
                                .map(([arc, count]) => (
                                    <div key={arc} style={{
                                        background: `${ARC_COLORS[arc]}15`,
                                        border: `1px solid ${ARC_COLORS[arc]}44`,
                                        color: ARC_COLORS[arc],
                                        padding: "8px 20px", fontSize: 11,
                                        fontWeight: 700, letterSpacing: 2,
                                        textTransform: "uppercase",
                                    }}>
                                        {arc.replace(/_/g, " ")} · {count}
                                    </div>
                                ))}
                        </div>
                    </div>
                )}

                <button
                    onClick={() => { logout(); navigate("/login") }}
                    style={{
                        background: "transparent", color: "#555",
                        border: "1px solid #2a2a2a", padding: "14px 32px",
                        fontSize: 11, fontWeight: 700, letterSpacing: 2,
                        textTransform: "uppercase", cursor: "pointer",
                        fontFamily: "Inter, sans-serif"
                    }}>
                    Sign Out
                </button>
            </motion.div>
        </div>
    )
}
