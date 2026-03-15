import { useState } from "react"
import { motion } from "framer-motion"
import { useStore } from "../store/useStore"
import MovieCard from "../components/MovieCard"
import MovieModal from "../components/MovieModal"

export default function Watchlist() {
    const { watchlist } = useStore()
    const [selected, setSelected] = useState(null)

    return (
        <div style={{ padding: "100px 48px 48px" }}>
            <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <p style={{
                    fontSize: 11, letterSpacing: 4, color: "#555",
                    textTransform: "uppercase", marginBottom: 16
                }}>
                    Saved films
                </p>
                <h2 style={{
                    fontSize: "clamp(32px, 6vw, 72px)", fontWeight: 900,
                    letterSpacing: -2, textTransform: "uppercase",
                    marginBottom: 56
                }}>
                    WATCHLIST
                    <span style={{
                        fontSize: 24, color: "#d2ff00",
                        marginLeft: 20, fontWeight: 700
                    }}>
                        {watchlist.length}
                    </span>
                </h2>
            </motion.div>

            {watchlist.length === 0 ? (
                <div style={{
                    textAlign: "center", padding: "80px 0",
                    color: "#333"
                }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
                    <p style={{
                        fontSize: 13, letterSpacing: 2,
                        textTransform: "uppercase"
                    }}>
                        Nothing saved yet — get recommendations first
                    </p>
                </div>
            ) : (
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                    gap: 16
                }}>
                    {watchlist.map((m, i) => (
                        <MovieCard key={m.movie_idx} movie={m} index={i}
                            onClick={() => setSelected(m)} />
                    ))}
                </div>
            )}

            {selected && (
                <MovieModal movie={selected} onClose={() => setSelected(null)} />
            )}
        </div>
    )
}
