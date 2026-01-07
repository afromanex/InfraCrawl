FROM python:3.11-slim
WORKDIR /app


# Install main and dev requirements
COPY requirements.txt ./
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
	pip install --no-cache-dir -r requirements-dev.txt

COPY . .

CMD ["python", "run.py"]
