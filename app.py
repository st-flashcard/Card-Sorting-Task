"""
Card Sorting Task
Streamlit版 臨床評価ツール (新ドメイン対応・アクセス制限なしVer.)
"""

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

# 新ドメインに設定
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

    positions = []
    n = int(number_str)
    if n == 1:
        positions = [(60, 60)]
    elif n == 2:
        positions = [(60, 10), (60, 110)]
    elif n == 3:
        positions = [(60, 10), (10, 110), (110, 110)]
    elif n == 4:
        positions = [(15, 15), (105, 15), (15, 105), (105, 105)]

    items = ""
    for x, y in positions:
        items += f'<g transform="translate({x}, {y})">{shape_svg}</g>'

    max_w = "60px" if size == "small" else "110px"
    
    return f'<div style="display:flex; justify-content:center; align-items:center; width:100%; margin:4px 0;"><svg viewBox="0 0 200 200" style="width:100%; max-width:{max_w}; height:auto;">{items}</svg></div>'

# ─────────────────────────────────────────
# 初期化
# ─────────────────────────────────────────
def init_state():
    defaults = {
        "started": False,
        "finished": False,
        "trial_num": 0,
        "logs": [],
        "current_rule_index": 0,
        "consecutive_correct": 0,
        "categories_achieved": 0,
        "target_card": None,
        "feedback": None,
        "prev_wrong_dimension": None,
        "prev_correct_rule": None,
        "rule_just_changed": False,
        "patient_name": "",
        "examiner_name": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def generate_target():
    return {
        "color":  random.choice(COLORS),
        "shape":  random.choice(SHAPES),
        "number": random.choice(NUMBERS),
    }

def current_rule():
    idx = st.session_state["current_rule_index"]
    return RULE_ORDER[idx] if idx < len(RULE_ORDER) else "color"

def reset_test():
    keys_to_clear = [
        "started","finished","trial_num","logs",
        "current_rule_index","consecutive_correct","categories_achieved",
        "target_card","feedback","prev_wrong_dimension",
        "prev_correct_rule","rule_just_changed",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    init_state()

# ─────────────────────────────────────────
# カード選択時の処理
# ─────────────────────────────────────────
def on_card_selected(ref_index: int):
    target  = st.session_state["target_card"]
    chosen  = REFERENCE_CARDS[ref_index]
    rule    = current_rule()
    is_correct = target[rule] == chosen[rule]

    error_type = None
    chosen_dimension = _match_dimension(target, chosen)

    if not is_correct:
        if (st.session_state["rule_just_changed"]
                and chosen_dimension == st.session_state["prev_correct_rule"]):
            error_type = "milner"
        elif (st.session_state["prev_wrong_dimension"] is not None
              and chosen_dimension == st.session_state["prev_wrong_dimension"]
              and chosen_dimension != rule):
            error_type = "nelson"
        elif st.session_state["consecutive_correct"] >= 3:
            error_type = "failure_to_maintain"
        else:
            error_type = "other"

    log_entry = {
        "試行":          st.session_state["trial_num"] + 1,
        "ターゲット_色":  target["color"],
        "ターゲット_形":  target["shape"],
        "ターゲット_数":  target["number"],
        "選択_色":        chosen["color"],
        "選択_形":        chosen["shape"],
        "選択_数":        chosen["number"],
        "正解ルール":      RULE_LABEL[rule],
        "選択次元":        RULE_LABEL.get(chosen_dimension, "不一致"),
        "正誤":           "○" if is_correct else "×",
        "エラー種別":      _error_label(error_type),
        "達成カテゴリー":  st.session_state["categories_achieved"],
    }
    st.session_state["logs"].append(log_entry)

    if is_correct:
        st.session_state["consecutive_correct"] += 1
        st.session_state["prev_wrong_dimension"] = None
        st.session_state["rule_just_changed"] = False

        if st.session_state["consecutive_correct"] >= REQUIRED_CORRECT:
            st.session_state["categories_achieved"] += 1
            st.session_state["consecutive_correct"] = 0
            old_rule = current_rule()
            st.session_state["current_rule_index"] += 1
            st.session_state["prev_correct_rule"]   = old_rule
            st.session_state["rule_just_changed"]   = True
    else:
        st.session_state["consecutive_correct"] = 0
        st.session_state["prev_wrong_dimension"] = chosen_dimension
        st.session_state["rule_just_changed"]    = False

    st.session_state["feedback"]   = "correct" if is_correct else "incorrect"
    st.session_state["trial_num"] += 1
    st.session_state["target_card"] = generate_target()

    if (st.session_state["trial_num"] >= MAX_TRIALS
            or st.session_state["categories_achieved"] >= MAX_CATEGORIES):
        st.session_state["finished"] = True

def _match_dimension(target, chosen):
    for dim in ["color", "shape", "number"]:
        if target[dim] == chosen[dim]:
            return dim
    return None

def _error_label(error_type):
    mapping = {
        "milner":             "ミルナー型保続",
        "nelson":             "ネルソン型保続",
        "failure_to_maintain":"セット維持困難",
        "other":              "非保続性エラー",
        None:                 "－",
    }
    return mapping.get(error_type, "非保続性エラー")

# ─────────────────────────────────────────
# 画面構成
# ─────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Card Sorting Task",
        page_icon="🧠",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.markdown("""
    <style>
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    button[kind="primary"] {
        background-color: #1e40af !important;
        color: white !important;
        border-radius: 8px !important;
    }
    button[kind="secondary"] {
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        opacity: 0.001 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

    init_state()

    if not st.session_state["started"]:
        # スタート画面
        st.markdown("<div style='text-align:center;'><h1>🧠 Card Sorting Task</h1></div>", unsafe_allow_html=True)
        st.text_input("患者名（任意）", key="patient_name")
        if st.button("🚀 テストを開始する", type="primary", use_container_width=True):
            st.session_state["started"] = True
            st.session_state["target_card"] = generate_target()
            st.rerun()

    elif st.session_state["finished"]:
        # 結果画面
        st.title("📊 テスト結果")
        df = pd.DataFrame(st.session_state["logs"])
        st.dataframe(df, use_container_width=True)
        if st.button("🔄 最初からやり直す", type="primary", use_container_width=True):
            reset_test()
            st.rerun()

    else:
        # テスト中
        target = st.session_state["target_card"]
        trial  = st.session_state["trial_num"]

        # 隠しボタン
        hcols = st.columns(4)
        for i, col in enumerate(hcols):
            with col:
                if st.button(f"CST_CARD_{i}", key=f"hbtn_{trial}_{i}"):
                    on_card_selected(i)
                    st.rerun()

        st.write("### 【基準カード】")
        
        cards_html = ""
        for i, card in enumerate(REFERENCE_CARDS):
            svg = generate_card_svg(card["color"], card["shape"], card["number"], size="small")
            cards_html += f'<div style="flex:1; background:#f8fafc; border:2px solid #cbd5e1; border-radius:10px; cursor:pointer; height:120px; display:flex; align-items:center; justify-content:center;" onclick="selectCard({i})">{svg}</div>'
        
        # クリックを飛ばすJavaScript
        st.markdown(f'<div style="display:flex; gap:10px; justify-content:center;">{cards_html}</div>', unsafe_allow_html=True)
        components.html(f"""
            <script>
            function selectCard(i) {{
                var btns = window.parent.document.querySelectorAll('button');
                for (var j = 0; j < btns.length; j++) {{
                    if (btns[j].innerText.trim() === 'CST_CARD_' + i) {{
                        btns[j].click();
                        break;
                    }}
                }}
            }}
            </script>
        """, height=0)

        st.markdown("---")
        st.write("### 【今から分類するカード】")
        _, tc_col, _ = st.columns([1, 1, 1])
        with tc_col:
            st.markdown(f'<div style="background:#f8fafc; border:4px solid #fbbf24; border-radius:12px; padding:10px;">{generate_card_svg(target["color"], target["shape"], target["number"])}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
