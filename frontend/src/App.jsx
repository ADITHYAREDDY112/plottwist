import { useState } from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import { useStore } from "./store/useStore"
import Loader from "./components/Loader"
import Nav from "./components/Nav"
import Login from "./pages/Login"
import Onboarding from "./pages/Onboarding"
import Home from "./pages/Home"
import Search from "./pages/Search"
import Watchlist from "./pages/Watchlist"
import Profile from "./pages/Profile"

function Protected({ children }) {
  const { user } = useStore()
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { user, onboardingDone } = useStore()
  const [loaded, setLoaded] = useState(false)

  return (
    <>
      {!loaded && <Loader onDone={() => setLoaded(true)} />}

      <div style={{
        opacity: loaded ? 1 : 0,
        transition: "opacity 0.4s ease"
      }}>
        <Nav />
        <Routes>
          <Route path="/login" element={
            user ? <Navigate to="/" replace /> : <Login />
          } />
          <Route path="/onboarding" element={
            <Protected><Onboarding /></Protected>
          } />
          <Route path="/" element={
            <Protected>
              {!onboardingDone
                ? <Navigate to="/onboarding" replace />
                : <Home />}
            </Protected>
          } />
          <Route path="/search" element={<Protected><Search /></Protected>} />
          <Route path="/watchlist" element={<Protected><Watchlist /></Protected>} />
          <Route path="/profile" element={<Protected><Profile /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </>
  )
}