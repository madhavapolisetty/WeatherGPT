
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
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