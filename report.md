# Parallel Web Server Load Simulation and Optimization Report

## Introduction
Modern web systems must handle many client requests at the same time. In event-driven environments such as Node.js, the way requests are handled has a direct effect on performance. This project studies how synchronous blocking behavior and asynchronous non-blocking behavior respond under concurrent load.

## Project Objective
The objective of this project is to build a simple experimental environment that compares two request handling models:

- Synchronous blocking model
- Asynchronous non-blocking model

The comparison is based on load testing results collected with a Python `asyncio` client.

## Technologies Used
- Node.js and Express.js for the web server
- Python 3 with `asyncio` and `aiohttp` for the load generator
- Docker and Docker Compose for repeatable execution
- CSV output for storing test results

## System Architecture
The system has two main parts:

1. A Node.js server exposing `/blocking` and `/non-blocking` endpoints.
2. A Python load tester sending concurrent HTTP requests to both endpoints.

The server listens on port `3000`. The load tester runs a sequence of experiments at predefined concurrency levels and writes the collected metrics to `results/test_results.csv`.

## Synchronous Blocking Model
The blocking endpoint performs CPU-bound work directly on the Node.js main thread. During this time, the event loop is blocked, which means other requests cannot be handled immediately.

This model demonstrates the limitations of synchronous processing in a single-threaded runtime. As concurrency increases, waiting requests accumulate and the overall responsiveness of the server decreases.

## Asynchronous Non-blocking Model
The non-blocking endpoint simulates a waiting task by using `await` with a timer. While the request is waiting, the event loop is not blocked and the server can continue accepting other requests.

This model represents I/O-oriented asynchronous behavior. It is especially useful when the server spends time waiting for external operations such as database access, file reading, or network communication.

## Load Testing Methodology
The load tester runs each endpoint separately with the following concurrency levels:

- 10 concurrent users
- 50 concurrent users
- 100 concurrent users
- 200 concurrent users
- 500 concurrent users

For each concurrency level, one request is sent per virtual user at the same time. The tool measures latency for every request and computes summary metrics for the scenario.

## Performance Metrics
The project records the following metrics:

- Endpoint name
- Concurrency level
- Total requests
- Successful requests
- Failed requests
- Average response time
- Minimum response time
- Maximum response time
- Throughput in requests per second
- Error rate

These metrics allow a direct comparison of how each concurrency model behaves as the amount of simultaneous load increases.

## Experimental Results
Results are saved in `results/test_results.csv`. A typical expectation is:

- The blocking endpoint shows higher response times as concurrency grows.
- The blocking endpoint produces lower throughput because requests are effectively serialized by the blocked event loop.
- The non-blocking endpoint maintains stronger throughput because waiting operations do not freeze the event loop.
- Under high load, the blocking endpoint is more likely to produce timeouts or failed requests.

## Discussion
Which concurrency model performs better and why?

The asynchronous non-blocking model generally performs better under heavy concurrent load. The reason is that waiting operations do not block the event loop, so the server can continue receiving and progressing other requests while one request is paused.

In contrast, the blocking model keeps the event loop busy until the current task is finished. This increases queueing delay for other clients, raises average response time, reduces throughput, and can increase the error rate at high load levels.

Therefore, for workloads that include waiting or I/O latency, the asynchronous non-blocking model is usually more scalable and efficient.

## Conclusion
This project demonstrates the practical performance difference between two concurrency models in Node.js. Even with a simple experiment, the results clearly show that blocking behavior harms scalability under concurrent load, while asynchronous non-blocking behavior allows the server to use the event loop more efficiently.

For this reason, the asynchronous non-blocking model is the better choice for handling large numbers of simultaneous requests in most modern web applications.
