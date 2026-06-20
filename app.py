from flask import Flask, request, jsonify
import asyncio
import binascii
import aiohttp
import requests
import json
import like_pb2
import uid_generator_pb2
import visit_count_pb2
from google.protobuf.message import DecodeError
from collections import OrderedDict

# Crypto package crash protection
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ModuleNotFoundError:
    import sys
    # Force fallback message if package is missing during initial build
    print("CRITICAL: pycryptodome module missing. Check requirements.txt")

app = Flask(__name__)

# ✅ Valid API keys
VALID_API_KEYS = {
    "ZEXXY"
}

daily_limit = 1000
used_count = 0


def load_tokens(region):
    try:
        if region == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
        elif region in {"BR", "US", "SAC", "NA"}:
            with open("token_br.json", "r") as f:
                tokens = json.load(f)
        else:
            with open("token_bd.json", "r") as f:
                tokens = json.load(f)
        return tokens
    except Exception as e:
        app.logger.error(f"Error loading tokens for region {region}: {e}")
        return None


def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Encryption error: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def direct_like_handler():
    global used_count

    if request.method == 'POST':
        data = request.get_json() or {}
        uid_str = data.get('uid') or request.args.get('uid')
        region = data.get('region') or request.args.get('region')
        key = data.get('key') or request.args.get('key')
    else:
        uid_str = request.args.get('uid')
        region = request.args.get('region')
        key = request.args.get('key')

    if not uid_str and not key:
        return jsonify({
            "status": "online",
            "message": "Free Fire Likes API is fully running on the main route!"
        })

    if not uid_str or not region or not key:
        return jsonify({"error": "Missing parameters. Required: uid, region, key", "status": 0}), 400

    if key not in VALID_API_KEYS:
        return jsonify({"error": "Invalid API key", "status": 0}), 403

    try:
        uid = int(uid_str)
    except ValueError:
        return jsonify({"error": "UID must be a number", "status": 0}), 400

    region = region.upper()
    tokens = load_tokens(region)
    if not tokens:
        return jsonify({"error": f"Failed to load tokens for region {region}", "status": 0}), 500

    async def process_request():
        global used_count
        status = 0
        like_given = 0
        before_like = 0
        after_like = 0
        player_name = "FF_Player"
        player_level = "N/A"
        player_region = region
        player_uid = uid_str

        l_msg = like_pb2.like()
        l_msg.uid = uid
        l_msg.region = region
        serialized_l = l_msg.SerializeToString()

        uid_gen = uid_generator_pb2.uid_generator()
        uid_gen.saturn_ = uid
        uid_gen.garena = uid
        serialized_uid = uid_gen.SerializeToString()

        enc_l = encrypt_message(serialized_l)
        enc_uid = encrypt_message(serialized_uid)

        if not enc_l or not enc_uid:
            return jsonify({"error": "Encryption failed. Library not ready.", "status": 0}), 500

        headers = {
            'Content-Type': 'application/json',
            'Connection': 'keep-alive'
        }

        async with aiohttp.ClientSession() as session:
            for token_entry in tokens:
                token = token_entry.get("token")
                if not token:
                    continue

                headers['Release'] = token

                url1 = f"https://client.freefiremobile.com/api/v1/like?bytes={enc_l}"
                try:
                    async with session.get(url1, headers=headers, timeout=5) as resp1:
                        if resp1.status != 200:
                            continue
                except Exception:
                    continue

                url2 = f"https://client.freefiremobile.com/api/v1/visit_count?bytes={enc_uid}"
                try:
                    async with session.get(url2, headers=headers, timeout=5) as resp2:
                        if resp2.status == 200:
                            body = await resp2.read()
                            try:
                                after = visit_count_pb2.Info()
                                after.ParseFromString(body)
                                status = 1
                                like_given += 1
                                
                                info_obj = getattr(after, 'AccountInfo', None)
                                if info_obj:
                                    after_like = getattr(info_obj, 'Likes', 1)
                                    before_like = max(after_like - 1, 0)
                                    player_name = getattr(info_obj, 'PlayerNickname', getattr(info_obj, 'Nickname', 'FF_Player'))
                                    player_level = str(getattr(info_obj, 'Levels', '65'))
                                    player_region = str(getattr(info_obj, 'PlayerRegion', region))
                                    player_uid = str(getattr(info_obj, 'UID', uid_str))
                                break
                            except DecodeError:
                                pass
                except Exception:
                    continue

            if status == 1:
                used_count += 1

            remaining = max(daily_limit - used_count, 0)

            result = OrderedDict([
                ("LikesGivenByAPI", like_given),
                ("LikesafterCommand", after_like),
                ("LikesbeforeCommand", before_like),
                ("PlayerNickname", player_name),
                ("Level", player_level),
                ("Region", player_region),
                ("UID", player_uid),
                ("status", status),
                ("daily_limit", daily_limit),
                ("used", used_count),
                ("remaining", remaining)
            ])

            return app.response_class(
                response=json.dumps(result, separators=(',', ':')),
                status=200,
                mimetype='application/json'
            )

    try:
        return asyncio.run(process_request())
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e), "status": 0}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
