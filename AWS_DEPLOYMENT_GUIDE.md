# FINNY — AWS Deployment Guide

This guide outlines the architecture and future deployment procedure for the **FINNY — Financial Statement Review Agent**.

---

## 1. System Architecture

```
                                  AWS Cloud
  GitHub Repository
         │
         ├────────────────────────────────────────► AWS Amplify Hosting
         │                                               │
         │                                               ▼
         │                                       React 19 + Vite 8 Frontend
         │                                               │
         │                                               │ HTTPS (API Requests)
         │                                               ▼
         └────────────────────────────────────────► AWS EC2 (Ubuntu 22.04 LTS)
                                                         │
                                                       Nginx (Ports 80/443, SSL)
                                                         │
                                                    FastAPI Backend (127.0.0.1:8001)
                                                         │
                                    ┌────────────────────┴────────────────────┐
                                    │                                         │
                             Core Financial Services                   Private Ollama Instance
                                    │                                    (127.0.0.1:11434)
                          • Ingestion (PDF, XLSX, CSV, DOCX)                  │
                          • Normalization Engine                              ▼
                          • Isolation Forest ML Anomaly Detector         Qwen 2.5 7B LLM
                          • Agent 1 (Mathematical Discrepancies)        (Agent 2 & Finny Chat)
                          • Agent 2 (Observations & Narrative Review)
```

### Key Architectural Isolation Guarantees:
1. **Frontend**: Hosted on **AWS Amplify Hosting** as a globally distributed static Single Page Application (SPA).
2. **Backend**: Hosted on an **AWS EC2 instance** running FastAPI via Uvicorn, reverse-proxied behind Nginx.
3. **AI / LLM Engine**: **Ollama** runs locally on the EC2 instance, bound exclusively to `127.0.0.1:11434`. It is **NEVER** exposed to the public internet or Nginx routing.
4. **Network Security**: Only ports `80` (HTTP) and `443` (HTTPS) are exposed on the EC2 Security Group.

---

## Part A: Frontend Deployment on AWS Amplify Hosting

### 1. Prerequisites & Preparation
- The repository contains `Frontend/amplify.yml` which defines the build lifecycle (`npm ci`, `npm run build`, output: `dist`).
- The repository contains `Frontend/amplify_redirects.json` defining the SPA fallback rule for React Router.

