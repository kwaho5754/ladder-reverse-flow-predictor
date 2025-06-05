# ✅ 흐름 기반 점수제 예측 시스템 main.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from collections import Counter

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "ladder")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 결과값 생성
def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        raw = supabase.table(SUPABASE_TABLE).select("*") \
            .order("reg_date", desc=True).order("date_round", desc=True).limit(3000).execute().data

        if not raw or len(raw) < 100:
            return jsonify({"error": "데이터 부족"}), 500

        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]

        # 최근 흐름 기준 데이터
        recent_20 = all_data[:20]
        recent_50 = all_data[:50]
        recent_100 = all_data[:100]
        total_all = all_data[::-1]  # 오래된 순

        candidates = ["좌3짝", "우3홀", "좌4홀", "우4짝"]
        scores = {c: 0 for c in candidates}

        # 전체 빈도
        total_counter = Counter(total_all)
        total_len = len(total_all)

        # 최근 빈도
        recent_counter = Counter(recent_20)

        for c in candidates:
            # 1. 전체 비중 대비 최근 급증 시 감점
            total_ratio = total_counter[c] / total_len
            recent_ratio = recent_counter[c] / 20 if c in recent_counter else 0
            if recent_ratio > total_ratio * 1.8:
                scores[c] -= 1
            elif recent_ratio < total_ratio * 0.5:
                scores[c] += 1  # 반등 가능성

            # 2. 최근 3연속 이상 반복 시 감점
            repeat_count = 0
            for i in range(len(recent_20)):
                if recent_20[i] == c:
                    repeat_count += 1
                    if repeat_count >= 3:
                        scores[c] -= 1
                        break
                else:
                    repeat_count = 0

            # 3. 최근 50줄 안에 거의 안 나왔으면 가산
            if recent_50.count(c) <= 2:
                scores[c] += 1

            # 4. 최근 흐름에서 갑작스러운 반전 후보면 +1
            if recent_20.count(c) == 0:
                scores[c] += 1

        # 점수 높은 순 Top3 + 제외 1개
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        top3 = sorted_scores[:3]
        exclude = sorted_scores[-1]

        return jsonify({
            "예측회차": round_num,
            "Top3예측": top3,
            "제외값": exclude,
            "최근흐름": recent_20,
            "점수표": scores
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)
