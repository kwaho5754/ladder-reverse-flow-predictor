# ✅ main_top3.py – 6개 예측 기반 Top3 최종 예측 출력 추가
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

def normalize(value):
    if '좌3짝' in value: return '좌삼짝'
    if '우3홀' in value: return '우삼홀'
    if '좌4홀' in value: return '좌사홀'
    if '우4짝' in value: return '우사짝'
    return '❌ 없음'

def meta_flow_predict(data):
    counter = Counter(data[:100])
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.2 for k, v in counter.items()}
    top3 = sorted(score_map.items(), key=lambda x: -x[1])[:3]
    return top3[0][0] if top3 else "❌ 없음"

def periodic_pattern_predict(data):
    score = defaultdict(int)
    for offset in [5,13]:
        for i in range(offset, len(data)):
            if data[i] == data[i-offset]:
                score[data[i]] += 1
    if not score: return "❌ 없음"
    return sorted(score.items(), key=lambda x: -x[1])[0][0]

def even_line_predict(data):
    even_lines = [data[i] for i in range(0, min(len(data), 100), 2)]
    counter = Counter(even_lines)
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.1 for k, v in counter.items()}
    return sorted(score_map.items(), key=lambda x: -x[1])[0][0]

def low_frequency_predict(data):
    recent = data[:50]
    counter = Counter(recent)
    score_map = {k: (1 - (v / sum(counter.values())))**1.5 for k, v in counter.items()}
    return sorted(score_map.items(), key=lambda x: -x[1])[0][0]

def reverse_bias_predict(data):
    recent = data[:30]
    bias = {'좌': 0, '우': 0, '홀': 0, '짝': 0, '3': 0, '4': 0}
    for d in recent:
        if d.startswith('좌'): bias['좌'] += 1
        if d.startswith('우'): bias['우'] += 1
        if '홀' in d: bias['홀'] += 1
        if '짝' in d: bias['짝'] += 1
        if '3' in d: bias['3'] += 1
        if '4' in d: bias['4'] += 1
    result = ''
    result += '우' if bias['좌'] > 21 else '좌' if bias['우'] > 21 else random.choice(['좌','우'])
    result += '4' if bias['3'] > 21 else '3' if bias['4'] > 21 else random.choice(['3','4'])
    result += '짝' if bias['홀'] > 21 else '홀' if bias['짝'] > 21 else random.choice(['홀','짝'])
    return result

def volatility_predict(data):
    recent = data[:30]
    diffs = [1 if recent[i] != recent[i+1] else 0 for i in range(len(recent)-1)]
    rate = sum(diffs) / len(diffs)
    counter = Counter(recent)
    score_map = {k: 1 - (v/sum(counter.values())) for k, v in counter.items()} if rate < 0.3 else counter
    return sorted(score_map.items(), key=lambda x: -x[1])[0][0]

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

        mapped = [normalize(v) for v in [meta, repeat, even, low, reverse, vol]]
        top3_final = [x[0] for x in Counter(mapped).most_common(3)]

        return jsonify({
            "예측회차": round_num,
            "메타흐름예측": meta,
            "주기패턴예측": repeat,
            "짝수위치예측": even,
            "중복억제예측": low,
            "비대칭반전예측": reverse,
            "진폭예측": vol,
            "Top3최종예측": top3_final
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)