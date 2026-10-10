
import asyncio
import httpx

from traffic_service import get_route_traffic, TOMTOM_API_KEY


async def main():
    print("TomTom API key loaded:", bool(TOMTOM_API_KEY))

    try:
        result = await get_route_traffic(
            origin="RVITM",
            destination="Hebbal",
            city="Bengaluru",
        )

        print("\nSUCCESS: Route information received")
        print(result)

    except httpx.HTTPStatusError as exc:
        print("\nTomTom HTTP status:", exc.response.status_code)
        print("TomTom response body:", exc.response.text)

    except httpx.RequestError as exc:
        print("\nNetwork error:", type(exc).__name__)

    except Exception as exc:
        print("\nError type:", type(exc).__name__)
        print("Error details:", str(exc))


asyncio.run(main())
