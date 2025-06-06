# ✅ main.py – 예측 6가지 방식 전체 적용 (3+3 구조)
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict
import random

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def meta_flow_predict(data, recent_size=100):
    recent = data[:recent_size]
    diffs = [1 if recent[i] != recent[i+1] else 0 for i in range(len(recent)-1)]
    rate = sum(diffs) / len(diffs) if diffs else 0
    counter = Counter(recent)
    total = sum(counter.values())

    score_map = {k: 1 - (v/total)**1.2 for k, v in counter.items()}
    if len(set(recent[:5])) == 1:
        score_map[recent[0]] = 0

    top3 = sorted(score_map.items(), key=lambda x: -x[1])[:3]
    values, weights = zip(*top3) if top3 else (["❌ 없음"], [1])
    return random.choices(values, weights=weights)[0]

def periodic_pattern_predict(data, offsets=[5,13]):
    score = defaultdict(int)
    for offset in offsets:
        for i in range(offset, len(data)):
            if data[i] == data[i-offset]:
                score[data[i]] += 1

    if not score:
        return "❌ 없음"

    total = sum(score.values())
    score_map = {k: v / total for k, v in score.items()}
    top3 = sorted(score_map.items(), key=lambda x: -x[1])[:3]
    values, weights = zip(*top3) if top3 else (["❌ 없음"], [1])
    return random.choices(values, weights=weights)[0]

def even_line_predict(data, recent_size=100):
    even_lines = [data[i] for i in range(0, min(len(data), recent_size), 2)]
    counter = Counter(even_lines)
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.1 for k, v in counter.items()}
    top3 = sorted(score_map.items(), key=lambda x: -x[1])[:3]
    values, weights = zip(*top3) if top3 else (["❌ 없음"], [1])
    return random.choices(values, weights=weights)[0]

def low_frequency_predict(data, window=50):
    recent = data[:window]
    counter = Counter(recent)
    total = sum(counter.values())
    score_map = {k: (1 - (v / total))**1.5 for k, v in counter.items()}
    top3 = sorted(score_map.items(), key=lambda x: -x[1])[:3]
    values, weights = zip(*top3)
    return random.choices(values, weights=weights)[0]

def reverse_bias_predict(data, window=30):
    recent = data[:window]
    bias = {'좌': 0, '우': 0, '홀': 0, '짝': 0, '3': 0, '4': 0}
    for d in recent:
        if d.startswith('좌'): bias['좌'] += 1
        if d.startswith('우'): bias['우'] += 1
        if '홀' in d: bias['홀'] += 1
        if '짝' in d: bias['짝'] += 1
        if '3' in d: bias['3'] += 1
        if '4' in d: bias['4'] += 1
    result = ''
    if bias['좌'] > window * 0.7: result += '우'
    elif bias['우'] > window * 0.7: result += '좌'
    else: result += random.choice(['좌', '우'])
    if bias['3'] > window * 0.7: result += '4'
    elif bias['4'] > window * 0.7: result += '3'
    else: result += random.choice(['3', '4'])
    if bias['홀'] > window * 0.7: result += '짝'
    elif bias['짝'] > window * 0.7: result += '홀'
    else: result += random.choice(['홀', '짝'])
    return result

def volatility_predict(data, window=30):
    recent = data[:window]
    diffs = [1 if recent[i] != recent[i+1] else 0 for i in range(len(recent)-1)]
    rate = sum(diffs) / len(diffs)
    counter = Counter(recent)
    if rate < 0.3:
        total = sum(counter.values())
        score_map = {k: 1 - (v/total) for k, v in counter.items()}
    else:
        score_map = {k: v for k, v in counter.items()}
    top = sorted(score_map.items(), key=lambda x: -x[1])[0][0]
    return top

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/meta_predict")
def meta_predict():
    try:
        response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute()
        raw = response.data
        all_data = [convert(d) for d in raw]
        round_num = int(raw[0]["date_round"]) + 1

        meta = meta_flow_predict(all_data)
        repeat = periodic_pattern_predict(all_data)
        even = even_line_predict(all_data)
        low = low_frequency_predict(all_data)
        reverse = reverse_bias_predict(all_data)
        vol = volatility_predict(all_data)

        return jsonify({
            "예측회차": round_num,
            "메타흐름예측": meta,
            "주기패턴예측": repeat,
            "짝수위치예측": even,
            "중복억제예측": low,
            "비대칭반전예측": reverse,
            "진폭예측": vol
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)