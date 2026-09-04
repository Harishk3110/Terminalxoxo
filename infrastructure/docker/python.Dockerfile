FROM python:3.12-slim

ARG SERVICE_DIR
WORKDIR /app

COPY services/${SERVICE_DIR}/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/${SERVICE_DIR} ./

EXPOSE 8000 8010 8020
CMD ["python", "-m", "app.main"]
