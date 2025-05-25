# ✅ main.py — 시작점 반전 / 홀짝 반전 블럭 기반 예측 (3~6줄)

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os
from collections import Counter

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

# 🔁 블럭 변환 함수들

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_start_only(block):
    return [
        ('우' if s == '좌' else '좌') + c + o
        for s, c, o in map(parse_block, block)
    ]

def flip_parity_only(block):
    return [
        s + c + ('짝' if o == '홀' else '홀')
        for s, c, o in map(parse_block, block)
    ]

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        raw = requests.get(URL).json()
        data = raw[-288:]
        mode = request.args.get("mode", "3block")
        round_num = int(raw[0]['date_round']) + 1

        size = int(mode[0])
        recent_block = [convert(d) for d in data[-size:]][::-1]

        if mode.endswith("start"):
            recent_block = flip_start_only(recent_block)
        elif mode.endswith("parity"):
            recent_block = flip_parity_only(recent_block)

        all_blocks = [convert(d) for d in data]
        candidates = []
        for i in range(len(all_blocks) - size + 1):
            block = all_blocks[i:i+size]
            if block == recent_block:
                if i - 1 >= 0:
                    candidates.append(all_blocks[i - 1])

        freq = Counter(candidates)
        top3 = [{"값": val, "횟수": cnt} for val, cnt in freq.most_common(3)]
        while len(top3) < 3:
            top3.append({"값": "❌ 없음", "횟수": 0})

        return jsonify({"예측회차": round_num, "Top3": top3})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
