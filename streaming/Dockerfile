FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY streaming/ ./streaming/
CMD ["python", "-m", "streaming.run_all"]
