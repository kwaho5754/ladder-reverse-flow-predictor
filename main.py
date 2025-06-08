from flask import Flask, jsonify, request, send_from_directory
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

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀') for s, c, o in map(parse_block, block)]

def flip_start(block):
    return [s + ('4' if c == '3' else '3') + ('홀' if o == '짝' else '짝') for s, c, o in map(parse_block, block)]

def flip_odd_even(block):
    return [('우' if s == '좌' else '좌') + ('4' if c == '3' else '3') + o for s, c, o in map(parse_block, block)]

def find_all_matches(block, full_data, existing_matches_indices=None):
    """
    주어진 블럭과 일치하는 모든 데이터를 찾고, 상단 및 하단 예측 값을 반환합니다.
    existing_matches_indices: (시작 인덱스, 블럭 길이) 튜플 리스트로,
                              겹치지 않아야 하는 기존 매칭된 블럭들의 인덱스 범위.
    """
    top_matches = []
    bottom_matches = []
    block_len = len(block)

    for i in reversed(range(len(full_data) - block_len + 1)):
        is_overlapping = False
        if existing_matches_indices:
            for existing_start, existing_len in existing_matches_indices:
                # 현재 블럭 범위와 기존 블럭 범위가 겹치는지 확인
                if max(i, existing_start) < min(i + block_len, existing_start + existing_len):
                    is_overlapping = True
                    break
        
        if is_overlapping:
            continue

        candidate = full_data[i:i + block_len]
        if candidate == block:
            top_index = i - 1
            top_pred = full_data[top_index] if top_index >= 0 else "❌ 없음"
            top_matches.append({
                "값": top_pred,
                "블럭": ">".join(block),
                "순번": i + 1
            })

            bottom_index = i + block_len
            bottom_pred = full_data[bottom_index] if bottom_index < len(full_data) else "❌ 없음"
            bottom_matches.append({
                "값": bottom_pred,
                "블럭": ">".join(block),
                "순번": i + 1
            })

    if not top_matches:
        top_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})
    if not bottom_matches:
        bottom_matches.append({"값": "❌ 없음", "블럭": ">".join(block), "순번": "❌"})

    top_matches = sorted(top_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else float('inf'))[:8]
    bottom_matches = sorted(bottom_matches, key=lambda x: int(x["순번"]) if str(x["순번"]).isdigit() else float('inf'))[:8]

    return top_matches, bottom_matches

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route("/predict")
def predict():
    try:
        mode = request.args.get("mode", "3block_orig")
        size_str = mode[0]
        if size_str not in ['3', '4']:
            return jsonify({"error": "지원하지 않는 블럭 크기입니다. 3 또는 4만 가능합니다."}), 400
        size = int(size_str)

        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        round_num = int(raw[0]["date_round"]) + 1
        all_data = [convert(d) for d in raw]
        recent_flow = all_data[:size]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow
        
        # 4줄 블럭이 먼저 매칭되고, 3줄 블럭은 4줄 블럭과 겹치지 않도록 처리
        if size == 3:
            # 모든 4줄 블럭의 원본 및 변형 매칭 인덱스를 찾습니다.
            four_block_matched_indices = []
            four_block_recent_flow = all_data[:4] # 4줄 블럭의 현재 플로우
            for fn in [lambda x: x, flip_full, flip_start, flip_odd_even]:
                transformed_four_block = fn(four_block_recent_flow)
                for i in range(len(all_data) - len(transformed_four_block) + 1):
                    if all_data[i:i + len(transformed_four_block)] == transformed_four_block:
                        four_block_matched_indices.append((i, len(transformed_four_block)))
            
            # 3줄 블럭 매칭 시 4줄 블럭 매칭 인덱스를 제외합니다.
            top, bottom = find_all_matches(flow, all_data, existing_matches_indices=four_block_matched_indices)
        else: # size == 4 인 경우
            top, bottom = find_all_matches(flow, all_data)


        return jsonify({
            "예측회차": round_num,
            "상단값들": top,
            "하단값들": bottom
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/predict_top3_summary")
def predict_top3_summary():
    try:
        from itertools import chain
        response = supabase.table(SUPABASE_TABLE) \
            .select("*") \
            .order("reg_date", desc=True) \
            .order("date_round", desc=True) \
            .limit(3000) \
            .execute()

        raw = response.data
        all_data = [convert(d) for d in raw]

        result = {}

        # 4줄 블럭의 모든 변형에 대한 매칭 인덱스를 먼저 찾습니다.
        four_block_matched_indices_for_summary = []
        for fn in [lambda x: x, flip_full, flip_start, flip_odd_even]: # 원본 및 모든 변형 포함
            temp_block_4 = all_data[:4] # 4줄 블럭
            transformed_temp_block_4 = fn(temp_block_4)
            for i in range(len(all_data) - len(transformed_temp_block_4) + 1):
                if all_data[i:i + len(transformed_temp_block_4)] == transformed_temp_block_4:
                    four_block_matched_indices_for_summary.append((i, len(transformed_temp_block_4)))

        for size in [3, 4]:  # 3줄 + 4줄 블럭만 포함
            recent_block = all_data[:size]
            transform_modes = {
                "orig": lambda x: x, # 원본 포함
                "flip_full": flip_full,
                "flip_start": flip_start,
                "flip_odd_even": flip_odd_even
            }

            top_values = []
            bottom_values = []

            for mode_name, fn in transform_modes.items():
                flow = fn(recent_block)
                
                if size == 3: # 3줄 블럭인 경우에만 4줄 블럭 겹침 방지 로직 적용
                    top, bottom = find_all_matches(flow, all_data, existing_matches_indices=four_block_matched_indices_for_summary)
                else: # size == 4
                    top, bottom = find_all_matches(flow, all_data)
                
                top_values += [t["값"] for t in top if t["값"] != "❌ 없음"]
                bottom_values += [b["값"] for b in bottom if b["값"] != "❌ 없음"]

            top_counter = Counter(top_values)
            bottom_counter = Counter(bottom_values)

            result[f"{size}줄 블럭 Top3 요약"] = {
                "Top3상단": [v[0] for v in top_counter.most_common(3)] if top_counter else [],
                "Top3하단": [v[0] for v in bottom_counter.most_common(3)] if bottom_counter else []
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT") or 5000)
    app.run(host='0.0.0.0', port=port)