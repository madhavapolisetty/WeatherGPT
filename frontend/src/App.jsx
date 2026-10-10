import { useState } from "react";
import { fetchWeather, askWeatherGPT } from "./api";
import "./App.css";

// --------------------------------------------------
// Weather codes
// --------------------------------------------------

function getForecastCondition(code) {
  const descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
  };

  if (code === null || code === undefined) {
    return "Not available";
  }

  return descriptions[code] || "Condition unavailable";
}

// --------------------------------------------------
// Format weather values
// --------------------------------------------------

function formatWeatherValue(value, unit = "") {
  if (value === null || value === undefined) {
    return "N/A";
  }

  const formattedValue =
    typeof value === "number" && !Number.isInteger(value)
      ? Math.round(value * 10) / 10
      : value;

  return `${formattedValue}${unit}`;
}

function formatTime(value) {
  if (!value) {
    return "N/A";
  }

  const parts = String(value).split("T");

  return parts.length > 1
    ? parts[1].slice(0, 5)
    : value;
}

// --------------------------------------------------
// Weather card for route origin or destination
// --------------------------------------------------

function EndpointWeatherCard({ title, data }) {
  const location = data?.location || {};
  const weather = data?.weather || {};
  const current = weather?.current || {};
  const units = weather?.current_units || {};

  if (current.temperature_2m == null) {
    return (
      <article className="endpoint-weather">
        <h4>{title}</h4>

        <p className="endpoint-location">
          {location.name || "Location"}
        </p>

        <p>Weather readings are unavailable.</p>
      </article>
    );
  }

  return (
    <article className="endpoint-weather">
      <h4>{title}</h4>

      <p className="endpoint-location">
        {location.name || "Location"}
        {location.country ? `, ${location.country}` : ""}
      </p>

      <p>
        {getForecastCondition(current.weather_code)}
      </p>

      <div className="endpoint-temperature">
        {formatWeatherValue(
          current.temperature_2m,
          units.temperature_2m || "°C"
        )}
      </div>

      <p>
        Feels like:{" "}
        {formatWeatherValue(
          current.apparent_temperature,
          units.apparent_temperature || "°C"
        )}
      </p>

      <p>
        Humidity:{" "}
        {formatWeatherValue(
          current.relative_humidity_2m,
          units.relative_humidity_2m || "%"
        )}
      </p>

      <p>
        Wind:{" "}
        {formatWeatherValue(
          current.wind_speed_10m,
          ` ${units.wind_speed_10m || "km/h"}`
        )}
      </p>

      <p>
        Precipitation:{" "}
        {formatWeatherValue(
          current.precipitation,
          ` ${units.precipitation || "mm"}`
        )}
      </p>

      <p className="endpoint-time">
        Updated: {current.time || "Time unavailable"}
      </p>
    </article>
  );
}

// --------------------------------------------------
// Detailed forecast for the city requested in chat
// --------------------------------------------------

