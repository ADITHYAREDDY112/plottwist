import axios from "axios"
const API = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const getRecommendations = async (userId, mood, topK = 20) => {
    try {
        // Clamp userId to valid range
        const safeId = Math.abs(Math.floor(userId)) % 69000
        const res = await axios.post(`${API}/recommend`, {
            user_idx: safeId,
            mood: mood || undefined,
            top_k: topK,
        })
        return res.data.results || []
    } catch (e) {
        console.error("Recommend failed:", e.response?.data || e.message)
        return []
    }
}

export const getUserHistory = async (userId) => {
    try {
        const safeId = Math.abs(Math.floor(userId)) % 69000
        const res = await axios.get(`${API}/user/${safeId}/history?top_n=20`)
        return res.data.history || []
    } catch { return [] }
}

export const checkHealth = () =>
    axios.get(`${API}/health`).then(r => r.data)