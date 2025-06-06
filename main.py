# ✅ main.py - 블럭 없이 3가지 예측 방식 (메타흐름, 주기패턴, 짝수위치)
from flask import Flask, jsonify, request, send_from_directory
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
    if rate < 0.3:
        # 변화가 적다 → 반전 가능성 → 적게 나온 값 추정
        total = sum(counter.values())
        score_map = {k: 1 - (v/total) for k, v in counter.items()}
        return max(score_map.items(), key=lambda x: x[1])[0]
    else:
        # 변화 많음 → 많이 나온 값 추정
        return counter.most_common(1)[0][0]

def periodic_pattern_predict(data, offsets=[5,13]):
    score = defaultdict(int)
    for offset in offsets:
        for i in range(offset, len(data)):
            if data[i] == data[i-offset]:
                score[data[i]] += 1
    return max(score.items(), key=lambda x: x[1])[0] if score else "❌ 없음"

def even_line_predict(data, recent_size=100):
    even_lines = [data[i] for i in range(0, min(len(data), recent_size), 2)]
    counter = Counter(even_lines)
    return counter.most_common(1)[0][0] if counter else "❌ 없음"

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

        return jsonify({
            "예측회차": round_num,
            "메타흐름예측": meta,
            "주기패턴예측": repeat,
            "짝수위치예측": even
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
