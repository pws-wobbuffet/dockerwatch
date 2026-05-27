FROM python:3.11-slim

# Create a non-root user and add it to a group whose GID matches the host
# docker group (992) so it can access /var/run/docker.sock without root.
ARG DOCKER_GID=992
RUN groupadd -g ${DOCKER_GID} dockersock \
 && useradd -m -u 1000 -g dockersock app

WORKDIR /app

# Install dependencies as root before switching user.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY src/ ./src/

USER app

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
