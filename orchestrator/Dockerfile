FROM python:3.11-slim
WORKDIR /app
COPY shared/ ./shared/
COPY orchestrator/orchestrator.py ./orchestrator/orchestrator.py
ENV PYTHONPATH=/app
VOLUME ["/results"]
CMD ["python", "orchestrator/orchestrator.py"]
