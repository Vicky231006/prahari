FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY data/synthetic/ ./data/synthetic/
CMD ["python", "-m", "data.synthetic.generators.run_generators"]
