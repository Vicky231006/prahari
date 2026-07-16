FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download the ChromaDB default ONNX embedding model at build time
# so the container starts instantly instead of blocking on a ~80 MB download.
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()"
COPY services/rag_explanation/ ./services/rag_explanation/
COPY services/__init__.py ./services/__init__.py
EXPOSE 8082
CMD ["uvicorn", "services.rag_explanation.main:app", "--host", "0.0.0.0", "--port", "8082"]
