import axios from "axios"
const KEY = import.meta.env.VITE_TMDB_API_KEY
const BASE = "https://api.themoviedb.org/3"
const cache = {}

export const searchMovie = async (title) => {
    if (cache[title]) return cache[title]
    try {
        const res = await axios.get(`${BASE}/search/movie`, {
            params: { api_key: KEY, query: title }
        })
        const movie = res.data.results?.[0]
        cache[title] = movie || null
        return movie || null
    } catch { return null }
}

export const getMovieDetails = async (tmdbId) => {
    try {
        const res = await axios.get(`${BASE}/movie/${tmdbId}`, {
            params: { api_key: KEY, append_to_response: "credits" }
        })
        return res.data
    } catch { return null }
}

export const posterUrl = (path, size = "w400") =>
    path ? `https://image.tmdb.org/t/p/${size}${path}` : null

export const backdropUrl = (path) =>
    path ? `https://image.tmdb.org/t/p/w1280${path}` : null

export const getTrending = async () => {
    try {
        const res = await axios.get(`${BASE}/trending/movie/week`, {
            params: { api_key: KEY }
        })
        return res.data.results?.slice(0, 20) || []
    } catch { return [] }
}

export const getNowPlaying = async () => {
    try {
        const res = await axios.get(`${BASE}/movie/now_playing`, {
            params: { api_key: KEY, region: "US" }
        })
        return res.data.results?.slice(0, 20) || []
    } catch { return [] }
}

export const getTopRated = async () => {
    try {
        const res = await axios.get(`${BASE}/movie/top_rated`, {
            params: { api_key: KEY }
        })
        return res.data.results?.slice(0, 20) || []
    } catch { return [] }
}

export const tmdbToMovie = (r, rank) => ({
    movie_idx: r.id,
    title: r.title,
    genres: r.genre_ids?.join(" ") || "",
    arc: "neutral_fun",
    score: r.vote_average / 10,
    rank: rank || null,
})