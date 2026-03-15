import { useEffect, useRef } from "react"
import { motion, useMotionValue, useSpring } from "framer-motion"

export default function Cursor() {
    const x = useMotionValue(-100)
    const y = useMotionValue(-100)
    const sx = useSpring(x, { stiffness: 300, damping: 28 })
    const sy = useSpring(y, { stiffness: 300, damping: 28 })
    const ref = useRef(null)

    useEffect(() => {
        const move = (e) => { x.set(e.clientX); y.set(e.clientY) }
        const over = () => ref.current?.classList.add("expanded")
        const out = () => ref.current?.classList.remove("expanded")

        window.addEventListener("mousemove", move)
        document.querySelectorAll("button, a, [data-hover]")
            .forEach(el => {
                el.addEventListener("mouseenter", over)
                el.addEventListener("mouseleave", out)
            })
        return () => window.removeEventListener("mousemove", move)
    }, [])

    return (
        <>
            {/* Dot */}
            <motion.div style={{
                position: "fixed", top: 0, left: 0, zIndex: 99999,
                width: 6, height: 6, borderRadius: "50%",
                background: "#d2ff00", pointerEvents: "none",
                translateX: x, translateY: y,
                marginLeft: -3, marginTop: -3,
            }} />
            {/* Ring */}
            <motion.div ref={ref} style={{
                position: "fixed", top: 0, left: 0, zIndex: 99998,
                width: 32, height: 32, borderRadius: "50%",
                border: "1px solid rgba(210,255,0,0.4)",
                pointerEvents: "none",
                translateX: sx, translateY: sy,
                marginLeft: -16, marginTop: -16,
                transition: "width 0.2s, height 0.2s, border-color 0.2s",
            }}
                className="cursor-ring"
            />
            <style>{`
        .cursor-ring.expanded {
          width: 56px !important;
          height: 56px !important;
          margin-left: -28px !important;
          margin-top: -28px !important;
          border-color: rgba(210,255,0,0.8) !important;
        }
      `}</style>
        </>
    )
}
