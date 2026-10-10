import json
import os
import re

import httpx


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat",
)
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
)


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_description(code):
    if code is None:
        return "Not available"

    try:
        return WEATHER_CODES.get(int(code), "Condition unavailable")
    except (ValueError, TypeError):
        return "Condition unavailable"


def show_value(value, unit=""):
    if value is None:
        return "Not available"

    if isinstance(value, float):
        value = round(value, 1)

    return f"{value}{unit}"


def get_item(values, index, default=None):
    if not isinstance(values, list):
        return default

    if 0 <= index < len(values):
        return values[index]

    return default


def format_time(value):
    if not value:
        return "Not available"

    if "T" in str(value):
        return str(value).split("T", 1)[1][:5]

    return str(value)


def format_duration(minutes):
    if minutes is None:
        return "Not available"

    total_minutes = max(0, round(minutes))
    hours, mins = divmod(total_minutes, 60)

    if hours and mins:
        return f"{hours} hours {mins} minutes"
    if hours:
        return f"{hours} hours"

    return f"{mins} minutes"


def describe_location_weather(place_weather, label):
    if not place_weather:
        return f"{label}: weather data is unavailable."

    location = place_weather.get("location", {})
    weather = place_weather.get("weather", {})
    current = weather.get("current", {})
    units = weather.get("current_units", {})

    place_name = location.get("name", label)

    temperature = show_value(
        current.get("temperature_2m"),
        units.get("temperature_2m", "°C"),
    )
    feels_like = show_value(
        current.get("apparent_temperature"),
        units.get("apparent_temperature", "°C"),
    )
    humidity = show_value(
        current.get("relative_humidity_2m"),
        units.get("relative_humidity_2m", "%"),
    )
    wind = show_value(
        current.get("wind_speed_10m"),
        " " + units.get("wind_speed_10m", "km/h"),
    )
    precipitation = show_value(
        current.get("precipitation"),
        " " + units.get("precipitation", "mm"),
    )
    condition = weather_description(current.get("weather_code"))

    return (
        f"{label} weather at {place_name}: {condition}; "
        f"temperature {temperature}; feels like {feels_like}; "
        f"humidity {humidity}; wind speed {wind}; "
        f"precipitation {precipitation}."
    )


def build_forecast_report(weather_data):
    """Build a detailed report directly from the weather API response."""

    location = weather_data.get("location", {})
    weather = weather_data.get("weather", {})

    current = weather.get("current", {})
    current_units = weather.get("current_units", {})

    place_name = location.get("name", "Selected location")
    country = location.get("country")

    title = place_name
    if country:
        title += f", {country}"

    lines = [
        f"Weather report for {title}",
        f"Data source: {weather_data.get('source', 'Weather provider')}",
        "",
        "CURRENT WEATHER",
        f"Condition: {weather_description(current.get('weather_code'))}",
        (
            "Temperature: "
            + show_value(
                current.get("temperature_2m"),
                current_units.get("temperature_2m", "°C"),
            )
        ),
        (
            "Feels like: "
            + show_value(
                current.get("apparent_temperature"),
                current_units.get("apparent_temperature", "°C"),
            )
        ),
        (
            "Humidity: "
            + show_value(
                current.get("relative_humidity_2m"),
                current_units.get("relative_humidity_2m", "%"),
            )
        ),
        (
            "Wind speed: "
            + show_value(
                current.get("wind_speed_10m"),
                " " + current_units.get("wind_speed_10m", "km/h"),
            )
        ),
        (
            "Precipitation: "
            + show_value(
                current.get("precipitation"),
                " " + current_units.get("precipitation", "mm"),
            )
        ),
        (
            "Daylight: "
            + (
                "Daytime"
                if current.get("is_day") == 1
                else "Nighttime"
                if current.get("is_day") == 0
                else "Not available"
            )
        ),
        f"Local observation time: {current.get('time', 'Not available')}",
    ]

    # Hourly forecast
    hourly = weather.get("hourly", {})
    hourly_units = weather.get("hourly_units", {})
    hourly_times = hourly.get("time", [])

    lines.extend(["", "HOURLY FORECAST — NEXT 12 HOURS"])

    if hourly_times:
        current_time = str(current.get("time", ""))[:13]

        start_index = next(
            (
                index
                for index, time_value in enumerate(hourly_times)
                if str(time_value)[:13] >= current_time
            ),
            0,
        )

        end_index = min(start_index + 12, len(hourly_times))

        for index in range(start_index, end_index):
            time_value = hourly_times[index]

            temperature = get_item(
                hourly.get("temperature_2m", []),
                index,
            )
            rain_chance = get_item(
                hourly.get("precipitation_probability", []),
                index,
            )
            precipitation = get_item(
                hourly.get("precipitation", []),
                index,
            )

            lines.append(
                f"{time_value}: "
                f"temperature {show_value(temperature, hourly_units.get('temperature_2m', '°C'))}; "
                f"rain probability {show_value(rain_chance, hourly_units.get('precipitation_probability', '%'))}; "
                f"precipitation {show_value(precipitation, ' ' + hourly_units.get('precipitation', 'mm'))}."
            )
    else:
        lines.append("Hourly forecast data is unavailable.")

    # Daily forecast
    daily = weather.get("daily", {})
    daily_units = weather.get("daily_units", {})
    daily_times = daily.get("time", [])

    lines.extend(["", "7-DAY FORECAST"])

    if daily_times:
        for index, date in enumerate(daily_times):
            condition = weather_description(
                get_item(daily.get("weather_code", []), index)
            )
            minimum = get_item(
                daily.get("temperature_2m_min", []),
                index,
            )
            maximum = get_item(
                daily.get("temperature_2m_max", []),
                index,
            )
            rain_chance = get_item(
                daily.get("precipitation_probability_max", []),
                index,
            )
            precipitation = get_item(
                daily.get("precipitation_sum", []),
                index,
            )
            sunrise = get_item(daily.get("sunrise", []), index)
            sunset = get_item(daily.get("sunset", []), index)

            lines.append(
                f"{date}: {condition}; "
                f"minimum temperature {show_value(minimum, daily_units.get('temperature_2m_min', '°C'))}; "
                f"maximum temperature {show_value(maximum, daily_units.get('temperature_2m_max', '°C'))}; "
                f"maximum rain probability {show_value(rain_chance, daily_units.get('precipitation_probability_max', '%'))}; "
                f"total precipitation {show_value(precipitation, ' ' + daily_units.get('precipitation_sum', 'mm'))}; "
                f"sunrise {format_time(sunrise)}; sunset {format_time(sunset)}."
            )
    else:
        lines.append("Daily forecast data is unavailable.")

    lines.extend(
        [
            "",
            "These are forecasts, not guarantees. Weather conditions can change.",
        ]
    )

    return "\n".join(lines)


