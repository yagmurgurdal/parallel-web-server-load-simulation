FROM python:3.11-slim

WORKDIR /app/load_tester

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY load_test.py ./

CMD ["python", "load_test.py"]
