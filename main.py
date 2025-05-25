# ✅ main.py — 예측값과 사용 블럭 구조 반환 (블럭 파생 분석용)

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

def find_prediction(block, all_blocks, reverse=False, use_bottom=False):
    indices = reversed(range(len(all_blocks) - len(block))) if reverse else range(len(all_blocks) - len(block))
    for i in indices:
        if all_blocks[i:i+len(block)] == block:
            pred = all_blocks[i + len(block)] if use_bottom and i + len(block) < len(all_blocks) else (
                all_blocks[i - 1] if not use_bottom and i - 1 >= 0 else "❌ 없음"
            )
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
        mode = request.args.get("mode", "3block")
        round_num = int(raw[0]['date_round']) + 1

        size = int(mode[0])
        recent_block = [convert(d) for d in data[-size:]][::-1]
        flipped_block = flip_full(recent_block)[::-1]
        all_blocks = [convert(d) for d in data]

        if mode.endswith("orig"):
            result, blk = find_prediction(recent_block, all_blocks, reverse=False, use_bottom=False)
        elif mode.endswith("flip"):
            result, blk = find_prediction(flipped_block, all_blocks, reverse=False, use_bottom=False)
        elif mode.endswith("orig_rev"):
            result, blk = find_prediction(recent_block, all_blocks, reverse=True, use_bottom=True)
        elif mode.endswith("flip_rev"):
            result, blk = find_prediction(flipped_block, all_blocks, reverse=True, use_bottom=True)
        else:
            result, blk = "❌ 없음", ">".join(recent_block)

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
