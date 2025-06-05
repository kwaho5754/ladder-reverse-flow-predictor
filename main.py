import os
import pandas as pd
import requests
from flask import Flask, jsonify, send_file
from collections import Counter
from supabase import create_client, Client

# Supabase 환경변수
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "ladder")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

def fetch_data():
    response = supabase.table(SUPABASE_TABLE).select("*").order("reg_date", desc=True).limit(3000).execute()
    data = response.data
    if not data or len(data) < 100:
        return []
    data_sorted = sorted(data, key=lambda x: (x["reg_date"], x["date_round"]))
    return [row["result"] for row in data_sorted]

def make_blocks(data, size):
    return [''.join(data[i:i+size]) for i in range(len(data) - size + 1)]

def analyze_blocks(data, size, directions):
    block_result = {}
    used_indexes = set()

    for direction in directions:
        direction_blocks = []

        for i in range(len(data) - size):
            block = tuple(data[i:i+size])
            if direction == '원본':
                key = block
            elif direction == '대칭':
                key = tuple('짝' if v == '홀' else '홀' for v in block)
            elif direction == '시작점반전':
                key = ('짝' if block[0] == '홀' else '홀',) + block[1:]
            elif direction == '홀짝반전':
                key = block[:2] + ('짝' if block[2] == '홀' else '홀',)

            direction_blocks.append((key, i))

        counter = Counter()
        for blk, idx in direction_blocks:
            if blk in [b for b, _ in direction_blocks[-1:]]:
                if idx + size < len(data):
                    result = data[idx + size]
                    counter[result] += 1
                    used_indexes.add(idx)

        top3 = [x[0] for x in counter.most_common(3)]
        block_result[direction] = {"top3": top3, "count": sum(counter.values())}

    return block_result, used_indexes

def combine_top3(result_dict):
    all = sum([result["top3"] for result in result_dict.values()], [])
    total = Counter(all)
    return [x[0] for x in total.most_common(3)]

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/predict")
def predict():
    data = fetch_data()
    if len(data) < 100:
        return jsonify({"error": "데이터 부족"})

    latest_round = len(data)
    recent_3 = data[-3:]
    recent_4 = data[-4:]

    three_result, used3 = analyze_blocks(data, 3, ['원본', '대칭', '시작점반전', '홀짝반전'])
    four_result, used4 = analyze_blocks([v for i, v in enumerate(data) if i not in used3], 4, ['원본', '대칭', '시작점반전', '홀짝반전'])

    final_top3 = combine_top3({**three_result, **four_result})

    return jsonify({
        "latest_round": latest_round,
        "3줄블럭": three_result,
        "4줄블럭": four_result,
        "최종 Top3": final_top3
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
