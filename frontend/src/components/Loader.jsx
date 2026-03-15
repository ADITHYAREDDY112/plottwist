import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"

const QUOTE = "popcorn not included but highly recommended."
const LETTERS = "plottwist ".split("")
const DURATION = 4000   // total loader duration ms

export default function Loader({ onDone }) {
    const [typed, setTyped] = useState("")
    const [exit, setExit] = useState(false)
    const [visible, setVisible] = useState(true)

    // Lock scroll
    useEffect(() => {
        document.body.style.overflow = "hidden"
        return () => { document.body.style.overflow = "" }
    }, [])

    // Typewriter — starts after letters animate in (~1.8s)
    useEffect(() => {
        const start = setTimeout(() => {
            let i = 0
            const tick = setInterval(() => {
                setTyped(QUOTE.slice(0, ++i))
                if (i >= QUOTE.length) clearInterval(tick)
            }, 52)
            return () => clearInterval(tick)
        }, 1100)
        return () => clearTimeout(start)
    }, [])

    // Exit timeline
    useEffect(() => {
        const t1 = setTimeout(() => setExit(true), DURATION - 800)
        const t2 = setTimeout(() => {
            setVisible(false)
            document.body.style.overflow = ""
            onDone()
        }, DURATION)
        return () => { clearTimeout(t1); clearTimeout(t2) }
    }, [])

    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    exit={{
                        clipPath: ["inset(0% 0% 0% 0%)", "inset(50% 0% 50% 0%)"],
                        filter: ["blur(0px)", "blur(12px)"],
                        opacity: [1, 0],
                        transition: { duration: 0.7, ease: [0.76, 0, 0.24, 1] }
                    }}
                    style={{
                        position: "fixed", inset: 0,
                        background: "#020202",
                        display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center",
                        overflow: "hidden", zIndex: 9999,
                    }}>

                    {/* Projector beam from top */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: exit ? 0 : 0.2 }}
                        transition={{ duration: 2 }}
                        style={{
                            position: "absolute", top: -200,
                            left: "50%", transform: "translateX(-50%)",
                            width: "60vw", height: "120vh",
                            background: "conic-gradient(from 180deg at 50% 0%, transparent 70deg, rgba(255,255,255,0.08) 90deg, transparent 110deg)",
                            pointerEvents: "none",
                        }} />

                    {/* Cinema screen glow */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.85 }}
                        animate={{ opacity: exit ? 0 : 1, scale: 1 }}
                        transition={{ duration: 2.4, ease: [0.16, 1, 0.3, 1] }}
                        style={{
                            position: "absolute",
                            width: "70vw", height: "35vh",
                            background: "radial-gradient(ellipse, rgba(210,255,0,0.04) 0%, transparent 70%)",
                            filter: "blur(60px)",
                            pointerEvents: "none",
                        }} />

                    {/* plottwist  letters */}
                    <div style={{ display: "flex", gap: 6, position: "relative" }}>
                        {LETTERS.map((l, i) => (
                            <motion.span key={i}
                                initial={{ opacity: 0, y: 60, filter: "blur(8px)" }}
                                animate={{
                                    opacity: exit ? 0 : 1,
                                    y: exit ? -50 : 0,
                                    filter: exit ? "blur(12px)" : "blur(0px)",
                                }}
                                transition={{
                                    delay: exit ? i * 0.03 : 0.4 + i * 0.07,
                                    duration: exit ? 0.4 : 1.0,
                                    ease: [0.16, 1, 0.3, 1],
                                }}
                                style={{
                                    fontSize: "clamp(72px, 11vw, 160px)",
                                    fontWeight: 900,
                                    letterSpacing: -4,
                                    lineHeight: 1,
                                    color: i >= 4 ? "#d2ff00" : "#ebebeb",
                                    textShadow: i >= 4
                                        ? "0 0 60px rgba(210,255,0,0.3)"
                                        : "0 0 40px rgba(255,255,255,0.1)",
                                }}>
                                {l}
                            </motion.span>
                        ))}
                    </div>

                    {/* Typewriter quote */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: exit ? 0 : 1 }}
                        transition={{ delay: 1.6, duration: 0.6 }}
                        style={{
                            marginTop: 28,
                            fontSize: "clamp(13px, 1.8vw, 18px)",
                            fontWeight: 200,
                            fontStyle: "italic",
                            color: "#444",
                            letterSpacing: 2,
                            minHeight: 28,
                            display: "flex", alignItems: "center", gap: 2,
                        }}>
                        {typed}
                        <motion.span
                            animate={{ opacity: [1, 0, 1] }}
                            transition={{ duration: 0.8, repeat: Infinity }}
                            style={{ color: "#d2ff00", fontStyle: "normal" }}>
                            |
                        </motion.span>
                    </motion.div>

                    {/* Film grain flicker */}
                    <motion.div
                        animate={{ opacity: [0.03, 0.06, 0.03, 0.05, 0.03] }}
                        transition={{ duration: 2.5, repeat: Infinity }}
                        style={{
                            position: "absolute", inset: 0,
                            background: "linear-gradient(transparent 49.5%, rgba(255,255,255,0.02) 50%, transparent 50.5%)",
                            backgroundSize: "100% 4px",
                            pointerEvents: "none",
                        }} />

                    {/* Progress bar */}
                    <motion.div
                        style={{
                            position: "absolute", bottom: 0, left: 0,
                            height: 2, background: "#d2ff00",
                            boxShadow: "0 0 12px rgba(210,255,0,0.6)",
                        }}
                        initial={{ width: "0%" }}
                        animate={{ width: "100%" }}
                        transition={{ duration: DURATION / 1000, ease: "linear" }}
                    />

                    {/* Scanline overlay */}
                    <motion.div
                        animate={{ backgroundPosition: ["0 0", "0 100vh"] }}
                        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                        style={{
                            position: "absolute", inset: 0, pointerEvents: "none",
                            background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)",
                            opacity: 0.4,
                        }} />

                </motion.div>
            )}
        </AnimatePresence>
    )
}