### 2. Steps in AWS Amplify Console
1. Log in to the [AWS Management Console](https://console.aws.amazon.com/) and navigate to **AWS Amplify**.
2. Click **Host an application** -> Select **GitHub** -> Authorize AWS Amplify.
3. Select your repository (`Financial-Statement-Review-Agent`) and branch (`main`).
4. **App Root Directory**: Set to `Frontend` (or check the monorepo checkbox and specify `Frontend`).
5. **Environment Variables**:
   In **Advanced settings** -> **Environment variables**, add:
   | Key | Value Description | Example |
   |---|---|---|
   | `VITE_API_BASE_URL` | Your EC2 Backend API Endpoint | `https://api.yourdomain.com/api/v1` |
   | `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth 2.0 Web Client ID | `xxxx.apps.googleusercontent.com` |
6. Click **Save and Deploy**. AWS Amplify will automatically build and host the static application.

### 3. Configure SPA Redirects in Amplify
In AWS Amplify Console:
1. Go to **App settings** -> **Rewrites and redirects**.
2. Add the following rule (from `Frontend/amplify_redirects.json`):
   - **Source address**: `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>`
   - **Target address**: `/index.html`
   - **Type**: `200 (Rewrite)`
3. Save. This ensures direct navigation to `/login`, `/dashboard`, `/upload`, `/review`, etc. loads correctly.

### 4. Update Google OAuth Authorized Origins
1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Edit your OAuth 2.0 Client ID.
3. Add your AWS Amplify domain (e.g. `https://main.xxxx.amplifyapp.com` and custom domain) to **Authorized JavaScript origins**.

---

## Part B: Backend Deployment on AWS EC2

### 1. EC2 Instance Selection
- **Recommended Instance Type**: `g4dn.xlarge` (NVIDIA T4 GPU, recommended for optimal Qwen 2.5 7B inference speeds) or `t3.xlarge` / `c6i.2xlarge` (4 vCPUs, 16 GB RAM minimum for CPU inference).
- **Operating System**: Ubuntu 22.04 LTS.
- **Storage**: 50 GB gp3 SSD (to accommodate OS, PyTorch/scikit-learn dependencies, and the 4.7 GB Qwen model weights).

### 2. Security Group Configuration
| Type | Protocol | Port Range | Source | Purpose |
|---|---|---|---|---|
| SSH | TCP | 22 | Your IP only | Secure Administration |
| HTTP | TCP | 80 | `0.0.0.0/0` | Let's Encrypt / HTTP redirect |
| HTTPS | TCP | 443 | `0.0.0.0/0` | Secure Backend API Traffic |
| Custom TCP | TCP | 8001 | **BLOCKED** | FastAPI internal port |
| Custom TCP | TCP | 11434 | **BLOCKED** | Ollama internal port |

### 3. Server Setup & Ollama Installation
On your EC2 instance:
```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 3. Pull Qwen 2.5 7B model
ollama pull qwen2.5:7b

# 4. Verify Ollama is listening locally
curl http://127.0.0.1:11434/api/tags
```

### 4. Deploying the Backend Application

#### Option 1: Direct Systemd Service (Standard)
1. Clone the repository to `/opt/finny`:
   ```bash
   sudo git clone https://github.com/Tejesh104/Financial-Statement-Review-Agent.git /opt/finny
   cd "/opt/finny/Congizant Backend/finny-backend"
   ```
2. Set up Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Configure `.env`:
   ```bash
   cp .env.example .env
   nano .env
   # Populate DATABASE_URL, JWT_SECRET_KEY, ALLOWED_ORIGINS (with your Amplify domain)
   ```
4. Install and enable Systemd service:
   ```bash
   sudo cp /opt/finny/deployment/systemd/finny-backend.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable finny-backend
   sudo systemctl start finny-backend
   sudo systemctl status finny-backend
   ```

#### Option 2: Docker Container
1. Build and run using the provided `Dockerfile`:
   ```bash
   cd "/opt/finny/Congizant Backend/finny-backend"
   docker build -t finny-backend:latest .
   docker run -d \
     --name finny-api \
     --restart always \
     --network host \
     --env-file .env \
     finny-backend:latest
   ```

### 5. Nginx & SSL Setup
1. Copy the Nginx configuration:
   ```bash
   sudo cp /opt/finny/deployment/nginx/finny.conf /etc/nginx/sites-available/finny.conf
   sudo ln -s /etc/nginx/sites-available/finny.conf /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   ```
2. Edit `/etc/nginx/sites-available/finny.conf` and replace `<YOUR_API_DOMAIN>` with your actual domain (e.g. `api.yourdomain.com`).
3. Obtain SSL certificate via Certbot:
   ```bash
   sudo certbot --nginx -d api.yourdomain.com
   sudo systemctl restart nginx
   ```
4. Verify backend health endpoint externally:
   ```bash
   curl https://api.yourdomain.com/api/health
   ```

---

## Part C: Environment Variables Checklist

### Backend (`.env` on EC2)
| Variable | Description | Example / Note |
|---|---|---|
| `PORT` | Uvicorn listen port | `8001` |
| `APP_ENV` | Environment identifier | `production` |
| `DEBUG` | FastAPI debug mode | `False` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@rds-host:5432/finny` |
| `JWT_SECRET_KEY` | Cryptographic signing key | 32+ character random hex/base64 |
| `GOOGLE_CLIENT_ID` | OAuth audience verification | `xxxx.apps.googleusercontent.com` |
| `ALLOWED_ORIGINS` | CORS allowed origins list | `["https://main.xxxx.amplifyapp.com"]` |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Ollama model tag | `qwen2.5:7b` |
| `OLLAMA_TIMEOUT_SECONDS` | Timeout for AI inference | `240` |

### Frontend (`Frontend/.env` / AWS Amplify Console)
| Variable | Description | Example / Note |
|---|---|---|
| `VITE_API_BASE_URL` | Target production backend URL | `https://api.yourdomain.com/api/v1` |
| `VITE_GOOGLE_CLIENT_ID` | OAuth 2.0 Web Client ID | `xxxx.apps.googleusercontent.com` |
