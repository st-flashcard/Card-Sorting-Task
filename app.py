import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import plotly.graph_objects as go
import plotly.express as px

# ─────────────────────────────────────────
# 定数・設定
# ─────────────────────────────────────────
MAX_TRIALS = 64
REQUIRED_CORRECT = 6
MAX_CATEGORIES = 6

COLORS  = ["赤", "緑", "黄", "青"]
SHAPES  = ["三角", "星", "十字", "丸"]
NUMBERS = ["1", "2", "3", "4"]

RULE_LABEL   = {"color": "色", "shape": "形", "number": "数"}
RULE_ORDER   = ["color", "shape", "number", "color", "shape", "number"]

REFERENCE_CARDS = [
    {"color": "赤",  "shape": "三角", "number": "1"},
    {"color": "緑",  "shape": "星",   "number": "2"},
    {"color": "黄",  "shape": "十字", "number": "3"},
    {"color": "青",  "shape": "丸",   "number": "4"},
]

# 新しいドメインに変更
BLOG_URL = "https://dementia-stroke-st.com/"

# ─────────────────────────────────────────
# 図形（SVG）描画ジェネレーター
# ─────────────────────────────────────────
def generate_card_svg(color_name, shape_name, number_str, size="normal"):
    color_map = {"赤": "#ef4444", "緑": "#22c55e", "黄": "#eab308", "青": "#3b82f6"}
    c = color_map.get(color_name, "#ffffff")
    
    if shape_name == "丸":
        shape_svg = f'<circle cx="40" cy="40" r="35" fill="{c}"/>'
    elif shape_name == "三角":
        shape_svg = f'<polygon points="40,5 75,75 5,75" fill="{c}"/>'
    elif shape_name == "十字":
        shape_svg = f'<polygon points="25,5 55,5 55,25 75,25 75,55 55,55 55,75 25,75 25,55 5,55 5,25 25,25" fill="{c}"/>'
    elif shape_name == "星":
        shape_svg = f'<polygon points="40,2 52,27 79,31 59,50 65,77 40,63 15,77 21,50 1,31 28,27" fill="{c}"/>'
    else:
        shape_svg = ""

    n = int(number_str)
    positions = [(60, 60)] if n==1 else [(60,10),(60,110)] if n==2 else [(60,10),(10,110),(110,110)] if n==3 else [(15,15),(105,15),(15,105),(105,105)]
    items = "".join([f'<g transform="translate({x}, {y})">{shape_svg}</g>' for x, y in positions])
    max_w = "60px" if size == "small" else "110px"
    return f'<div style="display:flex; justify-content:center; align-items:center; width:100%; margin:4px 0;"><svg viewBox="0 0 200 200" style="width:100%; max-width:{max_w}; height:auto;">{items}</svg></div>'

