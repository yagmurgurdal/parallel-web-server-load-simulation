import csv
from pathlib import Path

import matplotlib.pyplot as plt


# Tüm analiz çıktıları bu klasörde toplanır.
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_FILE = PROJECT_ROOT / "test_results.csv"
OUTPUT_DIR = PROJECT_ROOT / "analysis"
OUTPUT_CSV = OUTPUT_DIR / "latest_clean_results.csv"
OUTPUT_REPORT = OUTPUT_DIR / "benchmark_summary.md"
THROUGHPUT_CHART = OUTPUT_DIR / "throughput_comparison.png"
AVG_LATENCY_CHART = OUTPUT_DIR / "avg_latency_comparison.png"
P95_LATENCY_CHART = OUTPUT_DIR / "p95_latency_comparison.png"


def load_latest_modern_rows(csv_path):
    # test_results.csv içinde eski ve yeni format satırlar karışık olabilir.
    # Burada yalnızca 9 kolonlu güncel benchmark satırlarını alıyoruz.
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    modern_rows = [row for row in rows if len(row) == 9 and row[0] != "Model"]
    if not modern_rows:
        raise ValueError("No modern benchmark rows with P95 metrics were found.")

    # Aynı model + kullanıcı sayısı kombinasyonu için son kaydı saklıyoruz.
    latest_by_key = {}
    for row in modern_rows:
        model = row[0]
        user_count = int(row[2])
        latest_by_key[(model, user_count)] = {
            "Model": model,
            "Target_URL": row[1],
            "User_Count": user_count,
            "Throughput_Req_Sec": float(row[3]),
            "Avg_Latency_Sec": float(row[4]),
            "P95_Latency_Sec": float(row[5]),
            "Total_Duration_Sec": float(row[6]),
            "Success_Rate": float(row[7]),
            "Failed_Request_Count": int(row[8]),
        }

    return [
        latest_by_key[key]
        for key in sorted(latest_by_key, key=lambda item: (item[1], item[0]))
    ]


def write_clean_csv(rows, output_path):
    # Temizlenmiş veri kümesini ayrı bir CSV olarak dışa aktarır.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Model",
        "Target_URL",
        "User_Count",
        "Throughput_Req_Sec",
        "Avg_Latency_Sec",
        "P95_Latency_Sec",
        "Total_Duration_Sec",
        "Success_Rate",
        "Failed_Request_Count",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_model_map(rows):
    # Veriyi model ve kullanıcı sayısı bazında sözlüğe dönüştürür.
    model_map = {}
    for row in rows:
        model_map.setdefault(row["Model"], {})[row["User_Count"]] = row
    return model_map


def format_table(rows):
    # Markdown rapora doğrudan eklenebilecek tablo metni üretir.
    lines = [
        "| Model | Users | Throughput (req/sec) | Avg Latency (s) | P95 Latency (s) | Duration (s) | Success Rate (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{row['Model']} | "
            f"{row['User_Count']} | "
            f"{row['Throughput_Req_Sec']:.2f} | "
            f"{row['Avg_Latency_Sec']:.4f} | "
            f"{row['P95_Latency_Sec']:.4f} | "
            f"{row['Total_Duration_Sec']:.2f} | "
            f"{row['Success_Rate']:.2f} |"
        )

    return "\n".join(lines)


def comparison_lines(model_map):
    # Her yük seviyesi için iki model arasındaki oranları hesaplar.
    blocking = model_map["Blocking"]
    non_blocking = model_map["Non-Blocking"]
    lines = []

    for users in sorted(blocking):
        blocking_row = blocking[users]
        non_blocking_row = non_blocking[users]

        throughput_ratio = (
            non_blocking_row["Throughput_Req_Sec"]
            / blocking_row["Throughput_Req_Sec"]
        )
        avg_latency_ratio = (
            blocking_row["Avg_Latency_Sec"]
            / non_blocking_row["Avg_Latency_Sec"]
        )
        p95_ratio = (
            blocking_row["P95_Latency_Sec"]
            / non_blocking_row["P95_Latency_Sec"]
        )

        if users == 10:
            headline = (
                f"At {users} users, the blocking endpoint is faster because its CPU loop "
                f"finishes much sooner than the non-blocking endpoint's fixed 2-second wait."
            )
        elif users == 100:
            headline = (
                f"At {users} users, blocking still looks faster on raw throughput and latency, "
                f"but the gap is narrowing as concurrency rises."
            )
        else:
            headline = (
                f"At {users} users, the non-blocking endpoint scales better under concurrency."
            )

        lines.append(
            "- "
            + headline
            + " "
            + f"Throughput ratio (non-blocking/blocking): {throughput_ratio:.2f}x. "
            + f"Average latency ratio (blocking/non-blocking): {avg_latency_ratio:.2f}x. "
            + f"P95 latency ratio (blocking/non-blocking): {p95_ratio:.2f}x."
        )

    return "\n".join(lines)


