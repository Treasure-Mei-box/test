FROM python:3.10-slim
WORKDIR /app

COPY requirments.txt requirments.txt
RUN pip install --no-cache-dir -r requirments.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn","--bind","0.0.0.0:8000","yls_app.yls_store:app"]