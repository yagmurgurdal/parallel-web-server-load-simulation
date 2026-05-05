import argparse
import asyncio
import os
import time
from pathlib import Path

import aiohttp
import pandas as pd


# Varsayılan ayarlar merkezi tanımlanır; ister env'den ister CLI'dan değiştirilebilir.
DEFAULT_TARGET_URL = os.getenv("TARGET_URL", "http://localhost:3000/blocking")
DEFAULT_LOAD_LEVELS = os.getenv("LOAD_LEVELS", "10,100,500")
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
DEFAULT_CONNECTION_LIMIT = int(os.getenv("CONNECTION_LIMIT", "0"))
DEFAULT_RESULTS_FILE = os.getenv("RESULTS_FILE", "test_results.csv")


def parse_arguments():
    # Test davranışını komut satırından yönetmek için argümanları tanımlar.
    parser = argparse.ArgumentParser(
        description="Run concurrent load tests against the demo Node.js server."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_TARGET_URL,
        help=f"Target endpoint URL. Default: {DEFAULT_TARGET_URL}",
    )
    parser.add_argument(
        "--users",
        default=DEFAULT_LOAD_LEVELS,
        help=f"Comma-separated concurrent user counts. Default: {DEFAULT_LOAD_LEVELS}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}",
    )
    parser.add_argument(
        "--connection-limit",
        type=int,
        default=DEFAULT_CONNECTION_LIMIT,
        help=(
            "Maximum concurrent TCP connections. Use 0 for no client-side limit. "
            f"Default: {DEFAULT_CONNECTION_LIMIT}"
        ),
    )
    parser.add_argument(
        "--results-file",
        default=DEFAULT_RESULTS_FILE,
        help=f"CSV file used to save benchmark results. Default: {DEFAULT_RESULTS_FILE}",
    )
    parser.add_argument(
        "--overwrite-results",
        action="store_true",
        help="Delete the target CSV file before writing new benchmark rows.",
    )
    return parser.parse_args()


def parse_load_levels(raw_value):
    # "10,100,500" gibi bir metni sayısal listeye dönüştürür.
    levels = []
    for value in raw_value.split(","):
        value = value.strip()
        if not value:
            continue

        level = int(value)
        if level <= 0:
            raise ValueError("Concurrent user counts must be positive integers.")

        levels.append(level)

    if not levels:
        raise ValueError("At least one concurrent user count must be provided.")

    return levels


async def fetch_response(session, url, results):
    # Her istek için latency ölçümünü bağımsız tutarız.
    request_start = time.perf_counter()
    try:
        async with session.get(url) as response:
            # Yanıt gövdesini tamamen okuyarak isteği temiz şekilde tamamlıyoruz.
            await response.read()
            request_end = time.perf_counter()
            results.append(
                {
                    "latency": request_end - request_start,
                    "status_code": response.status,
                    "is_success": response.status == 200,
                    "error": "",
                }
            )
    except Exception as exc:
        # Hata alan istekleri de rapora eklemek, başarı oranını doğru hesaplamamızı sağlar.
        request_end = time.perf_counter()
        results.append(
            {
                "latency": request_end - request_start,
                "status_code": None,
                "is_success": False,
                "error": type(exc).__name__,
            }
        )


async def run_load_simulation(
    target_url, concurrent_users, timeout_seconds, connection_limit
):
    # Her senaryo kendi sonuç listesini üretir.
    results = []
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    # Aiohttp'nun bağlantı sayısını burada kontrol ediyoruz.
    # 0 değeri "istemci tarafında limit uygulama" anlamına gelir.
    connector = aiohttp.TCPConnector(limit=connection_limit)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Belirtilen kullanıcı sayısı kadar eşzamanlı görev oluşturuyoruz.
        tasks = [
            fetch_response(session, target_url, results)
            for _ in range(concurrent_users)
        ]
        test_start_time = time.perf_counter()
        await asyncio.gather(*tasks)
        total_duration = time.perf_counter() - test_start_time

    return results, total_duration


def determine_test_type(url):
    # Terminal çıktısı ve CSV raporu için okunabilir bir model adı döndürür.
    return "Non-Blocking" if "non-blocking" in url else "Blocking"


def analyze_and_save(results, duration, user_count, url, results_file):
    # Ham sonuç listesini tabloya çevirip metrikleri hesaplıyoruz.
    df = pd.DataFrame(results)
    success_rate = (df["is_success"].sum() / len(df)) * 100
    average_latency = df["latency"].mean()
    p95_latency = df["latency"].quantile(0.95)
    throughput = len(df) / duration if duration > 0 else 0
    error_count = int((~df["is_success"]).sum())

    test_type = determine_test_type(url)

    print(f"--- {test_type} Test Results ({user_count} Users) ---")
    print(f"Total Test Duration: {duration:.2f} seconds")
    print(f"Throughput: {throughput:.2f} req/sec")
    print(f"Average Latency: {average_latency:.4f} seconds")
    print(f"P95 Latency: {p95_latency:.4f} seconds")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Failed Requests: {error_count}")
    print("-" * 55)

    # Aynı veriyi hem terminale gösteriyor hem de analiz için CSV'ye yazıyoruz.
    report_data = {
        "Model": [test_type],
        "Target_URL": [url],
        "User_Count": [user_count],
        "Throughput_Req_Sec": [round(throughput, 2)],
        "Avg_Latency_Sec": [round(average_latency, 4)],
        "P95_Latency_Sec": [round(p95_latency, 4)],
        "Total_Duration_Sec": [round(duration, 2)],
        "Success_Rate": [round(success_rate, 2)],
        "Failed_Request_Count": [error_count],
    }

    report_df = pd.DataFrame(report_data)
    output_path = Path(results_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Dosya yeniyse başlık da yazılır; mevcutsa sadece satır eklenir.
    if not output_path.is_file():
        report_df.to_csv(output_path, index=False)
    else:
        report_df.to_csv(output_path, mode="a", header=False, index=False)


def main():
    # Program akışı: parametreleri oku, doğrula, her yük seviyesi için testi çalıştır.
    args = parse_arguments()
    load_levels = parse_load_levels(args.users)
    connection_limit = args.connection_limit

    if connection_limit < 0:
        raise ValueError("Connection limit must be 0 or a positive integer.")

    output_path = Path(args.results_file)
    # İstenirse önce eski rapor silinerek temiz benchmark dosyası oluşturulur.
    if args.overwrite_results and output_path.is_file():
        output_path.unlink()

    for level in load_levels:
        print(f"\nScenario: applying load with {level} concurrent users...")
        test_data, duration = asyncio.run(
            run_load_simulation(args.url, level, args.timeout, connection_limit)
        )
        analyze_and_save(test_data, duration, level, args.url, args.results_file)


if __name__ == "__main__":
    # Dosya doğrudan çağrılırsa yük testi başlar.
    main()
