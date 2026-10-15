from __future__ import annotations
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

# PROMETHEUS LOCATION http://prometheus:9090
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL","http://prometheus:9090")

# The LLM cannot provide arbitrary PromQL. Only approved functions in server.py use it.
async def query_prometheus(query: str):

    url = (
        f"{PROMETHEUS_URL}"
        "/api/v1/query"
    )


    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            url,
            params={"query":query}
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(
                "Prometheus query failed: "
                f"{payload}"
            )

        return payload["data"]["result"]
        
async def get_prometheus_alerts() -> list[dict]:
    """
    Fetch the current Prometheus alert states from /api/v1/alerts.

    Returns alerts in states such as:
    - pending
    - firing
    """

    url = f"{PROMETHEUS_URL}/api/v1/alerts"

    async with httpx.AsyncClient(timeout=20.0) as client:

        response = await client.get(url)

        response.raise_for_status()

        payload = response.json()


    if payload.get("status") != "success":
        raise RuntimeError(
            f"Prometheus returned unsuccessful response: {payload}"
        )


    data = payload.get("data", {})

    alerts = data.get("alerts", [])

    return alerts