function ForecastDetails({ data }) {
  if (!data?.weather) {
    return null;
  }

  const location = data.location || {};
  const weather = data.weather || {};

  const current = weather.current || {};
  const currentUnits = weather.current_units || {};

  const hourly = weather.hourly || {};
  const hourlyUnits = weather.hourly_units || {};
  const hourlyTimes = hourly.time || [];

  const daily = weather.daily || {};
  const dailyUnits = weather.daily_units || {};
  const dailyTimes = daily.time || [];

  // Find the current or next available forecast hour.
  const currentTime = current.time || "";

  const firstHour = currentTime
    ? hourlyTimes.findIndex((time) => time >= currentTime)
    : 0;

  const hourlyStart = firstHour >= 0 ? firstHour : 0;

  const hourlyIndices = Array.from(
    {
      length: Math.min(
        12,
        Math.max(0, hourlyTimes.length - hourlyStart)
      ),
    },
    (_, offset) => hourlyStart + offset
  );

  return (
    <section className="forecast-details">
      <h3>
        🌦️ Detailed Forecast — {location.name || "Selected location"}
        {location.country ? `, ${location.country}` : ""}
      </h3>

      <p className="forecast-source">
        Source: {data.source || "Weather provider"}
        {current.time ? ` · Observation time: ${current.time}` : ""}
      </p>

      {/* CURRENT WEATHER */}

      <h4>🌡️ Current Weather</h4>

      <div className="forecast-current-grid">
        <div className="forecast-stat">
          <span>Condition</span>
          <strong>
            {getForecastCondition(current.weather_code)}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Temperature</span>
          <strong>
            {formatWeatherValue(
              current.temperature_2m,
              currentUnits.temperature_2m || "°C"
            )}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Feels Like</span>
          <strong>
            {formatWeatherValue(
              current.apparent_temperature,
              currentUnits.apparent_temperature || "°C"
            )}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Humidity</span>
          <strong>
            {formatWeatherValue(
              current.relative_humidity_2m,
              currentUnits.relative_humidity_2m || "%"
            )}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Wind Speed</span>
          <strong>
            {formatWeatherValue(
              current.wind_speed_10m,
              ` ${currentUnits.wind_speed_10m || "km/h"}`
            )}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Precipitation</span>
          <strong>
            {formatWeatherValue(
              current.precipitation,
              ` ${currentUnits.precipitation || "mm"}`
            )}
          </strong>
        </div>

        <div className="forecast-stat">
          <span>Day / Night</span>
          <strong>
            {current.is_day === 1
              ? "Daytime"
              : current.is_day === 0
                ? "Nighttime"
                : "N/A"}
          </strong>
        </div>
      </div>

      {/* HOURLY FORECAST */}

      <h4>🕒 Hourly Forecast — Next 12 Hours</h4>

      {hourlyIndices.length > 0 ? (
        <div className="forecast-table-wrapper">
          <table className="forecast-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Condition Code</th>
                <th>Temperature</th>
                <th>Rain Probability</th>
                <th>Precipitation</th>
              </tr>
            </thead>

            <tbody>
              {hourlyIndices.map((index) => (
                <tr
                  key={`${hourlyTimes[index]}-${index}`}
                >
                  <td>
                    {String(hourlyTimes[index]).replace("T", " ")}
                  </td>

                  <td>
                    {getForecastCondition(
                      hourly.weather_code?.[index]
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      hourly.temperature_2m?.[index],
                      hourlyUnits.temperature_2m || "°C"
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      hourly.precipitation_probability?.[index],
                      hourlyUnits.precipitation_probability || "%"
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      hourly.precipitation?.[index],
                      ` ${hourlyUnits.precipitation || "mm"}`
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>Hourly forecast is unavailable for this location.</p>
      )}

      {/* DAILY FORECAST */}

      <h4>📅 7-Day Forecast</h4>

      {dailyTimes.length > 0 ? (
        <div className="forecast-table-wrapper">
          <table className="forecast-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Condition</th>
                <th>Min Temperature</th>
                <th>Max Temperature</th>
                <th>Rain Probability</th>
                <th>Precipitation</th>
                <th>Sunrise</th>
                <th>Sunset</th>
              </tr>
            </thead>

            <tbody>
              {dailyTimes.map((date, index) => (
                <tr key={date}>
                  <td>{date}</td>

                  <td>
                    {getForecastCondition(
                      daily.weather_code?.[index]
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      daily.temperature_2m_min?.[index],
                      dailyUnits.temperature_2m_min || "°C"
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      daily.temperature_2m_max?.[index],
                      dailyUnits.temperature_2m_max || "°C"
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      daily.precipitation_probability_max?.[index],
                      dailyUnits.precipitation_probability_max || "%"
                    )}
                  </td>

                  <td>
                    {formatWeatherValue(
                      daily.precipitation_sum?.[index],
                      ` ${dailyUnits.precipitation_sum || "mm"}`
                    )}
                  </td>

                  <td>
                    {formatTime(daily.sunrise?.[index])}
                  </td>

                  <td>
                    {formatTime(daily.sunset?.[index])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>Daily forecast is unavailable for this location.</p>
      )}

      <p className="forecast-disclaimer">
        Forecasts are estimates and can change as weather conditions change.
      </p>
    </section>
  );
}

// --------------------------------------------------
// Main WeatherGPT application
// --------------------------------------------------

function App() {
  const [city, setCity] = useState("Bengaluru");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");

  // --------------------------------------------------
  // Fetch dashboard weather
  // --------------------------------------------------

  async function searchWeather(event) {
    event.preventDefault();

    const selectedCity = city.trim();

    if (!selectedCity || loading) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await fetchWeather(selectedCity);
      setData(result);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Could not load weather. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // Submit a question to WeatherGPT
  // --------------------------------------------------

  async function handleChatSubmit(event) {
    event.preventDefault();

    const question = chatQuestion.trim();
    const selectedCity = city.trim();

    if (!question || !selectedCity || chatLoading) {
      return;
    }

    setChatMessages((previous) => [
      ...previous,
      {
        role: "user",
        text: question,
      },
    ]);

    setChatQuestion("");
    setChatError("");
    setChatLoading(true);

    try {
      const result = await askWeatherGPT(
        selectedCity,
        question
      );

      setChatMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text:
            result.answer ||
            "The AI returned an empty answer.",

          // Requested weather location and raw forecast data
          weatherCity:
            result.weather_city ||
            result.weather_data?.location?.name ||
            selectedCity,

          weatherData: result.weather_data || null,

          // Route details
          routeUrl: result.route_url || "",
          routeInfo: result.route_info || null,
          routeError: result.route_error || "",

          // Weather at both ends of a route
          routeWeather: result.route_weather || null,
          routeWeatherError:
            result.route_weather_error || "",
        },
      ]);
    } catch (err) {
      setChatError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to connect to the AI chatbot."
      );
    } finally {
      setChatLoading(false);
    }
  }

  const current = data?.weather?.current;
  const daily = data?.weather?.daily;

  // --------------------------------------------------
  // User interface
  // --------------------------------------------------

  return (
    <main className="app">
      {/* HEADER */}

      <header className="app-header">
        <h1>🌦️ WeatherGPT</h1>
        <p>Your conversational weather assistant</p>
      </header>

      {/* CITY SEARCH */}

      <section className="search-section">
        <form
          className="search-form"
          onSubmit={searchWeather}
        >
          <input
            value={city}
            onChange={(event) =>
              setCity(event.target.value)
            }
            placeholder="Enter a city"
            aria-label="City name"
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Loading..." : "Get weather"}
          </button>
        </form>

        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
      </section>

      {/* WEATHER DASHBOARD */}

      {data && current && (
        <section className="weather-card">
          <h2>
            {data.location.name}
            {data.location.country
              ? `, ${data.location.country}`
              : ""}
          </h2>

          <p>
            {getForecastCondition(current.weather_code)}
          </p>

          <div className="temperature">
            {formatWeatherValue(
              current.temperature_2m,
              data.weather?.current_units?.temperature_2m || "°C"
            )}
          </div>

          <p>
            Feels like:{" "}
            {formatWeatherValue(
              current.apparent_temperature,
              data.weather?.current_units?.apparent_temperature ||
                "°C"
            )}
          </p>

          <p>
            Humidity:{" "}
            {formatWeatherValue(
              current.relative_humidity_2m,
              data.weather?.current_units?.relative_humidity_2m ||
                "%"
            )}
          </p>

          <p>
            Wind:{" "}
            {formatWeatherValue(
              current.wind_speed_10m,
              ` ${
                data.weather?.current_units?.wind_speed_10m ||
                "km/h"
              }`
            )}
          </p>

          <p>
            Precipitation:{" "}
            {formatWeatherValue(
              current.precipitation,
              ` ${
                data.weather?.current_units?.precipitation ||
                "mm"
              }`
            )}
          </p>

          {daily?.time?.length > 0 && (
            <>
              <h3>7-Day Forecast</h3>

              <div className="forecast-list">
                {daily.time.map((day, index) => (
                  <div
                    className="forecast-item"
                    key={day}
                  >
                    <span>{day}</span>

                    <span>
                      {formatWeatherValue(
                        daily.temperature_2m_min?.[index],
                        "°C"
                      )}
                      {" – "}
                      {formatWeatherValue(
                        daily.temperature_2m_max?.[index],
                        "°C"
                      )}
                    </span>

                    <span>
                      Rain chance:{" "}
                      {formatWeatherValue(
                        daily.precipitation_probability_max?.[
                          index
                        ],
                        "%"
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* WEATHERGPT CHATBOT */}

      <section className="chat-section">
        <div className="chat-header">
          <div className="chat-avatar">🤖</div>

          <div>
            <h2>Ask WeatherGPT</h2>
            <p>
              Ask about weather or travel in{" "}
              {city || "your city"}.
            </p>
          </div>
        </div>

        {/* CHAT MESSAGES */}

        <div className="chat-messages" aria-live="polite">
          {chatMessages.length === 0 && (
            <div className="chat-welcome">
              <p>
                👋 Hello! I'm your AI weather assistant.
              </p>

              <p>Try asking:</p>

              <button
                type="button"
                className="suggestion-button"
                onClick={() =>
                  setChatQuestion(
                    "How is the weather in Chirala?"
                  )
                }
              >
                🌤️ How is the weather in Chirala?
              </button>

              <button
                type="button"
                className="suggestion-button"
                onClick={() =>
                  setChatQuestion(
                    "Give me the detailed 7-day weather forecast for Hyderabad"
                  )
                }
              >
                📅 Give me the 7-day forecast for Hyderabad
              </button>

              <button
                type="button"
                className="suggestion-button"
                onClick={() =>
                  setChatQuestion(
                    "Will it rain in Chennai tomorrow?"
                  )
                }
              >
                🌧️ Will it rain in Chennai tomorrow?
              </button>

              <button
                type="button"
                className="suggestion-button"
                onClick={() =>
                  setChatQuestion(
                    "Can I travel from Bengaluru to Hyderabad now?"
                  )
                }
              >
                🚗 Can I travel from Bengaluru to Hyderabad now?
              </button>
            </div>
          )}

          {chatMessages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`chat-message ${message.role}`}
            >
              <strong>
                {message.role === "user"
                  ? "You"
                  : "WeatherGPT"}
              </strong>

              <p>{message.text}</p>

              {/* DETAILED FORECAST FOR THE REQUESTED CITY */}

              {message.role === "assistant" &&
                message.weatherData &&
                !message.routeUrl && (
                  <ForecastDetails
                    data={message.weatherData}
                  />
                )}

              {/* ROUTE ESTIMATE */}

              {message.role === "assistant" &&
                message.routeInfo && (
                  <div className="route-info-card">
                    <h3>🚗 Route estimate</h3>

                    <p>
                      <strong>Origin:</strong>{" "}
                      {message.routeInfo.origin}
                    </p>

                    <p>
                      <strong>Destination:</strong>{" "}
                      {message.routeInfo.destination}
                    </p>

                    <div className="route-stats">
                      <div className="route-stat">
                        <span>Distance</span>
                        <strong>
                          {message.routeInfo.distance_km != null
                            ? `${message.routeInfo.distance_km} km`
                            : "Unavailable"}
                        </strong>
                      </div>

                      <div className="route-stat">
                        <span>Estimated journey</span>
                        <strong>
                          {message.routeInfo.estimated_minutes !=
                          null
                            ? `${message.routeInfo.estimated_minutes} min`
                            : "Unavailable"}
                        </strong>
                      </div>

                      <div className="route-stat">
                        <span>Reported traffic delay</span>
                        <strong>
                          {message.routeInfo.traffic_delay_minutes !=
                          null
                            ? `${message.routeInfo.traffic_delay_minutes} min`
                            : "Unavailable"}
                        </strong>
                      </div>
                    </div>

                    <p className="route-disclaimer">
                      Journey times are estimates, not guaranteed
                      arrival times. Check the latest route and
                      traffic conditions before travelling.
                    </p>
                  </div>
                )}

              {/* WEATHER AT ORIGIN AND DESTINATION */}

              {message.role === "assistant" &&
                message.routeWeather && (
                  <section className="route-weather-card">
                    <h3>🌦️ Weather at both ends</h3>

                    <div className="route-weather-grid">
                      <EndpointWeatherCard
                        title="📍 Departure"
                        data={message.routeWeather.origin}
                      />

                      <EndpointWeatherCard
                        title="🏁 Destination"
                        data={message.routeWeather.destination}
                      />
                    </div>
                  </section>
                )}

              {/* ROUTE WEATHER ERROR */}

              {message.role === "assistant" &&
                message.routeWeatherError && (
                  <p className="route-error-message">
                    {message.routeWeatherError}
                  </p>
                )}

              {/* ROUTE CALCULATION ERROR */}

              {message.role === "assistant" &&
                message.routeError &&
                !message.routeInfo && (
                  <p className="route-error-message">
                    {message.routeError}
                  </p>
                )}

              {/* GOOGLE MAPS LINK */}

              {message.role === "assistant" &&
                message.routeUrl && (
                  <div className="route-link-container">
                    <a
                      href={message.routeUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Check Route &amp; Live Traffic in Google Maps ↗
                    </a>
                  </div>
                )}
            </div>
          ))}

          {/* LOADING MESSAGE */}

          {chatLoading && (
            <div className="chat-message assistant">
              <strong>WeatherGPT</strong>
              <p>Thinking...</p>
            </div>
          )}
        </div>

        {/* CHAT ERROR */}

        {chatError && (
          <p className="error-message" role="alert">
            {chatError}
          </p>
        )}

        {/* CHAT INPUT */}

        <form
          className="chat-form"
          onSubmit={handleChatSubmit}
        >
          <input
            value={chatQuestion}
            onChange={(event) =>
              setChatQuestion(event.target.value)
            }
            placeholder="Ask about weather or travel..."
            aria-label="Your weather or travel question"
            minLength={3}
            maxLength={1000}
            required
          />

          <button type="submit" disabled={chatLoading}>
            {chatLoading ? "Thinking..." : "Ask AI ➤"}
          </button>
        </form>

        <p className="chat-note">
          Weather forecasts and route estimates may change
          as conditions change.
        </p>
      </section>

      {/* FOOTER */}

      <footer className="app-footer">
        <p>
          🌦️ WeatherGPT · Weather, local AI, and route estimates
        </p>
      </footer>
    </main>
  );
}

export default App;