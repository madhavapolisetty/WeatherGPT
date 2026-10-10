
import axios from "axios";

const localBackend = "http://127.0.0.1:8000";
const deployedBackend =
  "https://weathergpt-backend-kw2c.onrender.com";

const configuredBackend =
  import.meta.env.VITE_API_BASE_URL?.trim();

const api = axios.create({
  baseURL:
    configuredBackend ||
    (import.meta.env.DEV ? localBackend : deployedBackend),
  timeout: 20000,
});

export async function fetchWeather(city) {
  const response = await api.get("/api/weather", {
    params: { city },
  });

  return response.data;
}

export async function askWeatherGPT(city, question) {
  const response = await api.post("/api/chat", {
    city,
    question,
  });

  return response.data;
}