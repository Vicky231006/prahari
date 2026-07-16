FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY data/synthetic/ ./data/synthetic/
CMD ["python", "-m", "data.synthetic.generators.run_generators"]
