import { create } from "zustand"
import { persist } from "zustand/middleware"

function hashPassword(pass) {
    let hash = 0
    for (let i = 0; i < pass.length; i++)
        hash = (hash * 31 + pass.charCodeAt(i)) & 0xffffffff
    return hash.toString(16)
}

function deriveUserId(uname) {
    let hash = 0
    for (let i = 0; i < uname.length; i++)
        hash = (hash * 31 + uname.charCodeAt(i)) & 0xffff
    return hash % 69000
}

export const useStore = create(persist(
    (set, get) => ({

        // ── Auth ───────────────────────────────────────────────────────────────
        user: null,
        accounts: {},   // { username: { passwordHash, userId } }

        register: (username, password) => {
            const uname = username.toLowerCase().trim()
            const userId = deriveUserId(uname)
            const hash = hashPassword(password)
            set(s => ({
                accounts: { ...s.accounts, [uname]: { passwordHash: hash, userId } },
                user: { username, userId },
                currentMood: null,
            }))
            return "ok"
        },

        login: (username, password) => {
            const uname = username.toLowerCase().trim()
            const account = get().accounts[uname]
            if (!account) return "no_account"
            if (account.passwordHash !== hashPassword(password)) return "wrong_password"
            set({ user: { username, userId: account.userId }, currentMood: null })
            return "ok"
        },

        logout: () => set({
            user: null, watchlist: [], ratings: {},
            onboardingDone: false, currentMood: null,
        }),

        // ── Onboarding ─────────────────────────────────────────────────────────
        onboardingDone: false,
        completeOnboarding: () => set({ onboardingDone: true }),

        // ── Watchlist ──────────────────────────────────────────────────────────
        watchlist: [],
        addToWatchlist: (movie) => {
            const exists = get().watchlist.find(m => m.movie_idx === movie.movie_idx)
            if (!exists) set({ watchlist: [...get().watchlist, movie] })
        },
        removeFromWatchlist: (movieIdx) =>
            set({ watchlist: get().watchlist.filter(m => m.movie_idx !== movieIdx) }),
        isInWatchlist: (movieIdx) =>
            get().watchlist.some(m => m.movie_idx === movieIdx),

        // ── Ratings ────────────────────────────────────────────────────────────
        ratings: {},
        rateMovie: (movieIdx, rating) =>
            set({ ratings: { ...get().ratings, [movieIdx]: rating } }),
        getRating: (movieIdx) => get().ratings[movieIdx] || 0,

        // ── Mood ───────────────────────────────────────────────────────────────
        currentMood: null,
        setMood: (mood) => set({ currentMood: mood }),
    }),
    { name: "plottwist -store" }
))