# Parallel Web Server Load Simulation

This project demonstrates the difference between **blocking** and **non-blocking** request handling in Node.js under concurrent load.

It includes:

- a small Express server with two comparison endpoints
- an asynchronous Python load tester
- a one-command local benchmark pipeline
- Docker support for running the full workflow in containers
- a result analysis script for generating clean benchmark summaries

## Overview

The server exposes two endpoints:

- `GET /blocking`
  Runs a CPU-heavy synchronous loop. This blocks the Node.js event loop while the work is being processed.
- `GET /non-blocking`
  Simulates a 2-second I/O wait with `setTimeout`. This does not block the event loop in the same way, so the server can continue handling other requests.

The goal of the project is to show how these two models behave differently as concurrency increases.

## Tech Stack

- `Node.js` + `Express` for the demo server
- `Python` + `asyncio` + `aiohttp` for concurrent load generation
- `pandas` for result processing
- `matplotlib` for benchmark chart generation
- `Docker` + `Docker Compose` for containerized execution

## Project Structure

```text
parallel_programming_project/
├── index.js               # Express server with blocking and non-blocking endpoints
├── load_tester.py         # Async load test runner
├── run_pipeline.py        # End-to-end benchmark pipeline
├── analyze_results.py     # Result cleanup and analysis script
├── Dockerfile             # Node.js server image
├── dockerfile.tester      # Python test runner image
├── docker-compose.yml     # Multi-container benchmark workflow
├── requirements.txt       # Python dependencies
├── package.json           # Node.js scripts and metadata
└── README.md              # Project documentation
```

Generated benchmark outputs such as CSV files, charts, and temporary analysis files are intentionally excluded from version control.

## Requirements

- `Node.js 18+`
- `Python 3.10+`
- `Docker` and `Docker Compose` (optional)

## Installation

### Node.js dependencies

```bash
npm install
```

PowerShell:

```powershell
npm.cmd install
```

### Python dependencies

```bash
python -m pip install -r requirements.txt
```

## Running the Server

```bash
npm start
```

PowerShell:

```powershell
npm.cmd start
```

The server will run on:

- `http://localhost:3000/health`
- `http://localhost:3000/blocking`
- `http://localhost:3000/non-blocking`

## Running Individual Load Tests

You can test either endpoint directly with `load_tester.py`.

### Blocking endpoint

```bash
python load_tester.py --url http://localhost:3000/blocking --users 10,100,500 --connection-limit 0
```

### Non-blocking endpoint

```bash
python load_tester.py --url http://localhost:3000/non-blocking --users 10,100,500 --connection-limit 0
```

### Useful options

- `--url`: target endpoint
- `--users`: comma-separated concurrent user counts
- `--timeout`: per-request timeout in seconds
- `--connection-limit`: client-side connection cap, `0` means unlimited
- `--results-file`: output CSV path
- `--overwrite-results`: clears the output file before writing

## Running the Full Local Benchmark Pipeline

This command:

1. starts the Node.js server
2. waits until `/health` responds successfully
3. benchmarks both `/blocking` and `/non-blocking`
4. writes the benchmark results to CSV
5. shuts the server down

```bash
python run_pipeline.py --overwrite-results
```

PowerShell:

```powershell
npm.cmd run benchmark
```

### Example variations

```bash
python run_pipeline.py --users 10,100,500 --connection-limit 0
python run_pipeline.py --endpoints non-blocking
python run_pipeline.py --skip-server-start --base-url http://localhost:3000
```

## Running with Docker

To run the full benchmark flow in containers:

```bash
docker compose up --build --abort-on-container-exit
```

What happens:

1. the `server` container starts the Express app
2. Docker waits for the `/health` check to pass
3. the `tester` container runs the benchmark pipeline
4. results are written to the mounted `results/` folder on the host machine

## Analyzing Results

After running benchmarks, you can generate a cleaned summary and charts:

```bash
python analyze_results.py
```

This script:

- filters the latest valid benchmark rows
- writes a clean CSV summary
- generates comparison charts
- writes a Markdown report

Note:

- `matplotlib` must be installed for chart generation
- generated analysis files are not tracked in Git

## Scripts

Available `npm` scripts:

- `npm start`: start the Node.js server
- `npm run benchmark`: run the full local benchmark pipeline
- `npm run benchmark:docker`: run the benchmark workflow with Docker Compose

PowerShell users may need to replace `npm` with `npm.cmd`.

## What This Project Demonstrates

- how CPU-bound synchronous code can block the Node.js event loop
- how asynchronous waiting behaves differently under concurrent load
- why throughput, average latency, and P95 latency all matter in performance analysis
- how to automate benchmarking with a reproducible pipeline

## License

This project is provided for educational and experimental purposes.
