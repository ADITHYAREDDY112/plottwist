import { useState } from "react"
import { motion } from "framer-motion"

const MOOD_CONFIG = [
    { key: "excited", label: "Excited", color: "#d2ff00" },
    { key: "happy", label: "Happy", color: "#ff9100ff" },
    { key: "sad", label: "Sad", color: "#f6f6f6ff" },
    { key: "stressed", label: "Stressed", color: "#040ceeff" },
    { key: "bored", label: "Bored", color: "#46444dff" },
    { key: "reflective", label: "Reflective", color: "#7ad9f0ff" },
    { key: "angry", label: "Angry", color: "#ff003c" },
]

export default function MoodChips({ value, onChange }) {
    const [hovered, setHovered] = useState(null)

    return (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {MOOD_CONFIG.map(m => {
                const active = value === m.key
                const hover = hovered === m.key
                const c = m.color

                return (
                    <motion.button key={m.key}
                        data-hover
                        onHoverStart={() => setHovered(m.key)}
                        onHoverEnd={() => setHovered(null)}
                        onClick={() => onChange(active ? null : m.key)}
                        whileTap={{ scale: 0.95 }}
                        style={{
                            background: active ? c : "transparent",
                            color: active ? "#000" : hover ? c : "#444",
                            border: `1px solid ${active || hover ? c : "#1e1e1e"}`,
                            padding: "12px 28px",
                            fontSize: 11, fontWeight: 700,
                            letterSpacing: 2, textTransform: "uppercase",
                            cursor: "pointer", fontFamily: "Inter, sans-serif",
                            transition: "all 0.2s ease",
                            boxShadow: active
                                ? `0 0 24px ${c}55, 0 0 48px ${c}18`
                                : hover ? `0 0 16px ${c}33` : "none",
                        }}>
                        {m.label}
                    </motion.button>
                )
            })}
        </div>
    )
}