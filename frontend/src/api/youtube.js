import axios from "axios"
const KEY = import.meta.env.VITE_YOUTUBE_API_KEY
const cache = {}

export const getTrailerId = async (movieTitle, year) => {
    const cacheKey = `${movieTitle}-${year}`
    if (cache[cacheKey] !== undefined) return cache[cacheKey]
    try {
        const res = await axios.get("https://www.googleapis.com/youtube/v3/search", {
            params: {
                key: KEY,
                part: "snippet",
                maxResults: 1,
                type: "video",
                q: `${movieTitle} ${year ?? ""} official trailer`,
            }
        })
        const id = res.data.items?.[0]?.id?.videoId ?? null
        cache[cacheKey] = id
        return id
    } catch (e) {
        console.error("YouTube API error:", e?.response?.data || e.message)
        return null
    }
}