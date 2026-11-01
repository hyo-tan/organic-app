# 有機化合物ツール バックエンド (FastAPI + RDKit)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# compounds.db は compose 側でボリュームマウントする（無い場合は JSON フォールバックで起動）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
