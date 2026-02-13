FROM python:3.11-slim
WORKDIR /app
COPY shared/ ./shared/
COPY resource_node/resource_node.py ./resource_node/resource_node.py
ENV PYTHONPATH=/app
CMD ["python", "resource_node/resource_node.py"]
