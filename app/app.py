"""Mock drone telemetry API.

An in-memory FastAPI service used as a target for API test automation.
Optional API-key auth and per-client rate limiting are switched on by
environment variables so the default behaviour stays open and simple.
"""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Mock Drone Telemetry API", version="1.1.0")

# --- In-memory state --------------------------------------------------------

_flights: dict[str, list[dict]] = {}
_request_log: dict[str, deque[float]] = defaultdict(deque)

RATE_WINDOW_SECONDS = 60.0
_clock = time.monotonic  # indirection so tests can control time


def reset_state() -> None:
    """Clear all stored flights and rate-limit counters."""
    _flights.clear()
    _request_log.clear()


# --- Models -----------------------------------------------------------------


class Telemetry(BaseModel):
    # Reject "Infinity"/"NaN": lax float parsing would otherwise accept alt=inf.
    model_config = ConfigDict(allow_inf_nan=False)

    lat: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    alt: float = Field(..., ge=0, description="Altitude in metres above ground")
    speed: float = Field(..., ge=0, description="Ground speed in m/s")
    heading: float = Field(
        ..., ge=0, lt=360, description="Heading in degrees, 0 (north) up to but not including 360"
    )


class FlightResponse(BaseModel):
    flight_id: str
    data: list[Telemetry]


class CreateFlightResponse(BaseModel):
    flight_id: str
    status: Literal["ok"] = "ok"


class AppendResponse(BaseModel):
    flight_id: str
    status: Literal["appended"] = "appended"


class ResetResponse(BaseModel):
    status: Literal["reset"] = "reset"


# --- Optional auth and rate limiting ------------------------------------------


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def require_api_key(x_api_key: str | None = Header(default=None)) -> str | None:
    """Enforce X-API-Key when REQUIRE_API_KEY is set; otherwise a no-op."""
    if not _env_flag("REQUIRE_API_KEY"):
        return None
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfigured: REQUIRE_API_KEY is set but API_KEY is not",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


def rate_limit(
    request: Request, response: Response, api_key: str | None = Depends(require_api_key)
) -> None:
    """Sliding-window limit of RATE_LIMIT_PER_MINUTE requests per client (0 or unset = off)."""
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "0") or 0)
    if limit <= 0:
        return
    client = api_key or (request.client.host if request.client else "unknown")
    now = _clock()
    window = _request_log[client]
    while window and now - window[0] >= RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        retry_after = max(1, int(RATE_WINDOW_SECONDS - (now - window[0])) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(limit - len(window))


guarded = [Depends(rate_limit)]

# --- Endpoints --------------------------------------------------------------


@app.post(
    "/telemetry",
    response_model=CreateFlightResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=guarded,
)
async def post_telemetry(data: Telemetry) -> CreateFlightResponse:
    flight_id = str(uuid.uuid4())
    _flights[flight_id] = [data.model_dump()]
    return CreateFlightResponse(flight_id=flight_id)


@app.get(
    "/flight/{flight_id}",
    response_model=FlightResponse,
    responses={404: {"description": "Flight ID not found"}},
    dependencies=guarded,
)
async def get_flight_data(flight_id: str) -> FlightResponse:
    if flight_id not in _flights:
        raise HTTPException(status_code=404, detail="Flight ID not found")
    return FlightResponse(flight_id=flight_id, data=_flights[flight_id])


@app.post(
    "/telemetry/{flight_id}",
    response_model=AppendResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Flight ID not found"}},
    dependencies=guarded,
)
async def append_telemetry(flight_id: str, data: Telemetry) -> AppendResponse:
    if flight_id not in _flights:
        raise HTTPException(status_code=404, detail="Flight ID not found")
    _flights[flight_id].append(data.model_dump())
    return AppendResponse(flight_id=flight_id)


@app.delete("/reset", response_model=ResetResponse, dependencies=guarded)
async def reset() -> ResetResponse:
    _flights.clear()
    return ResetResponse()
