import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import toast from "react-hot-toast"
import { getMovieDetails, searchMovie, posterUrl, backdropUrl } from "../api/tmdb"
import { getTrailerId } from "../api/youtube"
import { useStore } from "../store/useStore"
import StarRating from "./StarRating"

const ARC_COLORS = {
    tense_release: "#d2ff00", uplifting: "#4caf82",
    cathartic: "#9b7fe8", thought_provoking: "#5bc4f0",
    bittersweet: "#e87d4b", draining: "#c0392b", neutral_fun: "#888",
}

export default function MovieModal({ movie, onClose }) {
    const [details, setDetails] = useState(null)
    const [trailerId, setTrailerId] = useState(null)
    const [showTrailer, setShowTrailer] = useState(false)
    const [loading, setLoading] = useState(true)
    const { addToWatchlist, removeFromWatchlist,
        isInWatchlist, rateMovie, getRating } = useStore()

    const inWatchlist = isInWatchlist(movie.movie_idx)
    const rating = getRating(movie.movie_idx)
    const arcColor = ARC_COLORS[movie.arc] || "#666"

    useEffect(() => {
        async function load() {
            setLoading(true)
            const tmdb = await searchMovie(movie.title)
            if (tmdb) {
                const det = await getMovieDetails(tmdb.id)
                setDetails(det)
                const year = det?.release_date?.slice(0, 4) ?? ""
                const tid  = await getTrailerId(movie.title, year)
                setTrailerId(tid)
            }
            setLoading(false)
        }
        load()
    }, [movie.title])

    // Close on escape
    useEffect(() => {
        const fn = (e) => e.key === "Escape" && onClose()
        window.addEventListener("keydown", fn)
        return () => window.removeEventListener("keydown", fn)
    }, [onClose])

    const backdrop = backdropUrl(details?.backdrop_path)
    const poster = posterUrl(details?.poster_path, "w300")
    const cast = details?.credits?.cast?.slice(0, 5) || []
    const director = details?.credits?.crew?.find(c => c.job === "Director")

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                onClick={onClose}
                style={{
                    position: "fixed", inset: 0, zIndex: 200,
                    background: "rgba(0,0,0,0.85)",
                    backdropFilter: "blur(8px)",
                    display: "flex", alignItems: "center",
                    justifyContent: "center", padding: 24
                }}>

                <motion.div
                    initial={{ opacity: 0, y: 40, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 40 }}
                    transition={{ duration: 0.35 }}
                    onClick={e => e.stopPropagation()}
                    style={{
                        background: "#111", width: "100%", maxWidth: 860,
                        maxHeight: "90vh", overflowY: "auto",
                        position: "relative"
                    }}>

                    {/* Backdrop */}
                    {backdrop && !showTrailer && (
                        <div style={{
                            position: "relative", height: 320,
                            overflow: "hidden"
                        }}>
                            <img src={backdrop} alt=""
                                style={{
                                    width: "100%", height: "100%",
                                    objectFit: "cover", opacity: 0.5
                                }} />
                            <div style={{
                                position: "absolute", inset: 0,
                                background: "linear-gradient(transparent 40%, #111)"
                            }} />
                            {trailerId && (
                                <button onClick={() => setShowTrailer(true)}
                                    style={{
                                        position: "absolute", top: "50%", left: "50%",
                                        transform: "translate(-50%,-50%)",
                                        background: "#d2ff00", color: "#000",
                                        border: "none", borderRadius: "50%",
                                        width: 64, height: 64, fontSize: 20,
                                        cursor: "pointer", display: "flex",
                                        alignItems: "center", justifyContent: "center"
                                    }}>
                                    ▶
                                </button>
                            )}
                        </div>
                    )}

                    {/* Trailer */}
                    {showTrailer && trailerId && (
                        <div style={{
                            position: "relative", paddingTop: "56.25%",
                            background: "#000"
                        }}>
                            <iframe
                                src={`https://www.youtube.com/embed/${trailerId}?autoplay=1`}
                                style={{
                                    position: "absolute", inset: 0,
                                    width: "100%", height: "100%",
                                    border: "none"
                                }}
                                allow="autoplay; fullscreen" allowFullScreen />
                            <button onClick={() => setShowTrailer(false)}
                                style={{
                                    position: "absolute", top: 12, right: 12,
                                    background: "rgba(0,0,0,0.7)", color: "#fff",
                                    border: "none", padding: "6px 12px",
                                    cursor: "pointer", fontSize: 12
                                }}>
                                ✕ Close
                            </button>
                        </div>
                    )}

                    {/* Content */}
                    <div style={{ padding: 32 }}>
                        <div style={{
                            display: "flex", gap: 24,
                            alignItems: "flex-start"
                        }}>

                            {/* Poster */}
                            {poster && (
                                <img src={poster} alt={movie.title}
                                    style={{
                                        width: 120, flexShrink: 0,
                                        borderRadius: 2
                                    }} />
                            )}

                            <div style={{ flex: 1 }}>
                                {/* Arc tag */}
                                <div style={{
                                    fontSize: 10, color: arcColor, fontWeight: 700,
                                    letterSpacing: 2, textTransform: "uppercase",
                                    marginBottom: 10
                                }}>
                                    {movie.arc.replace(/_/g, " ")}
                                </div>

                                {/* Title */}
                                <h2 style={{
                                    fontSize: "clamp(20px, 3vw, 32px)",
                                    fontWeight: 900, letterSpacing: -1,
                                    marginBottom: 8, lineHeight: 1.1
                                }}>
                                    {movie.title}
                                </h2>

                                {/* Meta */}
                                <div style={{
                                    display: "flex", gap: 16,
                                    marginBottom: 16, flexWrap: "wrap"
                                }}>
                                    {details?.release_date && (
                                        <span style={{ fontSize: 12, color: "#555" }}>
                                            {details.release_date.slice(0, 4)}
                                        </span>
                                    )}
                                    {details?.runtime && (
                                        <span style={{ fontSize: 12, color: "#555" }}>
                                            {details.runtime} min
                                        </span>
                                    )}
                                    {details?.vote_average && (
                                        <span style={{
                                            fontSize: 12, color: "#d2ff00",
                                            fontWeight: 700
                                        }}>
                                            ★ {details.vote_average.toFixed(1)}
                                        </span>
                                    )}
                                    <span style={{ fontSize: 12, color: "#555" }}>
                                        {movie.genres}
                                    </span>
                                </div>

                                {/* Overview */}
                                {details?.overview && (
                                    <p style={{
                                        fontSize: 14, color: "#888", lineHeight: 1.7,
                                        marginBottom: 20, fontWeight: 300
                                    }}>
                                        {details.overview}
                                    </p>
                                )}

                                {/* Director */}
                                {director && (
                                    <p style={{
                                        fontSize: 12, color: "#555",
                                        marginBottom: 16
                                    }}>
                                        <span style={{ color: "#333" }}>Director </span>
                                        {director.name}
                                    </p>
                                )}

                                {/* Cast */}
                                {cast.length > 0 && (
                                    <p style={{
                                        fontSize: 12, color: "#555",
                                        marginBottom: 24
                                    }}>
                                        <span style={{ color: "#333" }}>Cast </span>
                                        {cast.map(c => c.name).join(", ")}
                                    </p>
                                )}

                                {/* Your rating */}
                                <div style={{ marginBottom: 24 }}>
                                    <p style={{
                                        fontSize: 11, color: "#555",
                                        letterSpacing: 2, textTransform: "uppercase",
                                        marginBottom: 8
                                    }}>
                                        Your Rating
                                    </p>
                                    <StarRating value={rating}
                                        onChange={(r) => {
                                            rateMovie(movie.movie_idx, r)
                                            toast.success(`Rated ${movie.title} ${r}★`)
                                        }} />
                                </div>

                                {/* Actions */}
                                <div style={{ display: "flex", gap: 12 }}>
                                    {trailerId && !showTrailer && (
                                        <button onClick={() => setShowTrailer(true)}
                                            style={{
                                                background: "#d2ff00", color: "#000",
                                                border: "none", padding: "12px 28px",
                                                fontSize: 11, fontWeight: 700,
                                                letterSpacing: 2, textTransform: "uppercase",
                                                cursor: "pointer",
                                                fontFamily: "Inter, sans-serif"
                                            }}>
                                            ▶ Trailer
                                        </button>
                                    )}
                                    <button
                                        onClick={() => {
                                            if (inWatchlist) {
                                                removeFromWatchlist(movie.movie_idx)
                                                toast.success("Removed from watchlist")
                                            } else {
                                                addToWatchlist(movie)
                                                toast.success("Added to watchlist ✓")
                                            }
                                        }}
                                        style={{
                                            background: inWatchlist ? "#1a1a1a" : "transparent",
                                            color: inWatchlist ? "#d2ff00" : "#888",
                                            border: `1px solid ${inWatchlist ? "#d2ff00" : "#333"}`,
                                            padding: "12px 28px", fontSize: 11, fontWeight: 700,
                                            letterSpacing: 2, textTransform: "uppercase",
                                            cursor: "pointer", fontFamily: "Inter, sans-serif",
                                            transition: "all 0.2s",
                                        }}>
                                        {inWatchlist ? "✓ Saved" : "+ Watchlist"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Close button */}
                    <button onClick={onClose}
                        style={{
                            position: "absolute", top: 16, right: 16,
                            background: "rgba(0,0,0,0.5)", color: "#888",
                            border: "1px solid #2a2a2a", width: 36, height: 36,
                            cursor: "pointer", fontSize: 14,
                            fontFamily: "Inter, sans-serif"
                        }}>
                        ✕
                    </button>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}
