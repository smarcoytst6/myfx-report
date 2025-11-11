[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# MyFX Report – Flask + Gunicorn + Matplotlib

A tiny Flask API that receives a JSON payload (`account_info` + `trade_data`) and returns a **PNG report as base-64**.

## Quick start (Docker Compose)

```bash
git clone https://github.com/<your-username>/myfx-report.git
cd myfx-report
docker compose up -d

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.