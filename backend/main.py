import re
from urllib.parse import quote_plus

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from weather_service import get_weather, get_route_weather
from ai_service import answer_weather_question
from traffic_service import get_route_traffic


app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather and travel assistant",
    version="1.0.0",
)


# Allow local development and the deployed Vercel website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://weathergpt-29c5d9rku-madhavapolisetty.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to WeatherGPT",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# Error logging helpers
# --------------------------------------------------

def log_weather_http_error(
    exc: httpx.HTTPStatusError,
    context: str = "Weather provider",
):
    """Log the upstream HTTP status and response for diagnosis."""
    print(f"{context} HTTP status:", exc.response.status_code)
    print(f"{context} URL:", exc.request.url)
    print(f"{context} response:", exc.response.text[:500])


def log_weather_request_error(
    exc: httpx.RequestError,
    context: str = "Weather provider",
):
    """Log network and timeout errors."""
    print(f"{context} connection error:", repr(exc))

    if exc.request is not None:
        print(f"{context} URL:", exc.request.url)


# --------------------------------------------------
# Current weather endpoint
# --------------------------------------------------

@app.get("/api/weather")
async def weather(
    city: str = Query(min_length=2, max_length=100),
):
    try:
        result = await get_weather(city)

    except httpx.HTTPStatusError as exc:
        log_weather_http_error(exc, "Weather API")

        raise HTTPException(
            status_code=502,
            detail="Weather provider is temporarily unavailable",
        ) from exc

    except httpx.RequestError as exc:
        log_weather_request_error(exc, "Weather API")

        raise HTTPException(
            status_code=502,
            detail="Unable to connect to the weather provider",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city}",
        )

    return result


# --------------------------------------------------
# Chat request model
# --------------------------------------------------

