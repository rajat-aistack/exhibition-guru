# 🚀 Deployment Guide: Exhibition Guru on Render

This guide provides step-by-step instructions for deploying the **Exhibition Guru** Flask web application to [Render.com](https://render.com) for free.

---

## 📋 Prerequisites

Before starting, ensure you have:
1. A **GitHub account** ([github.com](https://github.com)).
2. A **Render account** ([render.com](https://render.com)).
3. **Git** installed on your computer.

---

## 🛠️ Step 1: Push Code to GitHub

If you haven't pushed your code to GitHub yet, follow these commands in your project terminal:

```bash
# 1. Initialize Git (if not already initialized)
git init

# 2. Add all files to staging
git add .

# 3. Commit your changes
git commit -m "Initial commit - Exhibition Guru web app"

# 4. Set main branch name
git branch -M main

# 5. Link to your GitHub Repository (replace YOUR_GITHUB_USERNAME with your username)
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/exhibition-guru.git

# 6. Push code to GitHub
git push -u origin main
```

---

## 🌐 Step 2: Deploy on Render

### Method A: Web Service (Recommended)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** button in the top-right corner and select **Web Service**.
3. Under **Connect a repository**, choose your `exhibition-guru` GitHub repository. *(If not visible, click "Configure account" to grant Render access)*.
4. Fill in the following deployment configuration settings:

| Setting | Value |
| :--- | :--- |
| **Name** | `exhibition-guru` *(or your preferred name)* |
| **Region** | Choose nearest (e.g., *Singapore*, *Frankfurt*, *Oregon*) |
| **Branch** | `main` |
| **Root Directory** | *(Leave blank)* |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Instance Type** | `Free` |

5. Click **Create Web Service**.

Render will start building your Python application. In 1–2 minutes, you will see `Build successful` and your live URL (e.g., `https://exhibition-guru.onrender.com`).

---

### Method B: Render Blueprint (Automatic Setup)

Because a `render.yaml` file is included in this repository:

1. Go to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Blueprint**.
3. Select your `exhibition-guru` repository.
4. Render will automatically detect `render.yaml` and pre-fill build/start commands.
5. Click **Apply** to deploy.

---

## ⚙️ Configuration Files Reference

Your project already includes the required files:

- **`Procfile`**:
  ```procfile
  web: gunicorn app:app
  ```
- **`requirements.txt`**:
  ```text
  Flask==3.0.3
  gunicorn==22.0.0
  ```
- **`render.yaml`**:
  ```yaml
  services:
    - type: web
      name: exhibition-guru
      env: python
      buildCommand: pip install -r requirements.txt
      startCommand: gunicorn app:app
      autoDeploy: true
      envVars:
        - key: PYTHON_VERSION
          value: 3.10.12
  ```

---

## 🧪 Step 3: Verify Deployment

1. Click on the generated `.onrender.com` URL provided in your Render dashboard.
2. Verify:
   - ✅ Homepage loads cleanly with styling and images.
   - ✅ Mobile view navigation menu operates smoothly.
   - ✅ Quote form submission functions.

---

## 🔒 Optional: Environment Variables (Email Notifications)

If you configure live SMTP email delivery via `config.json`, you can manage sensitive credentials safely:
1. Go to your Render Web Service dashboard.
2. Click **Environment** in the left sidebar.
3. Click **Add Environment Variable** (e.g., `SENDER_PASSWORD`).
4. Save changes. Render will automatically redeploy with the new settings.

---

## 🔄 Automatic Redeployments

Every time you commit and push new code to your GitHub `main` branch, Render will automatically trigger a build and redeploy your live website with zero downtime!
