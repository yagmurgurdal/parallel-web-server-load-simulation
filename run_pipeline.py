import argparse
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


# Yerel ve Docker çalıştırmaları için ortak varsayılanlar.
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
DEFAULT_LOAD_LEVELS = os.getenv("LOAD_LEVELS", "10,100,500")
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
DEFAULT_CONNECTION_LIMIT = int(os.getenv("CONNECTION_LIMIT", "0"))
DEFAULT_RESULTS_FILE = os.getenv("RESULTS_FILE", "test_results.csv")
DEFAULT_STARTUP_TIMEOUT_SECONDS = float(os.getenv("STARTUP_TIMEOUT_SECONDS", "30"))
DEFAULT_SERVER_COMMAND = os.getenv("SERVER_COMMAND", "node index.js")
DEFAULT_ENDPOINTS = os.getenv("ENDPOINTS", "blocking,non-blocking")


def parse_arguments():
    # Pipeline'ın nasıl çalışacağını kullanıcıdan alır.
    parser = argparse.ArgumentParser(
        description="Run the complete local benchmark pipeline for both demo endpoints."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--users", default=DEFAULT_LOAD_LEVELS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--connection-limit",
        type=int,
        default=DEFAULT_CONNECTION_LIMIT,
        help="Maximum concurrent TCP connections for the load tester. Use 0 for no limit.",
    )
    parser.add_argument("--results-file", default=DEFAULT_RESULTS_FILE)
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=DEFAULT_STARTUP_TIMEOUT_SECONDS,
        help="Maximum time to wait for the health endpoint to become ready.",
    )
    parser.add_argument(
        "--server-command",
        default=DEFAULT_SERVER_COMMAND,
        help='Command used to start the Node.js server when the pipeline manages it.',
    )
    parser.add_argument(
        "--endpoints",
        default=DEFAULT_ENDPOINTS,
        help='Comma-separated endpoint names such as "blocking,non-blocking".',
    )
    parser.add_argument(
        "--skip-server-start",
        action="store_true",
        help="Do not start the server process. Use this when the target server is already running.",
    )
    parser.add_argument(
        "--overwrite-results",
        action="store_true",
        help="Delete the results CSV before starting the benchmark pipeline.",
    )
    return parser.parse_args()


def parse_endpoints(raw_value):
    # Yalnızca desteklenen endpoint isimlerinin kullanılmasına izin verir.
    valid_endpoints = {"blocking", "non-blocking"}
    endpoints = []

    for value in raw_value.split(","):
        endpoint = value.strip().strip("/")
        if not endpoint:
            continue
        if endpoint not in valid_endpoints:
            raise ValueError(
                f'Unsupported endpoint "{endpoint}". Use blocking and/or non-blocking.'
            )
        endpoints.append(endpoint)

    if not endpoints:
        raise ValueError("At least one endpoint must be provided.")

    return endpoints


def wait_for_health(health_url, timeout_seconds):
    # Sunucu hazır olmadan yük testine başlamak hatalı sonuç üretebilir.
    # Bu yüzden /health endpoint'ini belirli süre boyunca yokluyoruz.
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except URLError:
            pass
        time.sleep(0.5)

    raise TimeoutError(
        f"Server did not become healthy within {timeout_seconds} seconds: {health_url}"
    )


def start_server(command):
    # Sunucuyu bu script içinden ayrı bir process olarak başlatır.
    command_parts = shlex.split(command, posix=os.name != "nt")
    return subprocess.Popen(command_parts, cwd=PROJECT_ROOT)


def run_benchmark(endpoint, args, overwrite_results):
    # Aynı load tester scriptini farklı endpoint için çağırıyoruz.
    target_url = f"{args.base_url.rstrip('/')}/{endpoint}"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "load_tester.py"),
        "--url",
        target_url,
        "--users",
        args.users,
        "--timeout",
        str(args.timeout),
        "--connection-limit",
        str(args.connection_limit),
        "--results-file",
        args.results_file,
    ]

    if overwrite_results:
        command.append("--overwrite-results")

    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def stop_server(process):
    # Pipeline sonunda arka planda açık kalan sunucu prosesini kapatır.
    if process is None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    # Ana akış: sunucuyu başlat, health check bekle, benchmark koş, sonra kapat.
    args = parse_arguments()
    endpoints = parse_endpoints(args.endpoints)
    server_process = None

    if args.connection_limit < 0:
        raise ValueError("Connection limit must be 0 or a positive integer.")

    # Kullanıcı isterse önce eski sonuç dosyası kaldırılır.
    if args.overwrite_results:
        results_path = PROJECT_ROOT / args.results_file
        if results_path.is_file():
            results_path.unlink()

    try:
        # Sunucu zaten çalışmıyorsa pipeline onu kendisi ayağa kaldırır.
        if not args.skip_server_start:
            print("Starting local Node.js server...")
            server_process = start_server(args.server_command)

        health_url = f"{args.base_url.rstrip('/')}/health"
        print(f"Waiting for server health check: {health_url}")
        wait_for_health(health_url, args.startup_timeout)

        # Her endpoint'i sırayla test ediyoruz.
        for index, endpoint in enumerate(endpoints):
            print(f"\nRunning benchmark for /{endpoint}...")
            run_benchmark(
                endpoint,
                args,
                overwrite_results=args.overwrite_results and index == 0,
            )

        print(f"\nBenchmark pipeline completed. Results saved to {args.results_file}")
    finally:
        stop_server(server_process)


if __name__ == "__main__":
    # Dosya doğrudan çalıştırıldığında pipeline başlatılır.
    main()
