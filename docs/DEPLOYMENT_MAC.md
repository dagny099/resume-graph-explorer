# macOS Production Deployment Guide

This guide provides step-by-step instructions for deploying Resume Explorer on macOS as a background service for personal use. This setup allows the application to run automatically on system startup and be accessed via a single URL.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Initial Setup](#initial-setup)
5. [Production Configuration](#production-configuration)
6. [Build Frontend](#build-frontend)
7. [Configure macOS Launch Agent](#configure-macos-launch-agent)
8. [Management Commands](#management-commands)
9. [Troubleshooting](#troubleshooting)
10. [Uninstallation](#uninstallation)
11. [Moving to Another Mac](#moving-to-another-mac)

---

## Overview

**Deployment Type:** Production build with macOS LaunchAgent background service

**Key Features:**
- Single URL access: `http://localhost:5005`
- Auto-starts on system boot
- Runs in background (no terminal needed)
- Serves optimized static frontend from Flask backend
- Native macOS integration via `launchd`

**What This Guide Does:**
1. Configures Flask to serve production-built frontend
2. Creates a production launch script
3. Sets up macOS LaunchAgent for auto-start
4. Builds optimized frontend bundle
5. Validates deployment

---

## Prerequisites

Before starting, ensure you have:

- [ ] macOS 10.14 or later
- [ ] Python 3.10+ installed
- [ ] Node.js 16+ and npm installed
- [ ] Git repository cloned to a permanent location
- [ ] Backend virtual environment created and dependencies installed
- [ ] Frontend dependencies installed (`npm install` in `/frontend`)
- [ ] `.env` file configured with your LLM provider API keys

**Verify Prerequisites:**

```bash
# Check Python version (should be 3.10+)
python3 --version

# Check Node.js version (should be 16+)
node --version

# Check if backend venv exists
ls backend/venv/bin/activate

# Check if frontend dependencies installed
ls frontend/node_modules

# Check if .env configured
ls backend/.env
```

---

## Architecture

### Before (Development Mode)
```
┌─────────────┐         ┌──────────────┐
│   Frontend  │         │   Backend    │
│  (Port 3000)│◄────────│  (Port 5005) │
│  Vite Dev   │  Proxy  │    Flask     │
└─────────────┘         └──────────────┘
  2 processes required
```

### After (Production Mode)
```
┌───────────────────────────────┐
│         Backend               │
│       (Port 5005)             │
│  ┌─────────────────────────┐  │
│  │  Flask API + Static     │  │
│  │  Serves /api/* + /dist  │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
  1 process, auto-started
```

---

## Initial Setup

### Step 1: Navigate to Project Root

```bash
cd /Users/bhs/PROJECTS/resume-graph-explorer
```

**Important:** Replace `/Users/bhs/PROJECTS/resume-graph-explorer` with your actual project path throughout this guide.

### Step 2: Verify Current State

```bash
# Check git status
git status

# Ensure no critical uncommitted changes
# If you have work in progress, commit or stash it
```

---

## Production Configuration

### Step 3: Update Backend to Serve Frontend

The Flask backend needs to be configured to serve the built frontend files.

**File:** `/backend/resume_explorer/api/app.py`

**Add the following code** after the `create_app()` function is defined, just before the routes are registered:

```python
def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)

    # ... existing configuration code ...

    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ============================================
    # PRODUCTION: Serve frontend static files
    # ============================================
    import os
    from flask import send_from_directory

    # Path to built frontend (dist folder)
    frontend_dist = os.path.join(
        os.path.dirname(__file__),
        '../../../frontend/dist'
    )

    # Only serve static files if dist folder exists
    if os.path.exists(frontend_dist):
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            """Serve frontend static files or index.html for SPA routing"""
            if path and os.path.exists(os.path.join(frontend_dist, path)):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

        app.logger.info(f"Serving frontend static files from: {frontend_dist}")
    else:
        app.logger.warning(f"Frontend dist folder not found at: {frontend_dist}")
    # ============================================

    # Register routes
    from resume_explorer.api import routes, websocket
    # ... rest of existing code ...
```

**Important Notes:**
- This code should be added **BEFORE** the routes are registered
- The route `@app.route('/')` will serve the frontend
- API routes (`/api/*`) will continue to work as before
- The frontend is only served if `/frontend/dist` exists

### Step 4: Create Production Launch Script

Create a script that activates the virtual environment and runs Flask in production mode.

**File:** `/scripts/run-production-mac.sh`

```bash
#!/bin/bash

#######################################
# Resume Explorer - Production Launcher
# Starts Flask backend in production mode
#######################################

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Resume Explorer (Production Mode)..."
echo "Project root: $PROJECT_ROOT"

# Navigate to backend directory
cd "$PROJECT_ROOT/backend"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found at $PROJECT_ROOT/backend/venv"
    exit 1
fi

# Set Flask environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. LLM features may not work."
fi

# Start Flask application
echo "Starting Flask server on port 5005..."
python -m resume_explorer.api.app --port 5005
```

**Make the script executable:**

```bash
chmod +x scripts/run-production-mac.sh
```

**Test the script manually:**

```bash
./scripts/run-production-mac.sh
```

Press `Ctrl+C` to stop after verifying it starts correctly.

---

## Build Frontend

### Step 5: Build Optimized Frontend Bundle

```bash
cd frontend
npm run build
```

**Expected Output:**
```
vite v4.x.x building for production...
✓ 1234 modules transformed.
dist/index.html                   x.xx kB
dist/assets/index-abc123.css     xx.xx kB
dist/assets/index-xyz789.js     xxx.xx kB
✓ built in x.xxs
```

**Verify Build:**

```bash
ls -lh frontend/dist/

# You should see:
# - index.html
# - assets/ directory with .js and .css files
# - vite.svg or other static assets
```

**Frontend Build Location:** `/frontend/dist`

**Note:** You'll need to rebuild the frontend (`npm run build`) whenever you make changes to the React code.

---

## Configure macOS Launch Agent

### Step 6: Create LaunchAgent Plist File

LaunchAgents are macOS's native way to run background services. This will make Resume Explorer start automatically when you log in.

**File:** `~/Library/LaunchAgents/com.resume-explorer.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Service identifier (must be unique) -->
    <key>Label</key>
    <string>com.resume-explorer</string>

    <!-- Command to run -->
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/bhs/PROJECTS/resume-graph-explorer/scripts/run-production-mac.sh</string>
    </array>

    <!-- Working directory -->
    <key>WorkingDirectory</key>
    <string>/Users/bhs/PROJECTS/resume-graph-explorer/backend</string>

    <!-- Start when user logs in -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Restart if process dies -->
    <key>KeepAlive</key>
    <true/>

    <!-- Log files -->
    <key>StandardOutPath</key>
    <string>/tmp/resume-explorer.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/resume-explorer-error.log</string>

    <!-- Environment variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
```

**IMPORTANT: Update Paths**

Replace `/Users/bhs/PROJECTS/resume-graph-explorer` with your actual project path:

```bash
# Find your actual path
pwd  # Run this in the project root
```

### Step 7: Install LaunchAgent

```bash
# Copy plist to LaunchAgents directory
# (It should already be there if you created it in ~/Library/LaunchAgents/)

# Load the service
launchctl load ~/Library/LaunchAgents/com.resume-explorer.plist

# Start the service
launchctl start com.resume-explorer
```

### Step 8: Verify Service is Running

```bash
# Check if service is loaded
launchctl list | grep resume-explorer

# Expected output:
# PID    Status    Label
# 12345  0         com.resume-explorer

# Check logs
tail -f /tmp/resume-explorer.log
```

**Access the application:**

Open your browser and navigate to: **http://localhost:5005**

You should see the Resume Explorer interface.

---

## Management Commands

### Start Service

```bash
launchctl start com.resume-explorer
```

### Stop Service

```bash
launchctl stop com.resume-explorer
```

### Restart Service

```bash
launchctl stop com.resume-explorer
launchctl start com.resume-explorer
```

### Unload Service (won't auto-start)

```bash
launchctl unload ~/Library/LaunchAgents/com.resume-explorer.plist
```

### Reload Service (after plist changes)

```bash
launchctl unload ~/Library/LaunchAgents/com.resume-explorer.plist
launchctl load ~/Library/LaunchAgents/com.resume-explorer.plist
```

### Check Service Status

```bash
launchctl list | grep resume-explorer
```

### View Logs

```bash
# Standard output
tail -f /tmp/resume-explorer.log

# Error output
tail -f /tmp/resume-explorer-error.log
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
cat /tmp/resume-explorer-error.log
```

**Common issues:**

1. **Virtual environment not found**
   - Verify: `ls backend/venv/bin/activate`
   - Fix: `cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

2. **Port 5005 already in use**
   - Check: `lsof -i :5005`
   - Fix: Kill the process or change port in script and plist

3. **Permissions error**
   - Fix: `chmod +x scripts/run-production-mac.sh`

4. **Path incorrect in plist**
   - Verify paths match your actual project location
   - Reload: `launchctl unload ~/Library/LaunchAgents/com.resume-explorer.plist`
   - Edit plist with correct paths
   - Reload: `launchctl load ~/Library/LaunchAgents/com.resume-explorer.plist`

### Frontend Not Loading

**Symptoms:** API works but UI shows 404 or blank page

**Diagnosis:**
```bash
# Check if dist folder exists
ls -la frontend/dist/

# Check Flask logs
tail -f /tmp/resume-explorer.log | grep "Serving frontend"
```

**Fix:**
```bash
cd frontend
npm run build
launchctl restart com.resume-explorer
```

### API Not Responding

**Check if Flask is running:**
```bash
curl http://localhost:5005/health
```

**Expected response:**
```json
{"status": "healthy"}
```

**If not responding:**
```bash
# Check service status
launchctl list | grep resume-explorer

# Check error logs
tail -f /tmp/resume-explorer-error.log
```

### LLM Features Not Working

**Symptoms:** Extraction fails or returns errors

**Check .env file:**
```bash
cat backend/.env | grep -E 'LLM_PROVIDER|API_KEY'
```

**Verify API keys are set:**
- `LLM_PROVIDER` should be `claude`, `openai`, or `ollama`
- Corresponding API key should be present
- No trailing spaces or quotes

**Restart after .env changes:**
```bash
launchctl restart com.resume-explorer
```

### Service Crashes on Boot

**Check KeepAlive setting in plist:**
- If crashes repeatedly, set `<key>KeepAlive</key><false/>` temporarily
- Check logs to diagnose root cause
- Fix issue, then re-enable `<true/>`

---

## Uninstallation

### Remove LaunchAgent

```bash
# Stop and unload service
launchctl stop com.resume-explorer
launchctl unload ~/Library/LaunchAgents/com.resume-explorer.plist

# Remove plist file
rm ~/Library/LaunchAgents/com.resume-explorer.plist

# Remove log files (optional)
rm /tmp/resume-explorer.log
rm /tmp/resume-explorer-error.log
```

### Remove Application Data

```bash
# Remove session data (if desired)
rm -rf /Users/bhs/PROJECTS/resume-graph-explorer/backend/data/sessions/
```

---

## Moving to Another Mac

### On the Old Mac

#### Step 1: Export Configuration

```bash
# Navigate to project root
cd /Users/bhs/PROJECTS/resume-graph-explorer

# Stop the service
launchctl stop com.resume-explorer
launchctl unload ~/Library/LaunchAgents/com.resume-explorer.plist

# Create backup directory
mkdir ~/resume-explorer-backup

# Copy .env file (contains API keys)
cp backend/.env ~/resume-explorer-backup/

# Optional: Backup session data
cp -r backend/data/sessions/ ~/resume-explorer-backup/sessions/

# Copy to cloud/external drive
# Option 1: Cloud
cp -r ~/resume-explorer-backup ~/Dropbox/
# Option 2: External drive
cp -r ~/resume-explorer-backup /Volumes/ExternalDrive/
```

#### Step 2: Note Your Configuration

Document any customizations:
- Custom port numbers
- Modified environment variables
- Any code changes you made

### On the New Mac

#### Step 1: Install Prerequisites

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10+
brew install python@3.10

# Install Node.js 18+
brew install node@18
```

#### Step 2: Clone Repository

```bash
# Create projects directory
mkdir -p ~/PROJECTS
cd ~/PROJECTS

# Clone repository
git clone <your-repo-url> resume-graph-explorer
cd resume-graph-explorer
```

#### Step 3: Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 4: Setup Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Build production bundle
npm run build
```

#### Step 5: Restore Configuration

```bash
# Copy .env from backup
cp ~/resume-explorer-backup/.env backend/.env

# Optional: Restore session data
mkdir -p backend/data/sessions
cp -r ~/resume-explorer-backup/sessions/* backend/data/sessions/
```

#### Step 6: Update Paths in Scripts

```bash
# Get your new project path
pwd
# Output example: /Users/newuser/PROJECTS/resume-graph-explorer

# Edit LaunchAgent plist (if you saved it)
# Update all instances of /Users/bhs/PROJECTS/resume-graph-explorer
# to your new path
```

#### Step 7: Follow Deployment Steps

Start from [Configure macOS Launch Agent](#configure-macos-launch-agent) section and complete setup.

**Quick checklist:**
- [ ] Update paths in `com.resume-explorer.plist`
- [ ] Copy plist to `~/Library/LaunchAgents/`
- [ ] Load LaunchAgent: `launchctl load ~/Library/LaunchAgents/com.resume-explorer.plist`
- [ ] Start service: `launchctl start com.resume-explorer`
- [ ] Test: Open http://localhost:5005

---

## Additional Tips

### Create Browser Bookmark

Add http://localhost:5005 to your browser favorites for quick access.

### Optional: Create Dock App

Use tools like [Fluid](https://fluidapp.com/) or [Unite](https://www.bzgapps.com/unite) to create a standalone macOS app:

1. Install Fluid or Unite
2. Create new app with URL: http://localhost:5005
3. Name it "Resume Explorer"
4. Choose an icon
5. Add to Dock

### Optional: Custom Domain

Edit `/etc/hosts` to use a custom local domain:

```bash
sudo nano /etc/hosts

# Add line:
127.0.0.1  resume.local

# Save and access via: http://resume.local:5005
```

### Updating the Application

When you pull new code from git:

```bash
# Navigate to project
cd /Users/bhs/PROJECTS/resume-graph-explorer

# Pull latest code
git pull

# Update backend dependencies (if requirements.txt changed)
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Rebuild frontend (if frontend code changed)
cd ../frontend
npm install  # Only if package.json changed
npm run build

# Restart service
launchctl restart com.resume-explorer
```

---

## Security Notes

**For Personal Use Only:**
- This setup binds to `localhost` (127.0.0.1) only
- Not accessible from other devices on your network
- No authentication/authorization required
- Suitable for single-user personal use

**If You Want Network Access:**
- Modify `app.py` to bind to `0.0.0.0`
- Add firewall rules
- Consider adding authentication
- Use HTTPS with self-signed certificates
- See `docs/DEPLOYMENT_PRODUCTION.md` for guidance (if created)

---

## Quick Reference

| Task | Command |
|------|---------|
| Access app | http://localhost:5005 |
| Start service | `launchctl start com.resume-explorer` |
| Stop service | `launchctl stop com.resume-explorer` |
| Restart service | `launchctl restart com.resume-explorer` |
| View logs | `tail -f /tmp/resume-explorer.log` |
| Check status | `launchctl list \| grep resume-explorer` |
| Rebuild frontend | `cd frontend && npm run build` |
| Manual start | `./scripts/run-production-mac.sh` |

---

## Support

For issues or questions:
- Check logs: `/tmp/resume-explorer.log` and `/tmp/resume-explorer-error.log`
- Review troubleshooting section above
- Check project documentation in `/docs`
- Review GitHub issues: [project repository]

---

**Document Version:** 1.0
**Last Updated:** 2026-01-05
**Target macOS Version:** 10.14+
**Python Version:** 3.10+
**Node.js Version:** 16+
