import os
import requests
from collections import Counter, defaultdict
from flask import Flask, jsonify, render_template
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE")

app = Flask(__name__)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_block(data, start, length):
    return "-".join([row["result"] for row in data[start:start+length]])

def mirror_block(block):
    return block.replace("좌", "X").replace("우", "좌").replace("X", "우")

def start_flip_block(block):
    parts = block.split("-")
    if not parts: return block
    start = parts[0]
    flipped = []
    for p in parts:
        if "짝" in p:
            flipped.append(p.replace("짝", "홀"))
        elif "홀" in p:
            flipped.append(p.replace("홀", "짝"))
        else:
            flipped.append(p)
    return "-".join(flipped)

def even_odd_flip_block(block):
    parts = block.split("-")
    if not parts: return block
    flipped = []
    for p in parts:
        if "홀" in p:
            flipped.append(p.replace("홀", "짝"))
        elif "짝" in p:
            flipped.append(p.replace("짝", "홀"))
        else:
            flipped.append(p)
    return "-".join(flipped)

def predict_block_top3(data, block_len, skip_overlap_with=None):
    prediction_scores = defaultdict(int)
    recent_block = create_block(data, 0, block_len)

    variants = {
        "원본": recent_block,
        "대칭": mirror_block(recent_block),
        "시작반전": start_flip_block(recent_block),
        "홀짝반전": even_odd_flip_block(recent_block)
    }

    skip_index = set()
    if skip_overlap_with:
        for i in range(len(data) - skip_overlap_with):
            for j in range(skip_overlap_with):
                skip_index.add(i + j)

    for name, block in variants.items():
        counter = Counter()
        for i in range(1, len(data) - block_len):  # i > 0 보장
            if skip_overlap_with and any(k in skip_index for k in range(i, i + block_len)):
                continue
            blk = create_block(data, i, block_len)
            if blk == block:
                target = data[i - 1]["result"]
                counter[target] += 1

        top3 = [item[0] for item in counter.most_common(3)]
        for rank, val in enumerate(top3):
            prediction_scores[val] += 3 - rank

    return sorted(prediction_scores.items(), key=lambda x: -x[1])[:3]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict")
def predict():
    response = supabase.table(SUPABASE_TABLE).select("*").order("id", desc=True).limit(3000).execute()
    data = response.data[::-1]  # 최신순으로 정렬된 걸 오래된 순으로

    if len(data) < 100:
        return jsonify({"error": "데이터 부족"})

    top3_5 = predict_block_top3(data, 5)
    top3_4 = predict_block_top3(data, 4, skip_overlap_with=5)

    recent_block_5 = create_block(data, 0, 5)
    recent_block_4 = create_block(data, 0, 4)

    return jsonify({
        "recent_block_5": recent_block_5,
        "top3_5": top3_5,
        "recent_block_4": recent_block_4,
        "top3_4": top3_4,
    })

if __name__ == "__main__":
    app.run(debug=True)
