import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useStore } from "../store/useStore"
import { getRecommendations } from "../api/plottwist"
import {
    searchMovie, backdropUrl, getTrending,
    getNowPlaying, getTopRated, tmdbToMovie
} from "../api/tmdb"
import MovieCard from "../components/MovieCard"
import MovieModal from "../components/MovieModal"
import MoodChips from "../components/MoodChips"
import SkeletonCard from "../components/SkeletonCard"

function Row({ title, subtitle, movies, loading, onSelect, accentColor }) {
    return (
        <div style={{ marginBottom: 48 }}>
            <div style={{
                paddingLeft: 48, paddingRight: 48,
                marginBottom: 20,
                display: "flex", alignItems: "baseline", gap: 12
            }}>
                <h3 style={{
                    fontSize: 10, letterSpacing: 4,
                    color: accentColor || "#444",
                    textTransform: "uppercase", fontWeight: 700
                }}>
                    {title}
                </h3>
                {subtitle && (
                    <span style={{
                        fontSize: 11, color: "#2a2a2a",
                        fontStyle: "italic", fontWeight: 200
                    }}>
                        {subtitle}
                    </span>
                )}
            </div>
            <div className="row-scroll"
                style={{ paddingLeft: 48, paddingRight: 48 }}>
                {loading
                    ? Array(8).fill(0).map((_, i) => <SkeletonCard key={i} />)
                    : movies.map((m, i) => (
                        <MovieCard key={`${m.movie_idx}-${i}`} movie={m}
                            index={i} onClick={() => onSelect(m)} />
                    ))}
            </div>
        </div>
    )
}

