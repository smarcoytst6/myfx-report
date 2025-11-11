# Testing the API

## 1. Start the service

```bash
docker compose up -d

2. Send test request
curl -X POST http://localhost:8000/myfx_report `
  -H "Content-Type: application/json" `
  -d '@docs/sample-request.json' `
  -o response.json

notepad response.json




