# main.py
import os
import json
import requests
from collections import Counter
from flask import Flask, jsonify, render_template
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# 블럭 유틸 함수
# -----------------------------
def transform_block(block, mode):
    if mode == "원본":
        return block
    elif mode == "대칭":
        return [b.replace("좌", "TEMP").replace("우", "좌").replace("TEMP", "우")
                  .replace("홀", "TEMP").replace("짝", "홀").replace("TEMP", "짝") for b in block]
    elif mode == "시작점반전":
        return [b.replace("좌", "TEMP").replace("우", "좌").replace("TEMP", "우") if i == 0 else b for i, b in enumerate(block)]
    elif mode == "홀짝반전":
        return [b.replace("홀", "TEMP").replace("짝", "홀").replace("TEMP", "짝") for b in block]
    return block

def get_blocks(data, size):
    blocks = []
    for i in range(len(data) - size):
        block = [row['result'] for row in data[i:i+size]]
        top = data[i-1]['result'] if i > 0 else None
        bottom = data[i+size]['result'] if i+size < len(data) else None
        blocks.append({"block": block, "top": top, "bottom": bottom})
    return blocks

def find_top3_predictions(data, block_size):
    recent_block = [row['result'] for row in data[:block_size]]
    result_summary = {}
    blocks = get_blocks(data, block_size)

    for mode in ["원본", "대칭", "시작점반전", "홀짝반전"]:
        transformed = transform_block(recent_block, mode)
        matches = []
        for b in blocks:
            if transform_block(b['block'], mode) == transformed:
                if b['top']:
                    matches.append(b['top'])
        counter = Counter(matches)
        top3 = counter.most_common(3)
        result_summary[mode] = {"top3": top3, "total": sum(counter.values())}

    # 합산 Top3 계산
    all_counts = Counter()
    for mode in result_summary:
        for value, count in result_summary[mode]["top3"]:
            all_counts[value] += count
    total_top3 = all_counts.most_common(3)

    return result_summary, total_top3

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict")
def predict():
    response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).limit(3000).execute()
    data = response.data
    data.reverse()

    result_3, top3_3 = find_top3_predictions(data, 3)
    result_4, top3_4 = find_top3_predictions(data, 4)

    return jsonify({
        "recent_round": data[-1]['date_round'] if data else "-",
        "results": {
            "3줄 블럭": result_3,
            "3줄 합산": top3_3,
            "4줄 블럭": result_4,
            "4줄 합산": top3_4
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
