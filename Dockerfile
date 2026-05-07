# Run: docker build -t tjs-assist . && docker run -p 8501:8501 -e GOOGLE_API_KEY=your_key tjs-assist
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

# Many hosts set PORT (e.g. Railway, Render, Cloud Run).
ENTRYPOINT ["sh", "-c", "exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=${PORT:-8501} \
  --server.headless=true"]
