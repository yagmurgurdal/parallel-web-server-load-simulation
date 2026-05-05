const express = require('express');

// Express uygulamasını oluşturuyoruz ve portu environment variable'dan okuyabiliyoruz.
const app = express();
const PORT = Number(process.env.PORT) || 3000;

// JSON gövdeli istekler gelirse Express bunları otomatik parse edebilsin.
app.use(express.json());

// Pipeline ve Docker health check burada sunucunun hazır olduğunu doğrular.
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok' });
});

// Bu endpoint CPU-bound bir işi senkron çalıştırır.
// Döngü devam ederken event loop meşgul olduğu için aynı process başka isteklere
// hızlı cevap veremez; yani "blocking" davranışını gözlemlemiş oluruz.
app.get('/blocking', (req, res) => {
    const start = Date.now();
    console.log('Blocking request received. Event loop is busy until the loop finishes.');

    // Büyük döngü işlemciyi kasıtlı olarak meşgul eder.
    let counter = 0;
    for (let i = 0; i < 5_000_000_000; i++) {
        counter++;
    }

    const end = Date.now();
    res.status(200).json({
        mode: 'Blocking',
        message: `CPU-heavy loop completed. Counter: ${counter}`,
        elapsedMs: end - start
    });
});

// Bu endpoint ise 2 saniyelik I/O benzeri beklemeyi asenkron olarak simüle eder.
// Bekleme sürerken event loop tamamen kilitlenmez ve sunucu başka isteklerle ilgilenebilir.
app.get('/non-blocking', async (req, res) => {
    const start = Date.now();
    console.log('Non-blocking request received. Server remains available while waiting.');

    // Gerçek hayatta bu bölüm bir veritabanı ya da dış servis çağrısı olabilir.
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const end = Date.now();
    res.status(200).json({
        mode: 'Non-Blocking',
        message: 'Simulated I/O wait completed without blocking the event loop.',
        elapsedMs: end - start
    });
});

// Sunucuyu başlatıp test sırasında kullanacağımız URL'leri terminale yazdırıyoruz.
app.listen(PORT, () => {
    console.log(`Target server is running on port ${PORT}.`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`Blocking test: http://localhost:${PORT}/blocking`);
    console.log(`Non-blocking test: http://localhost:${PORT}/non-blocking`);
});
