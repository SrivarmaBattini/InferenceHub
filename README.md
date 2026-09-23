# InferenceHub

InferenceHub is a production-ready, highly observable backend system designed for managing and running machine learning inference workloads. It is built to be stable, performant, and easily deployable using Docker.

## 🚀 Features

- **Robust Architecture:** Structured around clean practices with dedicated folders for routers, dependencies, schemas, and models.
- **Machine Learning Integration:** Dedicated modules (`ml/`, `ml_models/`) for seamless model deployment and inference.
- **Production-Grade Server:** Configured with Gunicorn (`gunicorn.conf.py`) for reliable process management.
- **Advanced Observability:** Implements structured logging (`logger.py`) and request tracing to monitor system health and metrics.
- **Database Management:** Uses Alembic for safe and synchronous database migrations alongside dedicated `crud/` layers.
- **Containerized Development & Production:** Ship anywhere with fully configured Docker environments (`Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`).
- **Performance Optimized:** Includes caching mechanisms (`cache.py`) and streaming support (`streaming.py`).

## 🛠️ Tech Stack

- **Language:** Python
- **Database Migrations:** Alembic
- **Deployment:** Docker & Docker Compose
- **WSGI/ASGI Server:** Gunicorn

## 📦 Local Setup & Installation

### Option 1: Using Docker (Recommended)
You can easily spin up the environment with Docker Compose:

```bash
# For development environment
docker-compose -f docker-compose.dev.yml up --build

# For production environment
docker-compose up -d --build
```

### Option 2: Local Python Environment
1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations (if applicable):**
   ```bash
   alembic upgrade head
   ```

4. **Start the application:**
   ```bash
   # Run via your standard start script/server
   python main.py
   ```

## 📝 Environment Variables
The application requires environment variables for configuration. Create a `.env` file in the root directory (this file is ignored by Git for security purposes) and add your secrets and database urls there. 

## 🛡️ Security
Security middleware and authentication strategies are handled centrally via `security.py`.

---
*Created and maintained by [SrivarmaBattini](https://github.com/SrivarmaBattini).*
