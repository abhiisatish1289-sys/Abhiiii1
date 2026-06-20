from flask import Flask, request, jsonify
import asyncio
import aiohttp
import json
from collections import OrderedDict

app = Flask(__name__)

VALID_API_KEYS = {"ZEXXY"}
daily_limit = 1000
used_count = 0

# Test endpoint to check if API is alive
@app.route('/remain', methods=['GET'])
def remain_info():
    global used_count
    remaining = max(daily_limit - used_count, 0)
    return jsonify({
        "daily_limit": daily_limit,
        "remaining": remaining,
        "used": used_count
    })

# Main endpoint where Bot sends request
@app.stdout_access_handler = None # ignore log
@app.route('/api/like', methods=['POST', 'GET'])
def handle_like():
    global used_count
    
    # Bot se data nikalna (chaye query params ho ya JSON)
    if request.method == 'POST':
        data = request.get_json() or {}
        uid = data.get('uid') or request.args.get('uid')
        region = data.get('region') or request.args.get('region')
        key = data.get('key') or request.args.get('key')
    else:
        uid = request.args.get('uid')
        region = request.args.get('region')
        key = request.args.get('key')

    if not uid or not region or not key:
        return jsonify({"error": "Missing parameters (uid, region, key required)", "status": 0}), 400

    if key not in VALID_API_KEYS:
        return jsonify({"error": "Invalid API Key", "status": 0}), 403

    # Simulated Free Fire Like Success Response format matching your old code
    used_count += 1
    remaining = max(daily_limit - used_count, 0)
    
    result = OrderedDict([
        ("LikesGivenByAPI", 1),
        ("LikesafterCommand", 999),
        ("LikesbeforeCommand", 998),
        ("PlayerNickname", "FF_Player"),
        ("Level", "65"),
        ("Region", region),
        ("UID", uid),
        ("status", 1),
        ("daily_limit", daily_limit),
        ("used", used_count),
        ("remaining", remaining)
    ])
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
