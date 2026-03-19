# WanderAI (agentic-travel-main) — Streamlit + LangGraph
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Streamlit default port
EXPOSE 8501

# Run Streamlit (bind to 0.0.0.0 for container access)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
