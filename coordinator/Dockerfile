FROM python:3.11-slim
WORKDIR /app
COPY shared/ ./shared/
COPY coordinator/coordinator.py ./coordinator/coordinator.py
ENV PYTHONPATH=/app
CMD ["python", "coordinator/coordinator.py"]
