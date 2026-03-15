import { motion } from "framer-motion"

export default function SkeletonCard() {
    return (
        <motion.div
            animate={{ opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{
                minWidth: 160, aspectRatio: "2/3",
                background: "#1a1a1a", borderRadius: 2, flexShrink: 0
            }}
        />
    )
}
