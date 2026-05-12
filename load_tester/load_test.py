import asyncio
import csv
import os
import time
from pathlib import Path

import aiohttp

BASE_URL = os.getenv("TARGET_BASE_URL", "http://localhost:3000")
CONCURRENCY_LEVELS = [10, 50, 100, 200, 500]
ENDPOINTS = [item.strip() for item in os.getenv("TEST_ENDPOINTS", "/non-blocking,/blocking").split(",") if item.strip()]
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
DELAY_MS = int(os.getenv("SIMULATION_DELAY_MS", "100"))
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "2"))
RESULTS_PATH = Path(__file__).resolve().parent.parent / "results" / "test_results.csv"


async def wait_for_server(base_url: str, retries: int = 20, delay_seconds: float = 1.0) -> None:
    health_url = f"{base_url}/health"
    timeout = aiohttp.ClientTimeout(total=5)

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        return
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass

        print(f"Waiting for server... attempt {attempt}/{retries}")
        await asyncio.sleep(delay_seconds)

    raise RuntimeError(f"Server did not become ready at {health_url}")


async def fetch_once(session: aiohttp.ClientSession, url: str) -> dict:
    start_time = time.perf_counter()

    try:
        async with session.get(url) as response:
            await response.read()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return {
                "success": response.status == 200,
                "status_code": response.status,
                "response_time_ms": elapsed_ms,
            }
    except Exception as error:
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return {
            "success": False,
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error": str(error),
        }


def build_timeout_seconds(endpoint: str, concurrency_level: int) -> float:
    if endpoint == "/blocking":
        estimated_seconds = (DELAY_MS * concurrency_level) / 1000
        return max(REQUEST_TIMEOUT_SECONDS, estimated_seconds + 10)

    return max(REQUEST_TIMEOUT_SECONDS, (DELAY_MS / 1000) + 5)


async def warm_up_endpoint(base_url: str, endpoint: str) -> None:
    url = f"{base_url}{endpoint}?delayMs={DELAY_MS}"
    timeout = aiohttp.ClientTimeout(total=max(5, build_timeout_seconds(endpoint, 1)))

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            await response.read()


async def run_single_test(base_url: str, endpoint: str, concurrency_level: int) -> dict:
    url = f"{base_url}{endpoint}?delayMs={DELAY_MS}"
    timeout = aiohttp.ClientTimeout(total=build_timeout_seconds(endpoint, concurrency_level))

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [fetch_once(session, url) for _ in range(concurrency_level)]

        started_at = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        total_duration_seconds = time.perf_counter() - started_at

    total_requests = len(responses)
    successful_requests = sum(1 for item in responses if item["success"])
    failed_requests = total_requests - successful_requests
    response_times = [item["response_time_ms"] for item in responses]

    average_response_time = sum(response_times) / total_requests if total_requests else 0.0
    minimum_response_time = min(response_times) if response_times else 0.0
    maximum_response_time = max(response_times) if response_times else 0.0
    throughput = total_requests / total_duration_seconds if total_duration_seconds > 0 else 0.0
    error_rate = (failed_requests / total_requests) * 100 if total_requests else 0.0

    return {
        "endpoint": endpoint,
        "concurrency_level": concurrency_level,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "average_response_time_ms": round(average_response_time, 2),
        "minimum_response_time_ms": round(minimum_response_time, 2),
        "maximum_response_time_ms": round(maximum_response_time, 2),
        "throughput_rps": round(throughput, 2),
        "error_rate_percent": round(error_rate, 2),
    }


def write_results(rows: list[dict]) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "endpoint",
        "concurrency_level",
        "total_requests",
        "successful_requests",
        "failed_requests",
        "average_response_time_ms",
        "minimum_response_time_ms",
        "maximum_response_time_ms",
        "throughput_rps",
        "error_rate_percent",
    ]

    for attempt in range(3):
        try:
            with RESULTS_PATH.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            return
        except PermissionError:
            if attempt == 2:
                raise

            time.sleep(0.2)


def print_result(row: dict) -> None:
    print(
        f"{row['endpoint']:>14} | "
        f"users={row['concurrency_level']:>3} | "
        f"avg={row['average_response_time_ms']:>8} ms | "
        f"min={row['minimum_response_time_ms']:>8} ms | "
        f"max={row['maximum_response_time_ms']:>8} ms | "
        f"throughput={row['throughput_rps']:>8} req/s | "
        f"errors={row['error_rate_percent']:>6}%"
    )


async def main() -> None:
    await wait_for_server(BASE_URL)

    all_results = []

    for endpoint in ENDPOINTS:
        print(f"\nTesting {endpoint} endpoint")
        await warm_up_endpoint(BASE_URL, endpoint)
        await asyncio.sleep(COOLDOWN_SECONDS)

        for concurrency_level in CONCURRENCY_LEVELS:
            result = await run_single_test(BASE_URL, endpoint, concurrency_level)
            all_results.append(result)
            print_result(result)
            await asyncio.sleep(COOLDOWN_SECONDS)

    write_results(all_results)
    print(f"\nResults saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
