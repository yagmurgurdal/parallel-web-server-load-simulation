import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
INPUT_CSV = RESULTS_DIR / "test_results.csv"
THROUGHPUT_PNG = RESULTS_DIR / "throughput_comparison.png"
AVG_RESPONSE_PNG = RESULTS_DIR / "average_response_time_comparison.png"
ERROR_RATE_PNG = RESULTS_DIR / "error_rate_comparison.png"


def load_results(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Results file not found: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    if not rows:
        raise ValueError("Results CSV is empty.")

    parsed_rows = []
    for row in rows:
        parsed_rows.append(
            {
                "endpoint": row["endpoint"],
                "concurrency_level": int(row["concurrency_level"]),
                "throughput_rps": float(row["throughput_rps"]),
                "average_response_time_ms": float(row["average_response_time_ms"]),
                "error_rate_percent": float(row["error_rate_percent"]),
            }
        )

    return parsed_rows


def group_by_endpoint(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["endpoint"]].append(row)

    for endpoint_rows in grouped.values():
        endpoint_rows.sort(key=lambda item: item["concurrency_level"])

    return dict(grouped)


def plot_metric(
    grouped_rows: dict[str, list[dict]],
    metric_key: str,
    title: str,
    y_label: str,
    output_path: Path,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(9, 5))

    style_map = {
        "/blocking": {"label": "Blocking", "color": "#c0392b"},
        "/non-blocking": {"label": "Non-Blocking", "color": "#1f77b4"},
    }

    for endpoint, rows in grouped_rows.items():
        style = style_map.get(endpoint, {"label": endpoint, "color": "#444444"})
        x_values = [row["concurrency_level"] for row in rows]
        y_values = [row[metric_key] for row in rows]

        axis.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=2.5,
            markersize=7,
            color=style["color"],
            label=style["label"],
        )

    axis.set_title(title)
    axis.set_xlabel("Concurrency Level")
    axis.set_ylabel(y_label)
    axis.set_xticks([10, 50, 100, 200, 500])
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=200)
    plt.close(figure)


def main() -> None:
    rows = load_results(INPUT_CSV)
    grouped_rows = group_by_endpoint(rows)

    plot_metric(
        grouped_rows,
        metric_key="throughput_rps",
        title="Throughput Comparison",
        y_label="Requests Per Second",
        output_path=THROUGHPUT_PNG,
    )
    plot_metric(
        grouped_rows,
        metric_key="average_response_time_ms",
        title="Average Response Time Comparison",
        y_label="Average Response Time (ms)",
        output_path=AVG_RESPONSE_PNG,
    )
    plot_metric(
        grouped_rows,
        metric_key="error_rate_percent",
        title="Error Rate Comparison",
        y_label="Error Rate (%)",
        output_path=ERROR_RATE_PNG,
    )

    print(f"Generated: {THROUGHPUT_PNG}")
    print(f"Generated: {AVG_RESPONSE_PNG}")
    print(f"Generated: {ERROR_RATE_PNG}")


if __name__ == "__main__":
    main()
