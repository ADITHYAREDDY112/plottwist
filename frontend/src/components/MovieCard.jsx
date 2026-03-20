import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { searchMovie, getMovieDetails, posterUrl } from "../api/tmdb"
import { useStore } from "../store/useStore"

const ARC_COLORS = {
    tense_release: "#d2ff00", uplifting: "#4caf82",
    cathartic: "#9b7fe8", thought_provoking: "#5bc4f0",
    bittersweet: "#e87d4b", draining: "#c0392b", neutral_fun: "#888",
}

export default function MovieCard({ movie, index = 0, onClick, size = "normal" }) {
    const [poster, setPoster] = useState(null)
    const [hovered, setHovered] = useState(false)
    const { isInWatchlist, getRating } = useStore()
    const arcColor = ARC_COLORS[movie.arc] || "#666"
    const width = size === "large" ? 200 : 160

    useEffect(() => {
        if (movie.tmdb_id && movie.tmdb_id > 0) {
            getMovieDetails(movie.tmdb_id).then(r => {
                if (r?.poster_path) setPoster(posterUrl(r.poster_path))
            })
        } else {
            searchMovie(movie.title).then(r => {
                if (r?.poster_path) setPoster(posterUrl(r.poster_path))
            })
        }
    }, [movie.tmdb_id, movie.title])

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.04 }}
            onHoverStart={() => setHovered(true)}
            onHoverEnd={() => setHovered(false)}
            onClick={onClick}
            style={{
                minWidth: width, width, cursor: "pointer",
                flexShrink: 0, position: "relative"
            }}>

            {/* Poster */}
            <div style={{
                aspectRatio: "2/3", background: "#1a1a1a",
                overflow: "hidden", position: "relative",
                marginBottom: 10
            }}>
                {poster ? (
                    <motion.img src={poster} alt={movie.title}
                        animate={{
                            scale: hovered ? 1.07 : 1,
                            filter: hovered ? "grayscale(0%) brightness(1)" : "grayscale(30%) brightness(0.8)"
                        }}
                        transition={{ duration: 0.4 }}
                        style={{
                            width: "100%", height: "100%",
                            objectFit: "cover", display: "block"
                        }} />
                ) : (
                    <div style={{
                        width: "100%", height: "100%",
                        display: "flex", alignItems: "center",
                        justifyContent: "center", color: "#2a2a2a",
                        fontSize: 32
                    }}>🎬</div>
                )}

                {/* Hover overlay */}
                <motion.div
                    animate={{ opacity: hovered ? 1 : 0 }}
                    style={{
                        position: "absolute", inset: 0,
                        background: "rgba(0,0,0,0.5)",
                        display: "flex", alignItems: "center",
                        justifyContent: "center"
                    }}>
                    <span style={{
                        fontSize: 12, fontWeight: 700, letterSpacing: 2,
                        textTransform: "uppercase", color: "#fff"
                    }}>
                        View
                    </span>
                </motion.div>

                {/* Watchlist indicator */}
                {isInWatchlist(movie.movie_idx) && (
                    <div style={{
                        position: "absolute", top: 8, right: 8,
                        background: "#d2ff00", color: "#000",
                        width: 20, height: 20, borderRadius: "50%",
                        display: "flex", alignItems: "center",
                        justifyContent: "center", fontSize: 10,
                        fontWeight: 900
                    }}>✓</div>
                )}

                {/* Rating indicator */}
                {getRating(movie.movie_idx) > 0 && (
                    <div style={{
                        position: "absolute", top: 8, left: 8,
                        background: "rgba(0,0,0,0.7)", color: "#d2ff00",
                        fontSize: 10, fontWeight: 700,
                        padding: "2px 6px"
                    }}>
                        {getRating(movie.movie_idx)}★
                    </div>
                )}

                {/* Rank */}
                {movie.rank && (
                    <div style={{
                        position: "absolute", bottom: 8, left: 8,
                        background: "rgba(0,0,0,0.8)", color: arcColor,
                        fontSize: 10, fontWeight: 800,
                        padding: "2px 6px", letterSpacing: 1
                    }}>
                        #{movie.rank}
                    </div>
                )}
            </div>

            {/* Info */}
            <div>
                <div style={{
                    fontSize: 9, color: arcColor, fontWeight: 700,
                    letterSpacing: 2, textTransform: "uppercase",
                    marginBottom: 4
                }}>
                    {movie.arc?.replace(/_/g, " ")}
                </div>
                <div style={{
                    fontSize: 13, fontWeight: 700, lineHeight: 1.3,
                    color: hovered ? "#d2ff00" : "#f0f0f0",
                    transition: "color 0.2s",
                    overflow: "hidden", textOverflow: "ellipsis",
                    whiteSpace: "nowrap"
                }}>
                    {movie.title}
                </div>
            </div>
        </motion.div>
    )
}
