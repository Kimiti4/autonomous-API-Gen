FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY reservation_system ./reservation_system
RUN useradd -m appuser && chown -R appuser:appuser /srv
USER appuser
EXPOSE 8000
CMD ["uvicorn", "reservation_system.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
