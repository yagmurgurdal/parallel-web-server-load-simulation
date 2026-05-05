# Node.js sunucusunu çalıştıracak hafif Linux tabanı.
FROM node:18-alpine

# Container içindeki ana çalışma dizini.
WORKDIR /app

# Önce sadece paket dosyalarını kopyalıyoruz.
# Böylece kaynak kod değişse bile npm install katmanı cache'ten gelebilir.
COPY package*.json ./
RUN npm install

# Uygulamanın geri kalan kaynak kodlarını imaja ekliyoruz.
COPY . .

# Sunucunun dinlediği portu belgeliyoruz.
EXPOSE 3000

# Container başladığında Express sunucusu ayağa kalkar.
CMD ["node", "index.js"]
