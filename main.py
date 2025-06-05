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

        recent_block = all_data[:size]
        base_block = recent_block[-3:]

        directions = {
            "원본": lambda b: b,
            "대치": lambda b: [reverse_name(x) for x in b],
            "시작점반전": flip_start,
            "홈작반전": flip_odd_even,
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

        # 각 방향에서 모두 나온 값과 해당 목록을 구할 경우
        intersection = {}
        for k in total_freq:
            if k in reverse_total_freq:
                intersection[k] = total_freq[k] + reverse_total_freq[k]
        top_predictions["협층 Top3"] = sorted([{"value": k, "count": v} for k, v in intersection.items()], key=lambda x: -x["count"])[:3]

        weighted = sorted([{"value": k, "count": v} for k, v in dir_counts.items()], key=lambda x: -x["count"])[:3]
        top_predictions["가용치 Top3"] = weighted

        return jsonify({
            "예측회차": round_num,
            "최근블랙": list(reversed(recent_block)),
            "Top3": top_predictions
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
