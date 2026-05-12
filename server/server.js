const express = require('express');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const DEFAULT_DELAY_MS = Number(process.env.SIMULATION_DELAY_MS) || 100;

app.use(express.json());

function parseDelayMs(value) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_DELAY_MS;
  }

  return Math.min(parsed, 5000);
}

function runBlockingWork(durationMs) {
  const endTime = Date.now() + durationMs;
  let counter = 0;

  while (Date.now() < endTime) {
    counter += 1;
  }

  return counter;
}

app.get('/health', (_req, res) => {
  res.status(200).json({
    status: 'ok',
    port: PORT,
    defaultDelayMs: DEFAULT_DELAY_MS,
  });
});

app.get('/blocking', (req, res, next) => {
  try {
    const requestedDelayMs = parseDelayMs(req.query.delayMs);
    const startTime = process.hrtime.bigint();
    const iterations = runBlockingWork(requestedDelayMs);
    const elapsedMs = Number(process.hrtime.bigint() - startTime) / 1_000_000;

    res.status(200).json({
      endpoint: 'blocking',
      model: 'Synchronous Blocking',
      configuredDelayMs: requestedDelayMs,
      measuredDurationMs: Number(elapsedMs.toFixed(2)),
      iterations,
      message: 'CPU-bound work completed on the main thread.',
    });
  } catch (error) {
    next(error);
  }
});

app.get('/non-blocking', async (req, res, next) => {
  try {
    const requestedDelayMs = parseDelayMs(req.query.delayMs);
    const startTime = process.hrtime.bigint();

    await new Promise((resolve) => setTimeout(resolve, requestedDelayMs));

    const elapsedMs = Number(process.hrtime.bigint() - startTime) / 1_000_000;

    res.status(200).json({
      endpoint: 'non-blocking',
      model: 'Asynchronous Non-Blocking',
      configuredDelayMs: requestedDelayMs,
      measuredDurationMs: Number(elapsedMs.toFixed(2)),
      message: 'I/O-style wait completed without blocking the event loop.',
    });
  } catch (error) {
    next(error);
  }
});

app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.method} ${req.originalUrl} does not exist.`,
  });
});

app.use((error, _req, res, _next) => {
  console.error('Server error:', error);

  res.status(500).json({
    error: 'Internal Server Error',
    message: 'The server could not complete the request.',
  });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`Blocking endpoint: http://localhost:${PORT}/blocking`);
  console.log(`Non-blocking endpoint: http://localhost:${PORT}/non-blocking`);
});
