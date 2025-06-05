# ✅ 최종 수정본 main.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os

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

def reverse_name(name):
    name = name.replace('좌', '@').replace('우', '좌').replace('@', '우')
    name = name.replace('홀', '@').replace('짝', '홀').replace('@', '짝')
    return name

def flip_start(block):
    return [reverse_name(block[0])] + block[1:] if block else []

def flip_odd_even(block):
    return [reverse_name(b) if '홀' in b or '짝' in b else b for b in block]

def rotate_block(block):
    return list(reversed([reverse_name(b) for b in block]))

def find_top3(data, block_size, rotate=False):
    if len(data) < block_size + 1:
        return {}, []

    recent_block = data[0:block_size]
    if rotate:
        recent_block = rotate_block(recent_block)

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
        for i in range(1, len(data) - block_size):
            candidate = data[i:i+block_size]
            if candidate == transformed:
                top = data[i - 1] if i > 0 else None
                if top:
                    freq[top] = freq.get(top, 0) + 1
        top3 = sorted(freq.items(), key=lambda x: -x[1])[:3]
        result[name] = [{"value": k, "count": v} for k, v in top3]

    return result, recent_block

def find_all_first_matches(data, block_sizes):
    recent_blocks = {n: data[0:n] for n in block_sizes}
    used_positions = set()
    results = {}

    for size in sorted(block_sizes, reverse=True):
        recent = recent_blocks[size]
        for i in reversed(range(1, len(data) - size)):
            if any(pos in used_positions for pos in range(i, i + size)):
                continue  # 이미 사용된 위치와 겹치면 skip
            candidate = data[i:i+size]
            if candidate == recent:
                top = data[i - 1] if i > 0 else None
                bottom = data[i + size] if i + size < len(data) else None
                results[size] = {
                    "블럭": candidate,
                    "상단": top,
                    "하단": bottom,
                    "순번": i + 1
                }
                used_positions.update(range(i, i + size))  # 블럭 범위 저장
                break
    return {
        "3줄": results.get(3),
        "4줄": results.get(4),
        "5줄": results.get(5)
    }

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
        result3_r, _ = find_top3(all_data, 3, rotate=True)
        result4_r, _ = find_top3(all_data, 4, rotate=True)

        first_matches = find_all_first_matches(all_data, [5, 4, 3])

        return jsonify({
            "예측회차": round_num,
            "최근블럭3": recent3,
            "최근블럭4": recent4,
            "Top3_3줄": result3,
            "Top3_4줄": result4,
            "Top3_3줄_180도": result3_r,
            "Top3_4줄_180도": result4_r,
            "처음매칭": first_matches
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
