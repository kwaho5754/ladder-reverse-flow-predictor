# ✅ main.py — 흐름 기반 블럭 매칭 방식 적용

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [
        ('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀')
        for s, c, o in map(parse_block, block)
    ]

def find_flow_match(block, full_data, reverse=False, use_bottom=False):
    block_len = len(block)
    indices = reversed(range(len(full_data) - block_len)) if reverse else range(len(full_data) - block_len)
    for i in indices:
        candidate = full_data[i:i+block_len]
        if candidate == block:
            if reverse:
                pred_index = i + block_len if use_bottom and i + block_len < len(full_data) else -1
            else:
                pred_index = i - 1 if not use_bottom and i - 1 >= 0 else -1
            pred = full_data[pred_index] if 0 <= pred_index < len(full_data) else "❌ 없음"
            return pred, ">".join(block)
    return "❌ 없음", ">".join(block)

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        raw = requests.get(URL).json()
        data = raw[-288:]
        mode = request.args.get("mode", "3block_orig")
        round_num = int(raw[0]['date_round']) + 1

        # 블럭 크기 (3~6)
        size = int(mode[0])
        recent_flow = [convert(d) for d in data[-size:]][::-1]
        all_data = [convert(d) for d in data]

        # 방향 및 대칭 판단
        is_flip = "flip" in mode
        is_reverse = "rev" in mode

        # 블럭 변환
        if is_flip:
            flow = flip_full(recent_flow)
        else:
            flow = recent_flow

        if is_reverse:
            flow = flow[::-1]

        result, blk = find_flow_match(flow, all_data, reverse=is_reverse, use_bottom=is_reverse)

        return jsonify({
            "예측회차": round_num,
            "예측값": result,
            "블럭": blk
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