def is_weather_question(question):
    return bool(
        re.search(
            r"\b(weather|forecast|temperature|rain|raining|"
            r"humidity|humid|wind|sunny|cloudy|hot|cold|"
            r"precipitation|sunrise|sunset)\b",
            question,
            re.IGNORECASE,
        )
    )


async def answer_weather_question(
    question: str,
    weather_data: dict,
    route_data: dict | None = None,
    route_weather: dict | None = None,
    route_weather_error: str | None = None,
) -> str:

    # Travel questions use the calculated route and endpoint weather.
    if route_data:
        distance = route_data.get("distance_km")
        estimated_minutes = route_data.get("estimated_minutes")
        traffic_delay = route_data.get("traffic_delay_minutes")
        no_traffic_minutes = route_data.get("no_traffic_minutes")

        lines = [
            f"Driving route from {route_data.get('origin', 'origin')} "
            f"to {route_data.get('destination', 'destination')}.",
            "",
        ]

        if distance is not None:
            lines.append(f"Estimated distance: {distance} km.")

        if estimated_minutes is not None:
            lines.append(
                "Traffic-aware estimated journey time: about "
                f"{format_duration(estimated_minutes)}."
            )

        if traffic_delay is not None:
            lines.append(
                f"TomTom-reported traffic delay: {traffic_delay} minutes. "
                "This is a separate reported value; do not add it "
                "to the estimated journey time."
            )

        if no_traffic_minutes is not None:
            lines.append(
                "Separate no-traffic journey estimate: about "
                f"{format_duration(no_traffic_minutes)}."
            )

        if route_weather:
            lines.extend(
                [
                    "",
                    describe_location_weather(
                        route_weather.get("origin"),
                        "Departure",
                    ),
                    describe_location_weather(
                        route_weather.get("destination"),
                        "Destination",
                    ),
                ]
            )
        elif route_weather_error:
            lines.extend(["", route_weather_error])

        lines.extend(
            [
                "",
                "Journey times are estimates, not guaranteed arrival times. "
                "Check Google Maps for updated route and traffic information "
                "before leaving.",
            ]
        )

        return "\n".join(lines)

    # Weather questions are answered from the actual API data.
    # This prevents the AI from confusing Chirala with Bengaluru.
    if weather_data and is_weather_question(question):
        return build_forecast_report(weather_data)

    # Use local Ollama for general questions.
    context = {
        "location": weather_data.get("location", {}),
        "current_weather": weather_data.get("weather", {}).get("current", {}),
        "daily_forecast": weather_data.get("weather", {}).get("daily", {}),
    }

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are WeatherGPT, a helpful weather assistant. "
                    "Use only the supplied weather data for factual weather "
                    "claims. Do not invent temperatures, forecasts, rain "
                    "warnings, or locations. The location name in the data "
                    "identifies which place the weather belongs to. "
                    "If the data does not answer the question, say so clearly. "
                    "Keep answers clear and practical."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    "Available weather data:\n"
                    + json.dumps(context, ensure_ascii=False)
                ),
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()

        result = response.json()
        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty answer.")

        return answer

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Could not contact local Ollama. Make sure Ollama is running "
            "and the qwen2.5:3b model is installed."
        ) from exc