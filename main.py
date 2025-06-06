# ✅ main.py - 예측 12개 기반 고정 Top3 구조
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter, defaultdict

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 📘 변환 함수
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

# ✅ 기존 방식 + 추가 방식 총 12개 예측 함수
def meta_flow_predict(data):
    counter = Counter(data[:100])
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.2 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def periodic_pattern_predict(data):
    score = defaultdict(int)
    for offset in [5,13]:
        for i in range(offset, len(data)):
            if data[i] == data[i-offset]:
                score[data[i]] += 1
    return max(score, key=score.get) if score else '❌ 없음'

def even_line_predict(data):
    even_lines = [data[i] for i in range(0, min(len(data), 100), 2)]
    counter = Counter(even_lines)
    total = sum(counter.values())
    score_map = {k: 1 - (v/total)**1.1 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

def low_frequency_predict(data):
    recent = data[:50]
    counter = Counter(recent)
    total = sum(counter.values())
    score_map = {k: (1 - (v / total))**1.5 for k, v in counter.items()}
    return max(score_map, key=score_map.get)

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
    result += '우' if bias['좌'] > 21 else '좌' if bias['우'] > 21 else '좌'
    result += '4' if bias['3'] > 21 else '3' if bias['4'] > 21 else '3'
    result += '짝' if bias['홀'] > 21 else '홀' if bias['짝'] > 21 else '홀'
    return result

def volatility_predict(data):
    recent = data[:30]
    diffs = [1 if recent[i] != recent[i+1] else 0 for i in range(len(recent)-1)]
    rate = sum(diffs) / len(diffs)
    counter = Counter(recent)
    if rate < 0.3:
        score_map = {k: 1 - (v/sum(counter.values())) for k, v in counter.items()}
        return max(score_map, key=score_map.get)
    return counter.most_common(1)[0][0]

# 🔁 추가 예측 방식

def trend_bias_predict(data):
    recent = data[:30]
    counter = Counter(recent)
    for key, val in counter.items():
        if val > 18:
            return key
    return '❌ 없음'

def start_position_predict(data):
    recent = data[:40]
    left = sum(1 for d in recent if d.startswith('좌'))
    right = len(recent) - left
    return '좌3홀' if left > right else '우4짝'

def odd_even_flow_predict(data):
    recent = data[:30]
    flow = ''.join(['1' if '홀' in x else '0' for x in recent])
    if flow.endswith('1010'): return '좌3홀'
    if flow.endswith('0101'): return '우4짝'
    return '좌4홀'

def block_tail_predict(data):
    tail = data[5:35]  # 중간구간만 보기
    counter = Counter(tail)
    return counter.most_common(1)[0][0] if counter else '❌ 없음'

# ✅ Top3 고정 알고리즘
PRIORITY = {'좌삼짝': 0, '우삼홀': 1, '좌사홀': 2, '우사짝': 3, '❌ 없음': 99}

def fixed_top3(predictions):
    norm = [normalize(p) for p in predictions]
    count = Counter(norm)
    # 사전순 우선 정렬 고정
    sorted_items = sorted(count.items(), key=lambda x: (-x[1], PRIORITY.get(x[0], 99)))
    return [item[0] for item in sorted_items[:3]]

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

        predictions = [
            meta_flow_predict(all_data),
            periodic_pattern_predict(all_data),
            even_line_predict(all_data),
            low_frequency_predict(all_data),
            reverse_bias_predict(all_data),
            volatility_predict(all_data),
            trend_bias_predict(all_data),
            start_position_predict(all_data),
            odd_even_flow_predict(all_data),
            block_tail_predict(all_data),
        ]

        top3_final = fixed_top3(predictions)

        return jsonify({
            "예측회차": round_num,
            "Top3최종예측": top3_final
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)