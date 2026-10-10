
import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv


# Load backend/.env during local development.
# Render uses its configured environment variables.
load_dotenv(Path(__file__).with_name(".env"))

VISUAL_CROSSING_URL = (
    "https://weather.visualcrossing.com/"
    "VisualCrossingWebServices/rest/services/timeline"
)

VISUAL_CROSSING_API_KEY = os.getenv(
    "VISUAL_CROSSING_API_KEY", ""
).strip()

REQUEST_TIMEOUT = 20.0
CACHE_SECONDS = 600

# Cache successful weather responses for 10 minutes.
_weather_cache = {}


def convert_weather_code(icon=None, conditions=None):
    """Convert provider descriptions to codes used by the frontend."""

    text = f"{icon or ''} {conditions or ''}".lower()

    if "thunder" in text:
        return 95
    if "snow" in text:
        return 71
    if "sleet" in text or "freezing" in text:
        return 66
    if "drizzle" in text:
        return 51
    if "shower" in text:
        return 80
    if "rain" in text:
        return 61
    if "fog" in text:
        return 45
    if "overcast" in text:
        return 3
    if "partially cloudy" in text or "partly-cloudy" in text:
        return 2
    if "cloudy" in text:
        return 3
    if "clear" in text or "sun" in text:
        return 0

    return None


def get_local_datetime(
    epoch,
    timezone_name,
    fallback_date=None,
    fallback_time=None,
):
    """Convert an epoch timestamp to local ISO-format time."""

    if epoch is not None and timezone_name:
        try:
            return datetime.fromtimestamp(
                float(epoch),
                ZoneInfo(timezone_name),
            ).replace(tzinfo=None).isoformat(timespec="seconds")
        except (
            ValueError,
            TypeError,
            OSError,
            ZoneInfoNotFoundError,
        ):
            pass

    if fallback_date and fallback_time:
        return f"{fallback_date}T{fallback_time}"

    return fallback_date or fallback_time or ""


def normalize_weather_response(
    raw,
    requested_location,
    preferred_name=None,
):
    """Adapt Visual Crossing data to WeatherGPT's existing data format."""

    resolved_address = (
        raw.get("resolvedAddress")
        or raw.get("address")
        or requested_location
    )

    timezone_name = raw.get("timezone", "UTC")
    days = raw.get("days") or []
    current = raw.get("currentConditions") or {}

    location_name = preferred_name or resolved_address

    current_time = get_local_datetime(
        current.get("datetimeEpoch"),
        timezone_name,
        days[0].get("datetime") if days else "",
        current.get("datetime"),
    )

    # Current conditions
    normalized_current = {
        "time": current_time,
        "temperature_2m": current.get("temp"),
        "relative_humidity_2m": current.get("humidity"),
        "apparent_temperature": current.get("feelslike"),
        "is_day": (
            1 if str(current.get("icon", "")).endswith("-day")
            else 0 if str(current.get("icon", "")).endswith("-night")
            else None
        ),
        "precipitation": current.get("precip"),
        "weather_code": convert_weather_code(
            current.get("icon"),
            current.get("conditions"),
        ),
        "wind_speed_10m": current.get("windspeed"),
    }

    # Hourly forecast
    hourly = {
        "time": [],
        "temperature_2m": [],
        "precipitation_probability": [],
        "precipitation": [],
        "weather_code": [],
    }

    for day in days:
        day_date = day.get("datetime", "")

        for hour in day.get("hours") or []:
            hour_time = str(hour.get("datetime", ""))

            if not day_date or not hour_time:
                continue

            full_time = (
                hour_time
                if "T" in hour_time
                else f"{day_date}T{hour_time[:5]}"
            )

            hourly["time"].append(full_time)
            hourly["temperature_2m"].append(hour.get("temp"))
            hourly["precipitation_probability"].append(
                hour.get("precipprob")
            )
            hourly["precipitation"].append(hour.get("precip"))
            hourly["weather_code"].append(
                convert_weather_code(
                    hour.get("icon"),
                    hour.get("conditions"),
                )
            )

    # Seven-day forecast
    daily = {
        "time": [],
        "weather_code": [],
        "temperature_2m_max": [],
        "temperature_2m_min": [],
        "precipitation_probability_max": [],
        "precipitation_sum": [],
        "sunrise": [],
        "sunset": [],
    }

    for day in days[:7]:
        daily["time"].append(day.get("datetime"))
        daily["weather_code"].append(
            convert_weather_code(
                day.get("icon"),
                day.get("conditions"),
            )
        )
        daily["temperature_2m_max"].append(day.get("tempmax"))
        daily["temperature_2m_min"].append(day.get("tempmin"))
        daily["precipitation_probability_max"].append(
            day.get("precipprob")
        )
        daily["precipitation_sum"].append(day.get("precip"))
        daily["sunrise"].append(day.get("sunrise"))
        daily["sunset"].append(day.get("sunset"))

    return {
        "location": {
            "name": location_name,
            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),
        },
        "weather": {
            "current_units": {
                "temperature_2m": "°C",
                "relative_humidity_2m": "%",
                "apparent_temperature": "°C",
                "precipitation": "mm",
                "wind_speed_10m": "km/h",
            },
            "current": normalized_current,
            "hourly_units": {
                "temperature_2m": "°C",
                "precipitation_probability": "%",
                "precipitation": "mm",
            },
            "hourly": hourly,
            "daily_units": {
                "temperature_2m_max": "°C",
                "temperature_2m_min": "°C",
                "precipitation_probability_max": "%",
                "precipitation_sum": "mm",
            },
            "daily": daily,
        },
        "source": "Visual Crossing",
    }


