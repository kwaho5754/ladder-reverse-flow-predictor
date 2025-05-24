# ⬇️ main.py — 3~6block 원본 + 대칭(_mirror), flow_mix 유지, 상단값만 예측 적용

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os
from collections import defaultdict, Counter

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s): return s[0], s[1], s[2]
def flip_start(s): return '우' if s == '좌' else '좌'
def flip_parity(p): return '짝' if p == '홀' else '홀'

def make_mirror(block):
    mirrored = []
    for b in block:
        s, c, o = parse_block(b)
        mirrored.append(f"{flip_start(s)}{c}{flip_parity(o)}")
    return mirrored

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

        if mode.endswith("block") or mode.endswith("mirror"):
            size = int(mode[0])
            recent_block = [convert(d) for d in data[-size:]]
            if mode.endswith("mirror"):
                recent_block = make_mirror(recent_block)

            all_blocks = [convert(d) for d in data]
            candidates = []
            for i in range(len(all_blocks) - size + 1):
                block = all_blocks[i:i+size]
                if block == recent_block:
                    if i - 1 >= 0:
                        candidates.append(convert(data[i - 1]))

            freq = Counter(candidates)
            top3 = [{"값": val, "횟수": cnt} for val, cnt in freq.most_common(3)]
            while len(top3) < 3:
                top3.append({"값": "❌ 없음", "횟수": 0})
            return jsonify({"예측회차": round_num, "Top3": top3})

        elif mode == "flow_mix":
            scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
            for size in range(3, 7):
                recent_block = [convert(d) for d in data[-size:]]
                all_blocks = [convert(d) for d in data]
                variants = {
                    "대칭시작": [f"{flip_start(s)}{c}{o}" for s, c, o in map(parse_block, recent_block)],
                    "대칭홀짝": [f"{s}{c}{flip_parity(o)}" for s, c, o in map(parse_block, recent_block)],
                    "대칭둘다": [f"{flip_start(s)}{c}{flip_parity(o)}" for s, c, o in map(parse_block, recent_block)]
                }
                for i in range(len(all_blocks) - size + 1):
                    past_block = all_blocks[i:i+size]
                    for key, pattern in variants.items():
                        if past_block == pattern:
                            if i - 1 >= 0:
                                target = convert(data[i - 1])
                                weight = {"대칭시작": 2, "대칭홀짝": 2, "대칭둘다": 1}[key]
                                scores[target]["score"] += weight
                                scores[target]["detail"][key] += 1

            sorted_scores = sorted(scores.items(), key=lambda x: -x[1]['score'])[:5]
            result = []
            for val, info in sorted_scores:
                result.append({
                    "값": val,
                    "점수": round(info['score'], 2),
                    "근거": dict(info['detail'])
                })
            if not result:
                result = [{"값": "❌ 없음", "점수": 0, "근거": {}}]
            return jsonify({"예측회차": round_num, "Top5": result})

        else:
            return jsonify({"error": "지원하지 않는 분석 모드입니다."})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
