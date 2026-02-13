# StreamLink Deployment Guide

This guide details how to deploy the StreamLink application layers:
- **Management Layer**: Render (Web Service)
- **Signaling Layer**: Render (Web Service)
- **Database (Postgres) & Redis**: Render (Managed Services via Blueprint)
- **Client Layer**: Vercel (Static Site)

---

## 🚀 Part 1: Backend Deployment (Render)

We use a **Render Blueprint** (`render.yaml`) to automate the deployment of the Management, Signaling, Redis, and Database services.

### Steps:
1.  **Push your code to GitHub/GitLab**.
2.  Log in to [Render dashboard](https://dashboard.render.com/).
3.  Click **New +** -> **Blueprint**.
4.  Connect your repository.
5.  Render will detect the `render.yaml` file.
6.  Click **Apply Blueprint**.

### What happens next?
- Render will spin up a **PostgreSQL** database and a **Redis** instance.
- It will build and deploy the **Management Layer** (`management-layer`).
- It will build and deploy the **Signaling Layer** (`signaling-layer`).
- **Environment Variables** (like `DATABASE_URL`, `REDIS_URL`) are automatically injected and linked between services.

### ⚠️ Important Note on Ports
- The **Management Layer** runs on port `8000` (HTTP) and `50051` (gRPC).
- The **Signaling Layer** runs on port `8001`.
- Render Web Services expose only **one public port** (usually the one defined in `PORT` env var).
    - Public access to Management API: `https://management-layer-xxxx.onrender.com` (maps to container port 8000).
    - Public access to Signaling WebSocket: `wss://signaling-layer-xxxx.onrender.com` (maps to container port 8001).
- **Internal Communication**: The Signaling Layer connects to the Management Layer via gRPC using the internal private network address (handled by `MANAGEMENT_HOST` env var).

---

## 🌐 Part 2: Frontend Deployment (Vercel)

Now that the backend is live, we deploy the React client to Vercel.

### Steps:
1.  Log in to [Vercel](https://vercel.com/).
2.  Click **Add New...** -> **Project**.
3.  Import your repository.
4.  Select `client_layer` as the **Root Directory** (Edit -> Select `client_layer`).
5.  **Framework Preset**: Select **Vite**.
6.  **Environment Variables**: Add the following (get URLs from your Render dashboard):

    | Variable Name | Value Example | Description |
    | :--- | :--- | :--- |
    | `VITE_API_URL` | `https://management-layer-xxxx.onrender.com` | URL of your Management Service on Render |
    | `VITE_WS_URL` | `wss://signaling-layer-xxxx.onrender.com` | URL of your Signaling Service on Render (use `wss://`) |

7.  Click **Deploy**.

### Configuration
- A `vercel.json` file has been added to `client_layer` to handle client-side routing (rewrites all requests to `index.html`).

---

## ✅ Verification

1.  Open your Vercel deployment URL.
2.  Register/Login (Hits `VITE_API_URL` -> Management Layer).
3.  Create/Join a Room (Hits Management, then Signaling).
4.  Check browser console for "Connected to Signaling Server" (successful WebSocket connection).
