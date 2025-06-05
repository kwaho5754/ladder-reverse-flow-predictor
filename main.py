# ✅ main.py (3줄/4줄 완전 분리 + 독립 예측 구조)
from flask import Flask, jsonify
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
CORS(app)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
TABLE = os.getenv("SUPABASE_TABLE")

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def reverse_name(name):
    name = name.replace('좌', '@').replace('우', '좌').replace('@', '우')
    name = name.replace('홀', '@').replace('짝', '홀').replace('@', '짝')
    return name

def flip_start(block): return [reverse_name(block[0])] + block[1:]
def flip_odd_even(block): return [reverse_name(b) if '홀' in b or '짝' in b else b for b in block]

def find_top3(all_data, base_block):
    results = {}
    directions = {
        "원본": lambda x: x,
        "대치": lambda x: [reverse_name(i) for i in x],
        "시작점반전": flip_start,
        "홀짝반전": flip_odd_even
    }
    for name, fn in directions.items():
        b = fn(base_block)
        freq = {}
        for i in range(len(all_data) - len(b)):
            if all_data[i:i+len(b)] == b:
                if i > 0:
                    above = all_data[i - 1]
                    freq[above] = freq.get(above, 0) + 1
        results[name] = sorted(freq.items(), key=lambda x: -x[1])[:3]
    return results

@app.route("/predict")
def predict():
    try:
        raw = supabase.table(TABLE).select("*").order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data
        if not raw or len(raw) < 10:
            return jsonify({"error": "데이터 부족"}), 500

        all_data = [convert(x) for x in raw]
        round_num = int(raw[0]['date_round']) + 1

        # ✅ 3줄 블럭 분석 (최신순 0~2)
        base3 = list(reversed(all_data[:3]))
        pred3 = find_top3(all_data, base3)

        # ✅ 4줄 블럭 분석 (단 3줄블럭과 겹치지 않도록 4줄 블럭의 시작점이 3줄 블럭 시작점과 겹치면 제거)
        base4 = list(reversed(all_data[3:7]))
        pred4 = find_top3(all_data, base4)

        return jsonify({
            "예측회차": round_num,
            "최근블럭_3줄": base3,
            "최근블럭_4줄": base4,
            "3줄 예측": pred3,
            "4줄 예측": pred4
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
