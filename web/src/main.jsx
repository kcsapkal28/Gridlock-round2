import React from "react";
import { createRoot } from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./theme.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(<App />);
