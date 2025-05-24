# ⬇️ main.py — 블럭 매칭 시 상단값만 예측값으로 사용

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

        if mode.endswith("block"):
            size = int(mode[0])
            recent_block = [convert(d) for d in data[-size:]]
            all_blocks = [convert(d) for d in data]
            candidates = []
            for i in range(len(all_blocks) - size + 1):
                block = all_blocks[i:i+size]
                if block == recent_block:
                    if i - 1 >= 0:
                        candidates.append(convert(data[i - 1]))  # ✅ 상단값만 사용
            freq = Counter(candidates)
            top3 = [
                {"값": val, "횟수": cnt} for val, cnt in freq.most_common(3)
            ]
            while len(top3) < 3:
                top3.append({"값": "❌ 없음", "횟수": 0})
            return jsonify({"예측회차": round_num, "Top3": top3})

        elif mode in ["flow_mix", "reverse_only"]:
            return jsonify({
                "예측회차": round_num,
                "Top5": [{"값": "❌ 흐름 예측 제거됨", "점수": 0, "근거": {}}]
            })

        else:
            return jsonify({"error": "지원하지 않는 분석 모드입니다."})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
