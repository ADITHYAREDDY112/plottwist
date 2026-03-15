import { useState } from "react"
import { motion } from "framer-motion"
import axios from "axios"
import { posterUrl } from "../api/tmdb"
import MovieModal from "../components/MovieModal"

const KEY = import.meta.env.VITE_TMDB_API_KEY
const BASE = "https://api.themoviedb.org/3"

export default function Search() {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [selected, setSelected] = useState(null)

    async function handleSearch(q) {
        setQuery(q)
        if (q.length < 2) return setResults([])
        setLoading(true)
        try {
            const res = await axios.get(`${BASE}/search/movie`, {
                params: { api_key: KEY, query: q, page: 1 }
            })
            setResults(res.data.results?.slice(0, 20) || [])
        } catch { } finally { setLoading(false) }
    }

    function tmdbToMovie(r) {
        return {
            movie_idx: r.id,
            title: r.title,
            genres: "",
            arc: "neutral_fun",
            score: r.vote_average / 10,
            rank: null,
        }
    }

    return (
        <div style={{ padding: "100px 48px 48px" }}>
            <motion.h2
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                style={{
                    fontSize: "clamp(32px, 6vw, 72px)", fontWeight: 900,
                    letterSpacing: -2, textTransform: "uppercase",
                    marginBottom: 48
                }}>
                SEARCH
            </motion.h2>

            {/* Search input */}
            <div style={{ position: "relative", maxWidth: 600, marginBottom: 56 }}>
                <input value={query}
                    onChange={e => handleSearch(e.target.value)}
                    placeholder="Search any movie..."
                    autoFocus
                    style={{
                        width: "100%", background: "transparent",
                        border: "none", borderBottom: "1px solid #2a2a2a",
                        color: "#f0f0f0", fontSize: 32, fontWeight: 700,
                        padding: "12px 0 12px 0", outline: "none",
                        fontFamily: "Inter, sans-serif", letterSpacing: -1
                    }}
                />
                {loading && (
                    <span style={{
                        position: "absolute", right: 0, top: "50%",
                        transform: "translateY(-50%)",
                        fontSize: 11, color: "#555",
                        letterSpacing: 2
                    }}>Searching...</span>
                )}
            </div>

            {/* Results */}
            <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: 16
            }}>
                {results.map((r, i) => (
                    <motion.div key={r.id}
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        onClick={() => setSelected(tmdbToMovie(r))}
                        style={{ cursor: "pointer" }}>
                        <div style={{
                            aspectRatio: "2/3", background: "#1a1a1a",
                            overflow: "hidden", marginBottom: 8
                        }}>
                            {r.poster_path ? (
                                <img src={posterUrl(r.poster_path)}
                                    alt={r.title}
                                    style={{
                                        width: "100%", height: "100%",
                                        objectFit: "cover"
                                    }} />
                            ) : (
                                <div style={{
                                    width: "100%", height: "100%",
                                    display: "flex", alignItems: "center",
                                    justifyContent: "center",
                                    color: "#2a2a2a", fontSize: 24
                                }}>🎬</div>
                            )}
                        </div>
                        <div style={{
                            fontSize: 12, fontWeight: 700, lineHeight: 1.3,
                            color: "#f0f0f0"
                        }}>
                            {r.title}
                        </div>
                        <div style={{ fontSize: 11, color: "#555" }}>
                            {r.release_date?.slice(0, 4)}
                            {r.vote_average ? ` · ★ ${r.vote_average.toFixed(1)}` : ""}
                        </div>
                    </motion.div>
                ))}
            </div>

            {selected && (
                <MovieModal movie={selected} onClose={() => setSelected(null)} />
            )}
        </div>
    )
}
