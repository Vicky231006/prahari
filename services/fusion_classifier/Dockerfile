FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/fusion_classifier/ ./services/fusion_classifier/
COPY services/__init__.py ./services/__init__.py
COPY fusion_model.joblib ./fusion_model.joblib
EXPOSE 8081
CMD ["uvicorn", "services.fusion_classifier.main:app", "--host", "0.0.0.0", "--port", "8081"]
