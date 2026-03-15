import { useState } from "react"

export default function StarRating({ value, onChange, size = 20 }) {
    const [hover, setHover] = useState(0)
    return (
        <div style={{ display: "flex", gap: 4 }}>
            {[1, 2, 3, 4, 5].map(star => (
                <span key={star}
                    onMouseEnter={() => setHover(star)}
                    onMouseLeave={() => setHover(0)}
                    onClick={() => onChange(star)}
                    style={{
                        fontSize: size, cursor: "pointer",
                        color: star <= (hover || value) ? "#d2ff00" : "#333",
                        transition: "color 0.15s",
                    }}>★</span>
            ))}
        </div>
    )
}