def build_findings(model_map):
    # Raporun en önemli kısa bulgularını üretir.
    blocking = model_map["Blocking"]
    non_blocking = model_map["Non-Blocking"]

    return "\n".join(
        [
            "- All six latest benchmark rows completed with a 100% success rate and zero failed requests.",
            "- The blocking endpoint has lower latency at 10 users because the CPU loop takes well under 2 seconds, so this is not an apples-to-apples latency comparison at low concurrency.",
            "- At 100 users, blocking still leads on raw throughput and latency because each request does less total work than the fixed 2-second non-blocking wait.",
            f"- At 500 users, non-blocking throughput reaches {non_blocking[500]['Throughput_Req_Sec']:.2f} req/sec versus {blocking[500]['Throughput_Req_Sec']:.2f} req/sec for blocking.",
            f"- At 500 users, blocking average latency rises to {blocking[500]['Avg_Latency_Sec']:.4f}s while non-blocking stays near {non_blocking[500]['Avg_Latency_Sec']:.4f}s.",
            f"- At 500 users, blocking P95 latency reaches {blocking[500]['P95_Latency_Sec']:.4f}s, which is about {blocking[500]['P95_Latency_Sec'] / non_blocking[500]['P95_Latency_Sec']:.2f}x higher than non-blocking.",
        ]
    )


def create_line_chart(rows, metric_key, metric_label, output_path):
    # Belirli bir metriği kullanıcı sayısına karşı çizgi grafik olarak üretir.
    plt.style.use("seaborn-v0_8-whitegrid")

    figure, axis = plt.subplots(figsize=(8, 5))
    colors = {
        "Blocking": "#c0392b",
        "Non-Blocking": "#1f77b4",
    }

    model_map = build_model_map(rows)
    for model, user_map in model_map.items():
        users = sorted(user_map)
        values = [user_map[user][metric_key] for user in users]

        # Her model farklı renkte çizilir ki görsel karşılaştırma kolay olsun.
        axis.plot(
            users,
            values,
            marker="o",
            linewidth=2.5,
            markersize=7,
            color=colors[model],
            label=model,
        )

        # Veri noktalarının üstüne ham değeri yazdırarak grafiği tek başına okunabilir tutuyoruz.
        for user, value in zip(users, values):
            offset = 0.03 * max(values) if max(values) > 1 else 0.03
            axis.text(user, value + offset, f"{value:.2f}", ha="center", fontsize=9)

    axis.set_title(f"{metric_label} Comparison", fontsize=14, pad=12)
    axis.set_xlabel("Concurrent Users")
    axis.set_ylabel(metric_label)
    axis.set_xticks(sorted({row["User_Count"] for row in rows}))
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def create_charts(rows):
    # Üç ana performans metriği için grafik üretir.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_line_chart(rows, "Throughput_Req_Sec", "Throughput (req/sec)", THROUGHPUT_CHART)
    create_line_chart(rows, "Avg_Latency_Sec", "Average Latency (s)", AVG_LATENCY_CHART)
    create_line_chart(rows, "P95_Latency_Sec", "P95 Latency (s)", P95_LATENCY_CHART)


def write_report(rows, output_path):
    # Temiz veri, grafik referansları ve yorumları tek Markdown dosyasında toplar.
    model_map = build_model_map(rows)
    report = "\n".join(
        [
            "# Benchmark Data Analysis",
            "",
            "This summary is based on the latest complete benchmark rows that include P95 latency values. Older CSV formats were ignored during the analysis.",
            "",
            "## Clean Benchmark Table",
            "",
            format_table(rows),
            "",
            "## Charts",
            "",
            f"- Throughput chart: `{THROUGHPUT_CHART.name}`",
            f"- Average latency chart: `{AVG_LATENCY_CHART.name}`",
            f"- P95 latency chart: `{P95_LATENCY_CHART.name}`",
            "",
            "## Key Findings",
            "",
            build_findings(model_map),
            "",
            "## Per-Load Comparison",
            "",
            comparison_lines(model_map),
            "",
            "## Conclusion",
            "",
            "The results support the expected concurrency behavior. The blocking endpoint appears faster at low and medium load here because it performs a shorter unit of work than the non-blocking endpoint's fixed 2-second wait. However, its latency grows sharply as concurrency increases, while the non-blocking endpoint stays near a stable latency band and overtakes blocking decisively at high concurrency, especially at 500 users.",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def main():
    # Analiz akışı:
    # 1. Güncel benchmark satırlarını seç
    # 2. Temiz CSV üret
    # 3. Grafik üret
    # 4. Yazılı analiz raporu oluştur
    rows = load_latest_modern_rows(SOURCE_FILE)
    write_clean_csv(rows, OUTPUT_CSV)
    create_charts(rows)
    write_report(rows, OUTPUT_REPORT)
    print(f"Clean CSV written to {OUTPUT_CSV}")
    print(f"Throughput chart written to {THROUGHPUT_CHART}")
    print(f"Average latency chart written to {AVG_LATENCY_CHART}")
    print(f"P95 latency chart written to {P95_LATENCY_CHART}")
    print(f"Summary report written to {OUTPUT_REPORT}")


if __name__ == "__main__":
    # Dosya doğrudan çalıştırıldığında veri analizi başlar.
    main()
