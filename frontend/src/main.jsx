import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { Toaster } from "react-hot-toast"
import "./index.css"
import App from "./App.jsx"

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#1a1a1a", color: "#f0f0f0",
            border: "1px solid #2a2a2a", fontSize: 13,
            fontFamily: "Inter, sans-serif",
          }
        }}
      />
    </BrowserRouter>
  </StrictMode>
)
