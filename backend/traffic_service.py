
import math
import os
import re
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

SEARCH_URL = "https://api.tomtom.com/search/2/search"
ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute"


def normalize_place(place: str) -> str:
    """Normalize text for matching location aliases."""
    return re.sub(r"[^a-z0-9]", "", place.lower())


# Optional aliases for abbreviations.
# Other place names are searched normally.
PLACE_ALIASES = {
    "rvitm": [
        "R.V. Institute of Technology and Management, Bengaluru, Karnataka, India",
        "RV Institute of Technology and Management, Bengaluru, Karnataka, India",
        "RVITM",
    ],
}


async def find_place(
    client: httpx.AsyncClient,
    place: str,
    city: str | None = None,
) -> dict:
    """
    Find any supported place using TomTom Search.

    Searches globally first, without forcing the location to Bengaluru
    or India. The city is only used as a fallback for ambiguous names.
    """

    place = place.strip()

    if not place:
        raise RuntimeError("A starting point or destination is missing.")

    normalized = normalize_place(place)
    search_names = PLACE_ALIASES.get(normalized, [place])

    # Try the supplied location or its aliases first.
    for search_name in search_names:
        encoded_query = quote(search_name, safe="")

        params = {
            "key": TOMTOM_API_KEY,
            "limit": 5,
            "language": "en-GB",
        }

        response = await client.get(
            f"{SEARCH_URL}/{encoded_query}.json",
            params=params,
        )
        response.raise_for_status()

        results = response.json().get("results", [])

        if results:
            result = results[0]
            position = result.get("position", {})
            address = result.get("address", {})
            poi = result.get("poi", {})

            latitude = position.get("lat")
            longitude = position.get("lon")

            if latitude is None or longitude is None:
                continue

            return {
                "latitude": latitude,
                "longitude": longitude,
                "label": (
                    poi.get("name")
                    or address.get("freeformAddress")
                    or search_name
                ),
            }

    # Only try the dashboard city as a fallback when the place
    # was ambiguous or could not be found by its supplied name.
    if city and normalize_place(city) not in normalized:
        fallback_query = f"{place}, {city}"
        encoded_query = quote(fallback_query, safe="")

        response = await client.get(
            f"{SEARCH_URL}/{encoded_query}.json",
            params={
                "key": TOMTOM_API_KEY,
                "limit": 5,
                "language": "en-GB",
            },
        )
        response.raise_for_status()

        results = response.json().get("results", [])

        if results:
            result = results[0]
            position = result.get("position", {})
            address = result.get("address", {})
            poi = result.get("poi", {})

            latitude = position.get("lat")
            longitude = position.get("lon")

            if latitude is not None and longitude is not None:
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "label": (
                        poi.get("name")
                        or address.get("freeformAddress")
                        or fallback_query
                    ),
                }

    raise RuntimeError(
        f"Could not identify '{place}'. "
        "Try including its city, state, or country."
    )


async def get_route_traffic(
    origin: str,
    destination: str,
    city: str | None = None,
) -> dict:
    """Calculate a driving route between any two supported locations."""

    if not TOMTOM_API_KEY:
        raise RuntimeError(
            "TOMTOM_API_KEY is missing from backend/.env."
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        start = await find_place(client, origin, city)
        end = await find_place(client, destination, city)

        locations = (
            f"{start['latitude']},{start['longitude']}:"
            f"{end['latitude']},{end['longitude']}"
        )

        response = await client.get(
            f"{ROUTING_URL}/{locations}/json",
            params={
                "key": TOMTOM_API_KEY,
                "traffic": "true",
                "routeType": "fastest",
                "travelMode": "car",
                "departAt": "now",
                "computeTravelTimeFor": "all",
            },
        )
        response.raise_for_status()

        routes = response.json().get("routes", [])

        if not routes:
            raise RuntimeError(
                f"No driving route was returned from "
                f"'{origin}' to '{destination}'."
            )

        summary = routes[0].get("summary", {})

        distance_meters = summary.get("lengthInMeters")
        travel_seconds = summary.get("travelTimeInSeconds")
        delay_seconds = summary.get("trafficDelayInSeconds")
        no_traffic_seconds = summary.get(
            "noTrafficTravelTimeInSeconds"
        )
        historic_seconds = summary.get(
            "historicTrafficTravelTimeInSeconds"
        )
        live_incidents_seconds = summary.get(
            "liveTrafficIncidentsTravelTimeInSeconds"
        )

        if distance_meters is None or travel_seconds is None:
            raise RuntimeError(
                "TomTom returned incomplete route information."
            )

        difference_seconds = None
        if no_traffic_seconds is not None:
            difference_seconds = max(
                0,
                travel_seconds - no_traffic_seconds,
            )

        return {
            "origin": start["label"],
            "destination": end["label"],
            "origin_latitude": start["latitude"],
            "origin_longitude": start["longitude"],
            "destination_latitude": end["latitude"],
            "destination_longitude": end["longitude"],
            "distance_km": round(distance_meters / 1000, 1),
            "estimated_minutes": math.ceil(travel_seconds / 60),
            "traffic_delay_minutes": (
                round(max(0, delay_seconds) / 60, 1)
                if delay_seconds is not None
                else None
            ),
            "estimate_difference_vs_no_traffic_minutes": (
                round(difference_seconds / 60, 1)
                if difference_seconds is not None
                else None
            ),
            "no_traffic_minutes": (
                math.ceil(no_traffic_seconds / 60)
                if no_traffic_seconds is not None
                else None
            ),
            "historic_traffic_minutes": (
                math.ceil(historic_seconds / 60)
                if historic_seconds is not None
                else None
            ),
            "live_traffic_incidents_minutes": (
                math.ceil(live_incidents_seconds / 60)
                if live_incidents_seconds is not None
                else None
            ),
        }