# ─────────────────────────────────────────
# 初期化・状態管理
# ─────────────────────────────────────────
def init_state():
    defaults = {
        "started": False, "finished": False, "trial_num": 0, "logs": [],
        "current_rule_index": 0, "consecutive_correct": 0, "categories_achieved": 0,
        "target_card": None, "feedback": None, "prev_wrong_dimension": None,
        "prev_correct_rule": None, "rule_just_changed": False,
        "patient_name": "", "examiner_name": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def generate_target():
    return {"color": random.choice(COLORS), "shape": random.choice(SHAPES), "number": random.choice(NUMBERS)}

def on_card_selected(ref_index: int):
    target = st.session_state["target_card"]
    chosen = REFERENCE_CARDS[ref_index]
    rule = st.session_state["current_rule_index"]
    current_rule = RULE_ORDER[rule] if rule < len(RULE_ORDER) else "color"
    is_correct = target[current_rule] == chosen[current_rule]

    # エラー分類
    chosen_dim = next((d for d in ["color", "shape", "number"] if target[d] == chosen[d]), None)
    error_type = None
    if not is_correct:
        if st.session_state["rule_just_changed"] and chosen_dim == st.session_state["prev_correct_rule"]:
            error_type = "milner"
        elif st.session_state["prev_wrong_dimension"] == chosen_dim and chosen_dim != current_rule:
            error_type = "nelson"
        elif st.session_state["consecutive_correct"] >= 3:
            error_type = "failure_to_maintain"
        else:
            error_type = "other"

    st.session_state["logs"].append({
        "試行": st.session_state["trial_num"] + 1,
        "正解ルール": RULE_LABEL[current_rule],
        "正誤": "○" if is_correct else "×",
        "エラー種別": {"milner":"ミルナー型保続", "nelson":"ネルソン型保続", "failure_to_maintain":"セット維持困難", "other":"非保続性エラー"}.get(error_type, "－")
    })

    if is_correct:
        st.session_state["consecutive_correct"] += 1
        if st.session_state["consecutive_correct"] >= REQUIRED_CORRECT:
            st.session_state["categories_achieved"] += 1
            st.session_state["consecutive_correct"] = 0
            st.session_state["prev_correct_rule"] = current_rule
            st.session_state["current_rule_index"] += 1
            st.session_state["rule_just_changed"] = True
    else:
        st.session_state["consecutive_correct"] = 0
        st.session_state["prev_wrong_dimension"] = chosen_dim
        st.session_state["rule_just_changed"] = False

    st.session_state["feedback"] = "correct" if is_correct else "incorrect"
    st.session_state["trial_num"] += 1
    st.session_state["target_card"] = generate_target()
    if st.session_state["trial_num"] >= MAX_TRIALS or st.session_state["categories_achieved"] >= MAX_CATEGORIES:
        st.session_state["finished"] = True

# ─────────────────────────────────────────
# メイン画面
# ─────────────────────────────────────────
def main():
    st.set_page_config(page_title="Card Sorting Task", layout="centered")

    # 【修正ポイント】どんなバージョンでも安全にURLを読み取る書き方
    query_val = ""
    try:
        # 新しい書き方
        query_val = st.query_params.get("from", "")
    except:
        # 古い書き方（予備）
        query_val = st.experimental_get_query_params().get("from", [""])[0]

    # このアプリの合言葉は「blog」です
    if query_val != "blog":
        st.markdown(f"""
        <div style="text-align:center; padding: 40px; background:white; border-radius:20px; border:4px solid #ffedd5;">
            <h1 style="color:#1f2937;">🏠 こんにちは！</h1>
            <p style="color:#4b5563;">このツールはブログ読者様限定です。</p>
            <a href="{BLOG_URL}" style="display:inline-block; padding:10px 20px; background:#6366f1; color:white; border-radius:99px; text-decoration:none;">ブログに戻る</a>
        </div>
        """, unsafe_allow_html=True)
        return

    init_state()

    if not st.session_state["started"]:
        st.title("🧠 Card Sorting Task")
        st.session_state["patient_name"] = st.text_input("患者名", value=st.session_state["patient_name"])
        if st.button("🚀 テスト開始", type="primary", use_container_width=True):
            st.session_state["started"] = True
            st.session_state["target_card"] = generate_target()
            st.rerun()

    elif st.session_state["finished"]:
        st.title("📊 結果レポート")
        df = pd.DataFrame(st.session_state["logs"])
        st.dataframe(df, use_container_width=True)
        if st.button("🔄 やり直す"):
            st.session_state.clear()
            st.rerun()

    else:
        # テスト中
        st.write(f"試行数: {st.session_state.trial_num}/{MAX_TRIALS}")
        
        # 基準カード（クリック判定用）
        cols = st.columns(4)
        for i, card in enumerate(REFERENCE_CARDS):
            with cols[i]:
                st.markdown(generate_card_svg(card["color"], card["shape"], card["number"], size="small"), unsafe_allow_html=True)
                if st.button(f"選択 {i+1}", key=f"btn_{i}", use_container_width=True):
                    on_card_selected(i)
                    st.rerun()

        st.markdown("---")
        # ターゲット
        target = st.session_state["target_card"]
        _, tc_col, _ = st.columns([1, 1, 1])
        with tc_col:
            st.markdown(f'<div style="background:#f8fafc; border:4px solid #fbbf24; border-radius:12px;">{generate_card_svg(target["color"], target["shape"], target["number"])}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
