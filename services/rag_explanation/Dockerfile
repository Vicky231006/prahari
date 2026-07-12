FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/rag_explanation/ ./services/rag_explanation/
COPY services/__init__.py ./services/__init__.py
EXPOSE 8082
CMD ["uvicorn", "services.rag_explanation.main:app", "--host", "0.0.0.0", "--port", "8082"]