export default function Home() {
    const { user, currentMood, setMood } = useStore()

    const [recs, setRecs] = useState([])
    const [moodRecs, setMoodRecs] = useState({})   // keyed by mood
    const [trending, setTrending] = useState([])
    const [nowPlaying, setNowPlaying] = useState([])
    const [topRated, setTopRated] = useState([])

    const [loadingRecs, setLoadingRecs] = useState(true)
    const [loadingMood, setLoadingMood] = useState(false)
    const [loadingTmdb, setLoadingTmdb] = useState(true)

    const [selected, setSelected] = useState(null)
    const [heroMovie, setHeroMovie] = useState(null)
    const [heroBg, setHeroBg] = useState(null)

    // TMDB rows — load once
    useEffect(() => {
        setLoadingTmdb(true)
        Promise.all([getTrending(), getNowPlaying(), getTopRated()])
            .then(([tr, np, top]) => {
                setTrending(tr.map((r, i) => tmdbToMovie(r, i + 1)))
                setNowPlaying(np.map((r, i) => tmdbToMovie(r, i + 1)))
                setTopRated(top.map((r, i) => tmdbToMovie(r, i + 1)))
                if (!heroMovie && tr[0]) setHeroMovie(tmdbToMovie(tr[0], 1))
            })
            .finally(() => setLoadingTmdb(false))
    }, [])

    // Base recs — load once
    useEffect(() => {
        if (!user) return
        setLoadingRecs(true)
        getRecommendations(user.userId || 0, null, 20)
            .then(r => {
                const seen = new Set()
                setRecs(r.filter(m => {
                    if (seen.has(m.movie_idx)) return false
                    seen.add(m.movie_idx); return true
                }))
                if (r[0]) setHeroMovie(r[0])
            })
            .finally(() => setLoadingRecs(false))
    }, [user])

    // Mood recs — load per mood, cache result
    useEffect(() => {
        if (!user || !currentMood) return
        if (moodRecs[currentMood]) return   // already cached
        setLoadingMood(true)
        getRecommendations(user.userId || 0, currentMood, 15)
            .then(r => setMoodRecs(prev => ({ ...prev, [currentMood]: r })))
            .finally(() => setLoadingMood(false))
    }, [user, currentMood])

    // Hero backdrop
    useEffect(() => {
        if (!heroMovie) return
        searchMovie(heroMovie.title).then(r => {
            if (r?.backdrop_path) setHeroBg(backdropUrl(r.backdrop_path))
        })
    }, [heroMovie])

    const forYou = recs.slice(0, 10)
    const hidden = recs.slice(10, 20)
    const moodList = currentMood ? (moodRecs[currentMood] || []) : []

    return (
        <div style={{ paddingTop: 64 }}>

            {/* ── Hero ── */}
            {heroMovie && (
                <div data-hover onClick={() => setSelected(heroMovie)}
                    style={{
                        position: "relative", height: "75vh",
                        overflow: "hidden", marginBottom: 64,
                        cursor: "pointer"
                    }}>
                    {heroBg && (
                        <motion.img src={heroBg} alt=""
                            initial={{ scale: 1.05 }} animate={{ scale: 1 }}
                            transition={{ duration: 1.4, ease: "easeOut" }}
                            style={{
                                width: "100%", height: "100%",
                                objectFit: "cover", opacity: 0.3
                            }} />
                    )}
                    <div style={{
                        position: "absolute", inset: 0,
                        background: `linear-gradient(
              to right,
              rgba(20,20,20,0.97) 0%,
              rgba(20,20,20,0.6) 55%,
              transparent 100%
            )`,
                        display: "flex", flexDirection: "column",
                        justifyContent: "flex-end",
                        padding: "0 48px 64px",
                    }}>
                        <motion.p
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                            style={{
                                fontSize: 10, letterSpacing: 4, color: "#d2ff00",
                                fontWeight: 700, textTransform: "uppercase",
                                marginBottom: 14
                            }}>
                            ✦ Top Pick For You
                        </motion.p>
                        <motion.h1
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
                            style={{
                                fontSize: "clamp(32px,7vw,88px)",
                                fontWeight: 900, letterSpacing: -3,
                                textTransform: "uppercase", lineHeight: 0.92,
                                marginBottom: 16, maxWidth: 700
                            }}>
                            {heroMovie.title}
                        </motion.h1>
                        <motion.p
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            transition={{ delay: 0.5 }}
                            style={{
                                fontSize: 13, color: "#555", marginBottom: 28,
                                fontWeight: 200, fontStyle: "italic"
                            }}>
                            {heroMovie.genres || "Film"}
                        </motion.p>
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6 }}
                            style={{ display: "flex", gap: 12 }}>
                            <button data-hover
                                onClick={e => { e.stopPropagation(); setSelected(heroMovie) }}
                                style={{
                                    background: "#d2ff00", color: "#000",
                                    border: "none", padding: "14px 36px",
                                    fontSize: 11, fontWeight: 900, letterSpacing: 3,
                                    textTransform: "uppercase", cursor: "pointer",
                                    fontFamily: "Inter, sans-serif",
                                    boxShadow: "0 0 32px rgba(210,255,0,0.25)"
                                }}>
                                ▶ Trailer
                            </button>
                            <button data-hover
                                onClick={e => { e.stopPropagation(); setSelected(heroMovie) }}
                                style={{
                                    background: "rgba(20,20,20,0.6)",
                                    backdropFilter: "blur(12px)",
                                    color: "#888", border: "1px solid #2a2a2a",
                                    padding: "14px 36px", fontSize: 11, fontWeight: 700,
                                    letterSpacing: 3, textTransform: "uppercase",
                                    cursor: "pointer", fontFamily: "Inter, sans-serif"
                                }}>
                                More Info
                            </button>
                        </motion.div>
                    </div>
                </div>
            )}

            {/* ── Mood accordion ── */}
            <div style={{ paddingLeft: 48, paddingRight: 48, marginBottom: 56 }}>
                <p style={{
                    fontSize: 10, letterSpacing: 4, color: "#333",
                    textTransform: "uppercase", marginBottom: 20,
                    fontWeight: 700
                }}>
                    How are you feeling tonight?
                </p>
                <MoodChips value={currentMood} onChange={setMood} />

                {/* Mood row — slides in when mood selected */}
                <AnimatePresence>
                    {currentMood && (
                        <motion.div
                            key={currentMood}
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                            style={{ overflow: "hidden" }}>
                            <div style={{ paddingTop: 36 }}>
                                <div style={{
                                    display: "flex", alignItems: "baseline",
                                    gap: 12, marginBottom: 20
                                }}>
                                    <h3 style={{
                                        fontSize: 10, letterSpacing: 4,
                                        color: "#ff6b00", textTransform: "uppercase",
                                        fontWeight: 700
                                    }}>
                                        {currentMood} picks
                                    </h3>
                                    <span style={{
                                        fontSize: 11, color: "#2a2a2a",
                                        fontStyle: "italic", fontWeight: 200
                                    }}>
                                        emotionally matched
                                    </span>
                                </div>
                                <div className="row-scroll">
                                    {loadingMood
                                        ? Array(8).fill(0).map((_, i) => <SkeletonCard key={i} />)
                                        : moodList.map((m, i) => (
                                            <motion.div key={`${m.movie_idx}-${i}`}
                                                initial={{ opacity: 0, y: 20, rotate: -1 }}
                                                animate={{ opacity: 1, y: 0, rotate: 0 }}
                                                transition={{
                                                    delay: i * 0.05,
                                                    type: "spring", stiffness: 200,
                                                    damping: 20
                                                }}>
                                                <MovieCard movie={m} index={i}
                                                    onClick={() => setSelected(m)} />
                                            </motion.div>
                                        ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── Static rows ── */}
            <Row title="For You"
                subtitle="personalised hybrid picks"
                movies={forYou} loading={loadingRecs}
                onSelect={setSelected} accentColor="#d2ff00" />

            <Row title="Hidden Gems"
                subtitle="high score · low noise"
                movies={hidden} loading={loadingRecs}
                onSelect={setSelected} accentColor="#9b7fe8" />

            <Row title="Trending This Week"
                subtitle="live from tmdb"
                movies={trending} loading={loadingTmdb}
                onSelect={setSelected} accentColor="#ff003c" />

            <Row title="Now In Cinemas"
                subtitle="currently showing"
                movies={nowPlaying} loading={loadingTmdb}
                onSelect={setSelected} accentColor="#5bc4f0" />

            <Row title="All-Time Greatest"
                subtitle="top rated ever"
                movies={topRated} loading={loadingTmdb}
                onSelect={setSelected} accentColor="#d2ff00" />

            {selected && (
                <MovieModal movie={selected}
                    onClose={() => setSelected(null)} />
            )}
        </div>
    )
}