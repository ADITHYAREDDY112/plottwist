import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import toast from "react-hot-toast"
import { useStore } from "../store/useStore"
import { searchMovie, posterUrl } from "../api/tmdb"
import StarRating from "../components/StarRating"

const SEED_MOVIES = [
    { movie_idx: 296, title: "Pulp Fiction", arc: "tense_release" },
    { movie_idx: 318, title: "Shawshank Redemption", arc: "cathartic" },
    { movie_idx: 858, title: "The Godfather", arc: "cathartic" },
    { movie_idx: 4993, title: "The Lord of the Rings", arc: "uplifting" },
    { movie_idx: 356, title: "Forrest Gump", arc: "bittersweet" },
    { movie_idx: 593, title: "The Silence of the Lambs", arc: "tense_release" },
    { movie_idx: 260, title: "Star Wars", arc: "uplifting" },
    { movie_idx: 480, title: "Jurassic Park", arc: "tense_release" },
]

export default function Onboarding() {
    const [posters, setPosters] = useState({})
    const [step, setStep] = useState(0)
    const { rateMovie, completeOnboarding } = useStore()
    const navigate = useNavigate()
    const movie = SEED_MOVIES[step]

    useEffect(() => {
        SEED_MOVIES.forEach(m => {
            searchMovie(m.title).then(r => {
                if (r?.poster_path)
                    setPosters(p => ({ ...p, [m.movie_idx]: posterUrl(r.poster_path, "w400") }))
            })
        })
    }, [])

    function handleRate(rating) {
        rateMovie(movie.movie_idx, rating)
        toast.success(`${rating}★`)
        if (step < SEED_MOVIES.length - 1) setStep(s => s + 1)
        else {
            completeOnboarding()
            navigate("/")
        }
    }

    function skip() {
        completeOnboarding()
        navigate("/")
    }

    return (
        <div style={{
            minHeight: "100vh", display: "flex",
            flexDirection: "column", alignItems: "center",
            justifyContent: "center", padding: 48
        }}>

            {/* Progress */}
            <div style={{ display: "flex", gap: 6, marginBottom: 48 }}>
                {SEED_MOVIES.map((_, i) => (
                    <div key={i} style={{
                        width: 24, height: 3,
                        background: i <= step ? "#d2ff00" : "#1a1a1a",
                        transition: "background 0.3s",
                    }} />
                ))}
            </div>

            <motion.p
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{
                    fontSize: 11, letterSpacing: 4, color: "#555",
                    textTransform: "uppercase", marginBottom: 16
                }}>
                Rate to calibrate your taste — {step + 1} of {SEED_MOVIES.length}
            </motion.p>

            <AnimatePresence mode="wait">
                <motion.div key={step}
                    initial={{ opacity: 0, x: 40 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -40 }}
                    transition={{ duration: 0.3 }}
                    style={{ textAlign: "center", maxWidth: 320 }}>

                    {posters[movie.movie_idx] && (
                        <img src={posters[movie.movie_idx]} alt={movie.title}
                            style={{
                                width: 200, marginBottom: 28,
                                boxShadow: "0 32px 64px rgba(0,0,0,0.8)"
                            }} />
                    )}

                    <h2 style={{
                        fontSize: 24, fontWeight: 900, letterSpacing: -1,
                        marginBottom: 24
                    }}>
                        {movie.title}
                    </h2>

                    <div style={{
                        display: "flex", justifyContent: "center",
                        marginBottom: 20
                    }}>
                        <StarRating value={0} onChange={handleRate} size={36} />
                    </div>

                    <button onClick={() => handleRate(0)}
                        style={{
                            fontSize: 11, color: "#333", background: "none",
                            border: "none", cursor: "pointer", letterSpacing: 2,
                            textTransform: "uppercase",
                            fontFamily: "Inter, sans-serif"
                        }}>
                        Haven't seen it →
                    </button>
                </motion.div>
            </AnimatePresence>

            <button onClick={skip}
                style={{
                    marginTop: 48, fontSize: 11, color: "#333",
                    background: "none", border: "none", cursor: "pointer",
                    letterSpacing: 2, textTransform: "uppercase",
                    fontFamily: "Inter, sans-serif"
                }}>
                Skip onboarding
            </button>
        </div>
    )
}