class ChatRequest(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    question: str = Field(min_length=3, max_length=1000)


# --------------------------------------------------
# Extract route locations
# --------------------------------------------------

def extract_route_locations(question: str):
    """Extract origin and destination from common route questions."""

    cleaned = question.strip().rstrip("?.! ")

    patterns = [
        r"\bfrom\s+(.+?)\s+\bto\s+(.+)$",
        r"\bbetween\s+(.+?)\s+\band\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)

        if not match:
            continue

        origin = match.group(1).strip(" ,.!?")
        destination = match.group(2).strip(" ,.!?")

        destination = re.sub(
            r"\s+(right\s+now|at\s+the\s+moment|now|today|"
            r"tomorrow|tonight|this morning|this afternoon|"
            r"this evening)$",
            "",
            destination,
            flags=re.IGNORECASE,
        ).strip(" ,.!?")

        if origin and destination:
            return origin, destination

    return None


# --------------------------------------------------
# Extract city from weather questions
# --------------------------------------------------

def extract_weather_city(question: str) -> str | None:
    """
    Detect common weather questions, for example:
    - How is the weather in Chirala?
    - Give me the forecast for Hyderabad tomorrow.
    - Will it rain in Chennai?
    - What is the temperature in New York?
    - Chirala weather forecast.
    """

    weather_words = (
        r"\b(weather|forecast|temperature|conditions?|rain|raining|"
        r"precipitation|humidity|humid|wind|sunny|cloudy|hot|cold|"
        r"sunrise|sunset)\b"
    )

    if not re.search(weather_words, question, re.IGNORECASE):
        return None

    cleaned = question.strip()

    # Remove forecast periods and common time phrases.
    cleaned = re.sub(
        r"\b(?:for\s+)?(?:the\s+)?next\s+\d+\s+days?\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\b(?:right now|at the moment|currently|today|tomorrow|"
        r"tonight|this morning|this afternoon|this evening|"
        r"this week|next week|this weekend|next weekend|please)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    patterns = [
        # "weather in Chirala", "forecast for Hyderabad"
        r"\b(?:weather|forecast|temperature|conditions?)\s+"
        r"(?:in|for|at|of)\s+"
        r"([\w][\w .'-]*?)"
        r"(?=\s+(?:like|and|versus|vs|with|during)\b|[?.!,;]|$)",

        # "Will it rain in Chennai?"
        # "What is the temperature in New York?"
        r"\b(?:in|at|for|of)\s+"
        r"([\w][\w .'-]*?)"
        r"(?=\s+(?:like|and|versus|vs|with|during)\b|[?.!,;]|$)",

        # "Chirala weather", "Hyderabad forecast"
        r"^\s*(?:what(?:'s| is)?\s+)?"
        r"([\w][\w .'-]*?)\s+"
        r"(?:weather|forecast|temperature|conditions?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)

        if not match:
            continue

        city = match.group(1).strip(" \t,.;:!?")

        if not city or city.lower() in {
            "the",
            "next",
            "this",
            "today",
            "tomorrow",
            "weather",
            "forecast",
        }:
            continue

        return city

    return None


# --------------------------------------------------
# Google Maps URL helpers
# --------------------------------------------------

def create_google_maps_route_url(
    origin: str,
    destination: str,
):
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}"
        f"&destination={quote_plus(destination)}"
        "&travelmode=driving"
    )


def create_google_maps_url_from_coordinates(route_info: dict):
    origin_lat = route_info.get("origin_latitude")
    origin_lon = route_info.get("origin_longitude")
    destination_lat = route_info.get("destination_latitude")
    destination_lon = route_info.get("destination_longitude")

    if all(
        value is not None
        for value in (
            origin_lat,
            origin_lon,
            destination_lat,
            destination_lon,
        )
    ):
        return create_google_maps_route_url(
            f"{origin_lat},{origin_lon}",
            f"{destination_lat},{destination_lon}",
        )

    return create_google_maps_route_url(
        route_info["origin"],
        route_info["destination"],
    )


# --------------------------------------------------
# WeatherGPT chat endpoint
# --------------------------------------------------

@app.post("/api/chat")
async def weather_chat(request: ChatRequest):

    # Detect route questions first.
    route_locations = extract_route_locations(request.question)

    # Use the dashboard city by default.
    weather_city = request.city

    # Select a city mentioned in ordinary weather questions.
    if not route_locations:
        mentioned_city = extract_weather_city(request.question)

        if mentioned_city:
            weather_city = mentioned_city

    # Fetch weather for the selected or detected city.
    try:
        weather_data = await get_weather(weather_city)

    except httpx.HTTPStatusError as exc:
        log_weather_http_error(exc, "Chat weather provider")

        raise HTTPException(
            status_code=502,
            detail="Weather provider is temporarily unavailable",
        ) from exc

    except httpx.RequestError as exc:
        log_weather_request_error(exc, "Chat weather provider")

        raise HTTPException(
            status_code=502,
            detail="Unable to connect to the weather provider",
        ) from exc

    if weather_data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Weather data could not be found for {weather_city}. "
                "Try adding the state or country to the place name."
            ),
        )

    # Initialise route information.
    route_info = None
    route_weather = None
    route_url = None
    route_error = None
    route_weather_error = None

    # Calculate the route when requested.
    if route_locations:
        origin, destination = route_locations

        # Keep a Google Maps link even if routing fails.
        route_url = create_google_maps_route_url(
            origin,
            destination,
        )

        try:
            route_info = await get_route_traffic(
                origin=origin,
                destination=destination,
                city=request.city,
            )

            route_url = create_google_maps_url_from_coordinates(
                route_info
            )

        except httpx.HTTPStatusError as exc:
            print("TomTom HTTP status:", exc.response.status_code)
            print("TomTom response:", exc.response.text[:500])

            route_error = (
                "TomTom could not provide a route estimate. "
                "You can still open Google Maps for directions."
            )

        except httpx.RequestError as exc:
            print("TomTom connection error:", repr(exc))

            route_error = (
                "Unable to contact the routing service right now."
            )

        except (RuntimeError, ValueError, KeyError) as exc:
            print("TomTom routing error:", str(exc))

            route_error = (
                "A route estimate is unavailable. "
                "Check the place names or use Google Maps."
            )

        # Fetch weather at both endpoints if routing succeeded.
        if route_info is not None:
            try:
                route_weather = await get_route_weather(route_info)

            except httpx.HTTPStatusError as exc:
                log_weather_http_error(exc, "Route weather provider")

                route_weather_error = (
                    "Weather at one or both route endpoints "
                    "could not be retrieved."
                )

            except httpx.RequestError as exc:
                log_weather_request_error(
                    exc,
                    "Route weather provider",
                )

                route_weather_error = (
                    "Weather at one or both route endpoints "
                    "could not be retrieved."
                )

            except (RuntimeError, ValueError, KeyError) as exc:
                print("Route weather error:", str(exc))

                route_weather_error = (
                    "Weather at both route endpoints is unavailable."
                )

    # Generate the answer using actual weather and route data.
    try:
        answer = await answer_weather_question(
            question=request.question,
            weather_data=weather_data,
            route_data=route_info,
            route_weather=route_weather,
            route_weather_error=route_weather_error,
        )

    except RuntimeError as exc:
        print("WeatherGPT AI error:", str(exc))

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return {
        "city": request.city,
        "weather_city": weather_city,
        "question": request.question,
        "answer": answer,
        "weather_data": weather_data,
        "route_url": route_url,
        "route_info": route_info,
        "route_weather": route_weather,
        "route_error": route_error,
        "route_weather_error": route_weather_error,
    }