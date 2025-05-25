from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

URL = "https://ntry.com/data/json/games/power_ladder/recent_result.json"

def convert(entry):
    side = '좌' if entry['start_point'] == 'LEFT' else '우'
    count = str(entry['line_count'])
    oe = '짝' if entry['odd_even'] == 'EVEN' else '홀'
    return f"{side}{count}{oe}"

def parse_block(s):
    return s[0], s[1:-1], s[-1]

def flip_full(block):
    return [
        ('우' if s == '좌' else '좌') + c + ('짝' if o == '홀' else '홀')
        for s, c, o in map(parse_block, block)
    ]

def flip_start(block):
    flipped = []
    for s, c, o in map(parse_block, block):
        c_flip = '4' if c == '3' else '3'
        o_flip = '홀' if o == '짝' else '짝'
        flipped.append(s + c_flip + o_flip)
    return flipped

def flip_odd_even(block):
    flipped = []
    for s, c, o in map(parse_block, block):
        s_flip = '우' if s == '좌' else '좌'
        c_flip = '4' if c == '3' else '3'
        flipped.append(s_flip + c_flip + o)
    return flipped

def find_flow_match(block, full_data):
    block_len = len(block)
    for i in range(len(full_data) - block_len):
        candidate = full_data[i:i+block_len]
        if candidate == block:
            return ">".join(block)
    return ">".join(block)

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/predict")
def predict():
    try:
        raw = requests.get(URL).json()
        data = raw[-288:]

        mode = request.args.get("mode", "3block_orig")
        size = int(mode[0])

        # ✅ 예측값: 가장 최신줄 (data[0])
        prediction_value = convert(data[0])
        round_num = int(data[0]['date_round']) + 1

        # ✅ 블럭: 예측값 아래줄부터 size개
        recent_flow = [convert(d) for d in data[1:size+1]][::-1]
        all_data = [convert(d) for d in data]

        if "flip_full" in mode:
            flow = flip_full(recent_flow)
        elif "flip_start" in mode:
            flow = flip_start(recent_flow)
        elif "flip_odd_even" in mode:
            flow = flip_odd_even(recent_flow)
        else:
            flow = recent_flow

        blk = find_flow_match(flow, all_data)

        return jsonify({
            "예측회차": round_num,
            "예측값": prediction_value,
            "블럭": blk
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
