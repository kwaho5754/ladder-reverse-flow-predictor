# main.py (흐름 반전 기반 예측 시스템)

from flask import Flask, jsonify
from flask_cors import CORS
import requests
from collections import defaultdict, Counter

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"


def convert(entry):
    start = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    parity = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{start}{count}{parity}"


def flip_start(s): return '우' if s == '좌' else '좌'
def flip_parity(p): return '짝' if p == '홀' else '홀'

def parse_block(s): return s[0], s[1], s[2]


def generate_variants(block):
    variants = defaultdict(list)
    for b in block:
        s, c, p = parse_block(b)
        variants['원본'].append(b)
        variants['반시작'].append(flip_start(s) + c + p)
        variants['반홀짝'].append(s + c + flip_parity(p))
        variants['반전체'].append(flip_start(s) + c + flip_parity(p))
    return variants


def analyze_flow(data):
    flow = {'시작방향': [], '줄수': [], '홀짝': []}
    recent = data[:5]
    for entry in recent:
        s, c, p = parse_block(convert(entry))
        flow['시작방향'].append(s)
        flow['줄수'].append(int(c))
        flow['홀짝'].append(p)
    unstable = sum(1 for i in range(4) if flow['줄수'][i] != flow['줄수'][i+1]) / 4
    flow['불안정도'] = round(unstable, 2)
    return flow


def predict(data):
    patterns = defaultdict(lambda: {'score': 0, 'detail': defaultdict(int)})
    for size in range(3, 8):
        recent = [convert(d) for d in data[:size]]
        variants = generate_variants(recent)
        all_data = [convert(d) for d in data]
        for i in range(len(data) - size):
            prev = all_data[i:i+size]
            target_idx = i - 1
            if target_idx < 0:
                continue
            target = all_data[target_idx]
            for key, block in variants.items():
                if prev == block:
                    weight = {'원본': 2.0, '반시작': 3.0, '반홀짝': 3.0, '반전체': 4.0}[key]
                    patterns[target]['score'] += weight
                    patterns[target]['detail'][key] += 1
    return patterns


@app.route("/predict")
def predict_route():
    raw = requests.get(URL).json()
    data = raw[:288]
    flow = analyze_flow(data)
    base_scores = predict(data)

    # 흐름 반대 보정 적용
    latest = flow['줄수'][-1]
    reversed_bias = []
    for k in base_scores:
        _, c, _ = parse_block(k)
        if int(c) != latest:
            base_scores[k]['score'] += 1.5  # 반전된 줄수에 보정
            reversed_bias.append(k)

    # 불안정도 보정
    for k in base_scores:
        base_scores[k]['score'] += flow['불안정도'] * 1.5

    result = sorted(base_scores.items(), key=lambda x: -x[1]['score'])[:5]
    output = []
    for i, (val, scoreinfo) in enumerate(result):
        output.append({
            "순위": f"{i+1}위",
            "예측값": val,
            "점수": round(scoreinfo['score'], 2),
            "상세": dict(scoreinfo['detail'])
        })

    return jsonify({
        "예측 회차": int(raw[0]['date_round']) + 1,
        "Top5": output,
        "흐름 해석": flow
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
