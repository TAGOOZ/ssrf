# SSRF Relay Server for Render

Deploy this to Render to test SSRF access to AWS metadata endpoint.

## Quick Deploy to Render

1. Go to https://dashboard.render.com/
2. Click "New" → "Web Service"
3. Connect your GitHub/GitLab OR use "Deploy from a URL"
4. Or push this folder to a GitHub repo and connect

## Manual Setup

1. Create new Web Service on Render
2. Set:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
3. Deploy!

## Usage

Once deployed at `https://your-app.onrender.com`:

```
/relay?target=http://169.254.169.254/latest/meta-data/
```
