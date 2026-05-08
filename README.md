# Parallel Web Server Load Simulation

This project explores how **blocking** and **non-blocking** request handling behave under concurrent load in a Node.js application.

It was built as a compact performance engineering experiment around one important backend idea:

> when CPU-bound work blocks the event loop, throughput and responsiveness degrade very differently than in asynchronous waiting workflows.

The repository combines a lightweight Express server, an asynchronous Python load tester, a reproducible benchmark pipeline, and result analysis tooling.

## Why This Project Matters

Performance discussions in backend development often stay theoretical. This project turns one of the most important Node.js runtime concepts into a repeatable benchmark:

- what happens when the event loop is blocked by synchronous CPU work
- how that differs from non-blocking waiting behavior
- why concurrency, latency, and throughput need to be measured together

Because of that, the repository works well as both a learning project and a portfolio example for systems thinking, concurrency, and backend performance analysis.

## What the Project Includes

- a small Express server with two comparison endpoints
- an asynchronous Python load tester built with `asyncio` and `aiohttp`
- a one-command local benchmark pipeline
- Docker support for containerized execution
- a result analysis script for producing clean summaries and charts

## Comparison Model

The server exposes two main endpoints:

- `GET /blocking`
  Runs a CPU-heavy synchronous loop. While this loop is running, the Node.js event loop is occupied and the process becomes less responsive to other requests.

- `GET /non-blocking`
  Simulates a 2-second asynchronous I/O-style wait with `setTimeout`. This does not block the event loop in the same way, so the server remains more available while waiting.

The goal is not to claim that `setTimeout` is a real I/O workload. The goal is to create a clean educational comparison between CPU-bound blocking work and asynchronous non-blocking waiting.

## Tech Stack

- `Node.js` and `Express` for the demo server
- `Python`, `asyncio`, and `aiohttp` for concurrent load generation
- `pandas` for result processing
- `matplotlib` for benchmark chart generation
- `Docker` and `Docker Compose` for containerized execution

## Repository Structure

```text
.
├── index.js
├── load_tester.py
├── run_pipeline.py
├── analyze_results.py
├── Dockerfile
├── dockerfile.tester
├── docker-compose.yml
├── requirements.txt
├── package.json
└── README.md
```

Generated benchmark outputs such as CSV files, charts, and temporary analysis files are intentionally excluded from version control.

## Installation

Install Node.js dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Running the Server

```bash
npm start
```

The server will run on:

- `http://localhost:3000/health`
- `http://localhost:3000/blocking`
- `http://localhost:3000/non-blocking`

## Running Individual Load Tests

Blocking endpoint:

```bash
python load_tester.py --url http://localhost:3000/blocking --users 10,100,500 --connection-limit 0
```

Non-blocking endpoint:

```bash
python load_tester.py --url http://localhost:3000/non-blocking --users 10,100,500 --connection-limit 0
```

Useful options:

- `--url` for the target endpoint
- `--users` for concurrent user counts
- `--timeout` for per-request timeout
- `--connection-limit` for client-side connection caps
- `--results-file` for output CSV path
- `--overwrite-results` to clear prior outputs

## Running the Full Benchmark Pipeline

This command:

1. starts the Node.js server
2. waits for `/health`
3. benchmarks both endpoints
4. writes benchmark results to CSV
5. shuts the server down

```bash
python run_pipeline.py --overwrite-results
```

You can also use:

```bash
npm run benchmark
```

## Running with Docker

```bash
docker compose up --build --abort-on-container-exit
```

This workflow:

1. starts the `server` container
2. waits for the health check to pass
3. runs the benchmark pipeline in the `tester` container
4. writes results to the mounted `results/` folder

## Analyzing Results

After running benchmarks, generate a cleaned summary and charts with:

```bash
python analyze_results.py
```

This script:

- filters valid benchmark rows
- writes a clean summary
- generates comparison charts
- produces a Markdown-style benchmark report

## What This Repository Demonstrates

- how CPU-bound synchronous work blocks the Node.js event loop
- how asynchronous waiting behaves under concurrent load
- why backend performance needs measured evidence
- how to automate repeatable benchmarks
- how to connect systems concepts to interpretable outputs

## Possible Improvements

Future extensions could include:

- a truly I/O-bound workload such as database or file access
- richer latency metrics such as P95 and P99 by default
- worker-thread or clustering comparisons
- dashboard-style visualization of throughput and latency together

## License

This project is shared for educational and experimental use.
