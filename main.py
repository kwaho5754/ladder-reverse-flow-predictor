# ⬇️ main.py — 3~6줄 블럭 + 흐름종합 + 흐름반전 통합 예측 API

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

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        raw = requests.get(URL).json()
        data = raw[-288:]
        mode = request.args.get("mode", "3block")
        round_num = int(raw[-1]['date_round']) + 1

        if mode.endswith("block"):
            size = int(mode[0])
            recent_block = [convert(d) for d in data[-size:]]
            all_blocks = [convert(d) for d in data]
            candidates = []
            for i in range(len(all_blocks) - size + 1):
                block = all_blocks[i:i+size]
                if block == recent_block:
                    if i - 1 >= 0:
                        candidates.append(convert(data[i - 1]))
                    if i + size < len(data):
                        candidates.append(convert(data[i + size]))
            freq = Counter(candidates)
            top3 = [
                {"값": val, "횟수": cnt} for val, cnt in freq.most_common(3)
            ]
            while len(top3) < 3:
                top3.append({"값": "❌ 없음", "횟수": 0})
            return jsonify({"예측회차": round_num, "Top3": top3})

        elif mode == "flow_mix":
            def generate_variants_for_block(block):
                variants = {"원본": block, "대칭시작": [], "대칭홀짝": [], "대칭둘다": []}
                for b in block:
                    s, c, o = parse_block(b)
                    variants["대칭시작"].append(f"{flip_start(s)}{c}{o}")
                    variants["대칭홀짝"].append(f"{s}{c}{flip_parity(o)}")
                    variants["대칭둘다"].append(f"{flip_start(s)}{c}{flip_parity(o)}")
                return variants

            def analyze_flow(data):
                flow = {"시작방향": [], "줄수": [], "홀짝": []}
                for d in data[-5:]:
                    s, c, o = parse_block(convert(d))
                    flow["시작방향"].append(s)
                    flow["줄수"].append(int(c))
                    flow["홀짝"].append(o)
                불안정도 = sum(1 for i in range(4) if flow["줄수"][i] != flow["줄수"][i+1]) / 4
                return {**flow, "불안정도": round(불안정도, 2)}

            def score_blocks(data, size, reverse=False):
                if reverse:
                    data = list(reversed(data))
                recent = [convert(d) for d in data[:size]]
                variants = generate_variants_for_block(recent)
                all_data = [convert(d) for d in data]
                scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
                for i in range(len(all_data) - size):
                    past = all_data[i:i+size]
                    target_idx = i + size if reverse else i - 1
                    if target_idx < 0 or target_idx >= len(data): continue
                    target = convert(data[target_idx])
                    for key, variant in variants.items():
                        if past == variant:
                            weight = {"원본": 3, "대칭시작": 2, "대칭홀짝": 2, "대칭둘다": 1}[key]
                            scores[target]["score"] += weight
                            scores[target]["detail"][key] += 1
                return scores

            def detect_recent_flow(data, n=20):
                return [convert(d) for d in data[-n:]]

            def detect_reverse_pattern_match(data, recent_flow):
                all_data = [convert(d) for d in data]
                reverse_scores = defaultdict(int)
                length = len(recent_flow)
                for i in range(len(all_data) - length - 1):
                    if all_data[i:i+length] == recent_flow:
                        next_value = all_data[i+length]
                        reverse_scores[next_value] += 1
                return reverse_scores

            def get_most_common_flow_item(data):
                last = convert(data[-1])
                return parse_block(last)

            flow_info = analyze_flow(data)
            instability = flow_info["불안정도"]
            scores = defaultdict(lambda: {"score": 0, "detail": defaultdict(int)})
            for size in range(3, 8):
                for reverse in [False, True]:
                    result = score_blocks(data, size, reverse)
                    for k, v in result.items():
                        scores[k]["score"] += v["score"]
                        for dkey, dval in v["detail"].items():
                            scores[k]["detail"][dkey] += dval

            recent_flow = detect_recent_flow(data, 20)
            reverse_boost = detect_reverse_pattern_match(data, recent_flow)
            flow_start, flow_line, flow_oe = get_most_common_flow_item(data)

            scored_items = []
            for name, info in scores.items():
                s, c, o = parse_block(name)
                match_score = 0
                if s == flow_start: match_score += 1
                if int(c) == int(flow_line): match_score += 1
                if o == flow_oe: match_score += 1
                flow_match_bonus = match_score * 1.0
                reverse_bonus = reverse_boost.get(name, 0) * 2
                adjusted_score = round((info["score"] + reverse_bonus + flow_match_bonus) * (1 - instability * 0.5), 2)
                scored_items.append((name, adjusted_score, info["detail"]))

            seen = set()
            top5 = []
            for name, adj_score, details in sorted(scored_items, key=lambda x: x[1], reverse=True):
                if name not in seen and adj_score > 0:
                    top5.append({"값": name, "점수": adj_score, "근거": dict(details)})
                    seen.add(name)
                if len(top5) == 5:
                    break
            if not top5:
                top5 = [{"값": "❌ 예측 불가 (불안정도 최대)", "점수": 0, "근거": {}}]
            return jsonify({"예측회차": round_num, "Top5": top5, "흐름해석": flow_info})

        elif mode == "reverse_only":
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

            base_scores = defaultdict(lambda: {'score': 0, 'detail': defaultdict(int)})
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
                            base_scores[target]['score'] += weight
                            base_scores[target]['detail'][key] += 1

            flow = analyze_flow(data)
            latest = flow['줄수'][-1]
            for k in base_scores:
                _, c, _ = parse_block(k)
                if int(c) != latest:
                    base_scores[k]['score'] += 1.5
                base_scores[k]['score'] += flow['불안정도'] * 1.5

            result = sorted(base_scores.items(), key=lambda x: -x[1]['score'])[:5]
            output = []
            for i, (val, scoreinfo) in enumerate(result):
                output.append({
                    "순위": f"{i+1}위", "예측값": val,
                    "점수": round(scoreinfo['score'], 2),
                    "상세": dict(scoreinfo['detail'])
                })
            return jsonify({"예측회차": round_num, "Top5": output, "흐름해석": flow})

        else:
            return jsonify({"error": "지원하지 않는 분석 모드입니다."})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
