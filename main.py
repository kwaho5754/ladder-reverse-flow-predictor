# ✅ main.py (예측 Top3 기반 통계로 개선된 구조)
from flask import Flask, jsonify, request, send_from_directory
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
    if not block:
        return []
    return [reverse_name(block[0])] + block[1:]

def flip_odd_even(block):
    return [reverse_name(b) if '홀' in b or '짝' in b else b for b in block]

def rotate_180(block):
    return list(reversed([reverse_name(b) for b in block]))

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        size = 5
        raw = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data

        if not raw or len(raw) < size + 3:
            return jsonify({"error": "데이터 부족"}), 500

        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        recent_block = list(reversed(all_data[:size]))
        base_block = recent_block[:3]

        directions = {
            "원본": lambda b: b,
            "대치": lambda b: [reverse_name(x) for x in b],
            "시작점반전": flip_start,
            "홀짝반전": flip_odd_even,
        }

        top_predictions = {}
        total_freq = {}
        reverse_total_freq = {}
        dir_counts = {}

        for name, transform in directions.items():
            transformed = transform(base_block)
            freq = {}
            for i in range(3, len(all_data) - 3):
                candidate = all_data[i:i+3]
                if candidate == transformed:
                    above = all_data[i-1] if i > 0 else None
                    if above:
                        freq[above] = freq.get(above, 0) + 1
            top3 = sorted(freq.items(), key=lambda x: -x[1])[:3]
            top_predictions[name] = [{"value": k, "count": v} for k, v in top3]
            for k, v in freq.items():
                total_freq[k] = total_freq.get(k, 0) + v
                dir_counts[k] = dir_counts.get(k, 0) + 1

        for name, transform in directions.items():
            transformed = transform(base_block)
            rotated = list(reversed([reverse_name(b) for b in transformed]))
            freq = {}
            for i in range(3, len(all_data) - 3):
                candidate = all_data[i:i+3]
                if candidate == rotated:
                    below = all_data[i+3] if i+3 < len(all_data) else None
                    if below:
                        freq[below] = freq.get(below, 0) + 1
            top3 = sorted(freq.items(), key=lambda x: -x[1])[:3]
            label = f"{name}(180도)"
            top_predictions[label] = [{"value": k, "count": v} for k, v in top3]
            for k, v in freq.items():
                reverse_total_freq[k] = reverse_total_freq.get(k, 0) + v
                dir_counts[k] = dir_counts.get(k, 0) + 1

        total_sorted = sorted(total_freq.items(), key=lambda x: -x[1])
        top_predictions["Top3 합산"] = [{"value": k, "count": v} for k, v in total_sorted[:3]]

        reverse_total_sorted = sorted(reverse_total_freq.items(), key=lambda x: -x[1])
        top_predictions["Top3 합산(180도)"] = [{"value": k, "count": v} for k, v in reverse_total_sorted[:3]]

        intersection = {}
        for k in total_freq:
            if k in reverse_total_freq:
                intersection[k] = total_freq[k] + reverse_total_freq[k]
        top_predictions["교집합 Top3"] = sorted([{"value": k, "count": v} for k, v in intersection.items()], key=lambda x: -x["count"])[:3]

        weighted = sorted([{"value": k, "count": v} for k, v in dir_counts.items()], key=lambda x: -x["count"])[:3]
        top_predictions["가중치 Top3"] = weighted

        recent_20 = all_data[:20]
        flow_freq = {}
        for val in recent_20:
            flow_freq[val] = flow_freq.get(val, 0) + 1
        flow_top3 = sorted(flow_freq.items(), key=lambda x: -x[1])[:3]
        top_predictions["흐름 기반 Top3"] = [{"value": k, "count": v} for k, v in flow_top3]

        similar_freq = {}
        for i in range(3, len(all_data) - 3):
            candidate = all_data[i:i+3]
            match = sum([1 for a, b in zip(candidate, base_block) if a == b])
            if match >= 2:
                above = all_data[i-1] if i > 0 else None
                if above:
                    similar_freq[above] = similar_freq.get(above, 0) + 1
        similar_top3 = sorted(similar_freq.items(), key=lambda x: -x[1])[:3]
        top_predictions["유사 블럭 Top3"] = [{"value": k, "count": v} for k, v in similar_top3]

        # ✅ 예측 Top3 기준 통계 계산
        key_list = ["Top3 합산", "Top3 합산(180도)", "교집합 Top3"]
        top3_stats = {"좌": 0, "우": 0, "3줄": 0, "4줄": 0, "홀": 0, "짝": 0}
        for key in key_list:
            for entry in top_predictions.get(key, []):
                val = entry["value"]
                if val.startswith("좌"): top3_stats["좌"] += 1
                if val.startswith("우"): top3_stats["우"] += 1
                if "3" in val: top3_stats["3줄"] += 1
                if "4" in val: top3_stats["4줄"] += 1
                if val.endswith("홀"): top3_stats["홀"] += 1
                if val.endswith("짝"): top3_stats["짝"] += 1

        return jsonify({
            "예측회차": round_num,
            "최근블럭": recent_block,
            "Top3": top_predictions,
            "Top3분석": top3_stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
