import os
import subprocess
from dotenv import load_dotenv
import time
import sys

load_dotenv()

# Fallbacks just in case
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql+asyncpg://risklens:risklens@localhost:5432/risklens")
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
os.environ["FINNHUB_API_KEY"] = os.environ.get("FINNHUB_API_KEY", "fake_key")
os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "fake_key")

procs = [
    subprocess.Popen(["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]),
    subprocess.Popen(["python", "-m", "workers.ingestion_worker"]),
    subprocess.Popen(["python", "-m", "workers.fast_path_worker"]),
    subprocess.Popen(["python", "-m", "workers.slow_path_worker"]),
    subprocess.Popen(["python", "-m", "workers.garch_worker"]),
    subprocess.Popen(["python", "-m", "workers.regime_worker"]),
    subprocess.Popen(["python", "-m", "arq", "workers.job_worker.WorkerSettings"]),
]

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    for p in procs:
        p.kill()
    sys.exit(0)
