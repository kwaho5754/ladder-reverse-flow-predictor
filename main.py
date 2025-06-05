# main.py (load_dotenv 포함, 3줄/4줄 블럭 완전 독립 구조)
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()  # ✅ .env 환경변수 로딩 추가

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

def reverse_name(name):
    name = name.replace('좌', '@').replace('우', '좌').replace('@', '우')
    name = name.replace('홀', '@').replace('짝', '홀').replace('@', '짝')
    return name

def flip_start(block):
    return [reverse_name(block[0])] + block[1:] if block else []

def flip_odd_even(block):
    return [reverse_name(b) if '홀' in b or '짝' in b else b for b in block]

def find_top3(data, block_size):
    if len(data) < block_size + 1:
        return {}, []

    recent_block = list(reversed(data[:block_size]))
    directions = {
        "원본": lambda b: b,
        "대칭": lambda b: [reverse_name(x) for x in b],
        "시작점반전": flip_start,
        "홀짝반전": flip_odd_even,
    }

    result = {}
    for name, transform in directions.items():
        transformed = transform(recent_block)
        freq = {}
        for i in range(block_size, len(data) - block_size):
            candidate = data[i:i+block_size]
            if candidate == transformed:
                above = data[i-1] if i > 0 else None
                if above:
                    freq[above] = freq.get(above, 0) + 1
        top3 = sorted(freq.items(), key=lambda x: -x[1])[:3]
        result[name] = [{"value": k, "count": v} for k, v in top3]

    return result, recent_block

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        raw = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data

        if not raw:
            return jsonify({"error": "데이터 없음"}), 500

        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        result3, recent3 = find_top3(all_data, 3)
        result4, recent4 = find_top3(all_data, 4)

        return jsonify({
            "예측회차": round_num,
            "최근블럭3": recent3,
            "최근블럭4": recent4,
            "Top3_3줄": result3,
            "Top3_4줄": result4
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
