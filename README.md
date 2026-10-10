# 🌦️ WeatherGPT — AI-Powered Weather & Travel Assistant

WeatherGPT is a web application that provides real-time weather information, detailed forecasts, and AI-assisted weather conversations. It also helps users explore driving routes, estimated journey times, traffic information, and weather conditions at departure and destination locations.

## ✨ Features

* **Weather Dashboard:** View current temperature, feels-like temperature, humidity, wind speed, and precipitation.
* **Multi-City Weather Search:** Retrieve weather data for different locations.
* **Detailed Forecasts:** View hourly weather information and a 7-day forecast, including minimum and maximum temperatures, precipitation probability, sunrise, and sunset where available.
* **AI Weather Chatbot:** Ask natural-language questions about weather using a locally running Ollama model.
* **Route & Traffic Estimates:** Calculate driving-route distance, estimated journey time, and reported traffic delay through TomTom.
* **Weather Along a Journey:** View weather conditions at the route's origin and destination.
* **Google Maps Integration:** Open driving directions in Google Maps.
* **Responsive Interface:** Use the React-based web interface on desktop and mobile-sized screens.

## 🛠️ Technology Stack

**Frontend**

* React
* Vite
* JavaScript
* CSS

**Backend**

* Python
* FastAPI
* HTTPX

**Weather and Travel Services**

* Open-Meteo Weather API
* TomTom Search and Routing APIs
* Google Maps directions links

**Local AI**

* Ollama
* Qwen2.5 3B

## 🏗️ Project Structure

```text
weathergpt/
├── backend/
│   ├── main.py
│   ├── weather_service.py
│   ├── ai_service.py
│   ├── traffic_service.py
│   ├── requirements.txt
│   ├── .env
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── App.css
│       └── api.js
├── .gitignore
└── README.md
```

## ⚙️ Prerequisites

Install the following before running the application:

* Python
* Node.js and npm
* Ollama
* The Qwen2.5 3B model
* A TomTom API key for route and traffic features

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd weathergpt
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your repository URL after uploading the project to GitHub.

### 2. Set up the backend

Open a terminal in the project folder and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure the environment variables required by your backend in `backend/.env`. For example:

```env
TOMTOM_API_KEY=your_tomtom_api_key
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=qwen2.5:3b
```

Keep your real API keys private. Never upload `.env` to a public repository.

### 3. Start Ollama

Install Ollama and download the model if you have not already done so:

```powershell
ollama pull qwen2.5:3b
```

Start the model using:

```powershell
ollama run qwen2.5:3b
```

Keep Ollama available while using the AI chatbot.

### 4. Start the FastAPI backend

In the backend terminal, run:

```powershell
python -m uvicorn main:app --reload
```

The backend should be available at:

* API: `http://127.0.0.1:8000`
* Interactive API documentation: `http://127.0.0.1:8000/docs`

### 5. Start the React frontend

Open a **second terminal**:

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL displayed in the terminal, usually:

`http://localhost:5173`

## 🧪 Testing

Test the application with questions such as:

* How is the weather in Chirala?
* What is the temperature in Hyderabad?
* Give me the detailed 7-day weather forecast for Chennai.
* Will it rain in Bengaluru tomorrow?
* Can I travel from Bengaluru to Hyderabad now?

Check that the application identifies the requested location, displays available forecast data, and returns route information when appropriate.

## 🔐 Security Notes

* Keep API keys in environment variables.
* Do not commit `.env`, virtual environments, or Python cache files.
* Keep dependencies documented in `requirements.txt` and `package.json`.
* Validate external API responses and handle timeouts and unavailable data gracefully.

## 📌 Limitations

* Forecast availability depends on the weather provider and requested location.
* Weather forecasts and traffic estimates are not guarantees.
* Route calculation requires a working TomTom API key.
* The local AI chatbot requires Ollama and the selected model to be running.
* The application is currently designed for local development; public deployment requires additional configuration.

## 👨‍💻 Project Purpose

WeatherGPT demonstrates how a modern full-stack application can combine React, Python APIs, weather services, routing information, and local language models in one conversational interface.

**Future Improvements:** Weather alerts, maps embedded in the dashboard, saved locations, forecast visualizations, automated tests, and deployment.
