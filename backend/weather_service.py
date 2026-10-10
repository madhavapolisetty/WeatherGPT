
import asyncio

import httpx


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,"
    "apparent_temperature,is_day,precipitation,"
    "weather_code,wind_speed_10m"
)

HOURLY_FIELDS = (
    "temperature_2m,precipitation_probability,precipitation"
)

DAILY_FIELDS = (
    "weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_probability_max,precipitation_sum,"
    "sunrise,sunset"
)


async def _get_weather_at_coordinates(
    latitude: float,
    longitude: float,
    name: str,
    country: str | None = None,
) -> dict:
    """Fetch current weather and forecast for any coordinates."""

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": CURRENT_FIELDS,
                "hourly": HOURLY_FIELDS,
                "daily": DAILY_FIELDS,
                "timezone": "auto",
                "forecast_days": 7,
            },
        )

        response.raise_for_status()
        forecast = response.json()

    return {
        "location": {
            "name": name,
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
        },
        "weather": forecast,
        "source": "Open-Meteo",
    }


async def get_weather(city: str):
    """
    Fetch weather for a city name.
    Keeps the existing GET /api/weather endpoint compatible.
    """

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )

        response.raise_for_status()
        locations = response.json().get("results", [])

    if not locations:
        return None

    place = locations[0]

    return await _get_weather_at_coordinates(
        latitude=place["latitude"],
        longitude=place["longitude"],
        name=place["name"],
        country=place.get("country"),
    )


async def get_weather_by_coordinates(
    latitude: float,
    longitude: float,
    name: str,
    country: str | None = None,
) -> dict:
    """Fetch weather directly from known route coordinates."""

    return await _get_weather_at_coordinates(
        latitude=latitude,
        longitude=longitude,
        name=name,
        country=country,
    )


async def get_route_weather(route_info: dict) -> dict:
    """
    Fetch weather for both ends of a TomTom route.

    Expects route_info to contain:
    origin, destination,
    origin_latitude, origin_longitude,
    destination_latitude, destination_longitude.
    """

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
        latitude=route_info["origin_latitude"],
        longitude=route_info["origin_longitude"],
        name=route_info["origin"],
    )

    destination_task = get_weather_by_coordinates(
        latitude=route_info["destination_latitude"],
        longitude=route_info["destination_longitude"],
        name=route_info["destination"],
    )

    # Fetch both locations concurrently.
    origin_weather, destination_weather = await asyncio.gather(
        origin_task,
        destination_task,
    )

    return {
        "origin": origin_weather,
        "destination": destination_weather,
    }