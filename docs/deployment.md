# Production Deployment Guide - SHL Assessment Recommendation portal

This guide provides step-by-step instructions for deploying the containerized FastAPI recommendation service to Render and Railway.

---

## 1. Environment Configurations (All Platforms)

Ensure the following environment variables are set in your production console:

| Variable Name | Required | Default Value | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | **Yes** | (none) | Your Gemini API Key from Google AI Studio. |
| `MODEL_NAME` | No | `gemini-1.5-flash` | The LLM model configuration. |
| `TEMPERATURE` | No | `0.0` | Sampling temperature for LLM replies. |
| `TOP_K` | No | `5` | Maximum number of hybrid retrieval results. |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Embedding model for semantic search. |

---

## 2. Deploying to Render (Docker Service)

Render supports deploying from Docker files on their free tier.

### Step-by-Step:
1. Push your codebase to a GitHub or GitLab repository.
2. Log in to [Render](https://render.com) and click **New +** -> **Web Service**.
3. Connect your repository.
4. Configure the service settings:
   - **Name**: `shl-assessment-agent`
   - **Region**: Select region closest to your clients.
   - **Branch**: `main` (or default branch)
   - **Runtime**: `Docker`
5. In the **Environment Variables** section, add your `GOOGLE_API_KEY` (and any other settings from Section 1).
6. Click **Deploy Web Service**.
7. Render will pull your repository, execute the multi-stage build specified in the `Dockerfile` (which automatically compiles the search index), and expose the service.

Your service health url will be: `https://<your-render-subdomain>.onrender.com/health`

---

## 3. Deploying to Railway

Railway is another popular platform that builds directly from Dockerfiles.

### Step-by-Step:
1. Connect your GitHub account to [Railway](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Choose your repository.
4. Click **Add Variables** and define `GOOGLE_API_KEY`.
5. Railway will detect the `Dockerfile` automatically and provision a builder instance. It builds the runtime image and provisions an IP address.
6. Under **Settings** -> **Public Networking**, click **Generate Domain** to open a public URL.

Your service url is ready for integrations!