async def _fetch_weather(
    location_query,
    preferred_name=None,
):
    """Fetch and normalize weather data from Visual Crossing."""

    if not VISUAL_CROSSING_API_KEY:
        raise RuntimeError(
            "VISUAL_CROSSING_API_KEY is missing. Configure it in "
            "backend/.env for local development and Render's "
            "Environment settings for the deployed service."
        )

    location_query = str(location_query).strip()

    if not location_query:
        return None

    cache_key = location_query.lower()
    cached = _weather_cache.get(cache_key)

    if cached and time.monotonic() - cached["time"] < CACHE_SECONDS:
        return cached["data"]

    url = (
        f"{VISUAL_CROSSING_URL}/"
        f"{quote(location_query, safe=',')}"
    )

    params = {
        "key": VISUAL_CROSSING_API_KEY,
        "unitGroup": "metric",
        "include": "current,hours,days",
        "contentType": "json",
        "lang": "en",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url, params=params)

        if response.is_error:
            # Never log the request URL because it contains the API key.
            print(
                "Visual Crossing HTTP status:",
                response.status_code,
            )
            print(
                "Visual Crossing response:",
                response.text[:500],
            )

        response.raise_for_status()
        raw = response.json()

    result = normalize_weather_response(
        raw,
        requested_location=location_query,
        preferred_name=preferred_name,
    )

    _weather_cache[cache_key] = {
        "time": time.monotonic(),
        "data": result,
    }

    return result


async def get_weather(city: str):
    """Fetch weather for any city supported by Visual Crossing."""

    city = city.strip()

    if not city:
        return None

    return await _fetch_weather(
        city,
        preferred_name=city,
    )


async def get_weather_by_coordinates(
    latitude: float,
    longitude: float,
    name: str = "Selected location",
    country: str | None = None,
):
    """Fetch weather at coordinates for a route endpoint."""

    return await _fetch_weather(
        f"{latitude},{longitude}",
        preferred_name=name,
    )


async def _get_weather_at_coordinates(
    latitude: float,
    longitude: float,
    name: str,
    country: str | None = None,
):
    """Compatibility wrapper for existing imports."""

    return await get_weather_by_coordinates(
        latitude=latitude,
        longitude=longitude,
        name=name,
        country=country,
    )


async def get_route_weather(route_info: dict):
    """Fetch weather for both ends of a calculated route."""

    required_fields = (
        "origin",
        "destination",
        "origin_latitude",
        "origin_longitude",
        "destination_latitude",
        "destination_longitude",
    )

    if any(route_info.get(field) is None for field in required_fields):
        raise ValueError(
            "Route information is missing origin or destination coordinates."
        )

    origin_task = get_weather_by_coordinates(
        route_info["origin_latitude"],
        route_info["origin_longitude"],
        name=route_info["origin"],
    )

    destination_task = get_weather_by_coordinates(
        route_info["destination_latitude"],
        route_info["destination_longitude"],
        name=route_info["destination"],
    )

    origin_weather, destination_weather = await asyncio.gather(
        origin_task,
        destination_task,
    )

    return {
        "origin": origin_weather,
        "destination": destination_weather,
    }