"""
Card Sorting Task
Streamlit版 臨床評価ツール (直接クリック 確実オーバーレイ版)
"""

import streamlit as st
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
# 画面①：スタート画面
# ─────────────────────────────────────────
def show_start():
    st.markdown("""
    <div style="text-align:center; padding: 20px 0;">
      <h1 style="font-size:2rem; color:#60a5fa; font-family:'BIZ UDPGothic',sans-serif; margin-bottom:5px;">
        🧠 Card Sorting Task
      </h1>
      <p style="color:#94a3b8; font-size:0.9rem;">
        認知的柔軟性評価ツール
      </p>
    </div>""", unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("患者名（任意）", key="patient_name")
            st.text_input("検査者名（任意）", key="examiner_name")
            st.markdown(f"""
            <div style="background:#1e293b; padding:15px; border-radius:10px; margin:15px 0;">
                <p style="margin:0; font-size:0.9rem;">✔️ 総試行数：最大 <b>{MAX_TRIALS}</b> 回</p>
                <p style="margin:0; font-size:0.9rem;">✔️ 連続正解で達成：<b>{REQUIRED_CORRECT}</b> 回</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚀 テストを開始する", type="primary", use_container_width=True):
                st.session_state["started"] = True
                st.session_state["target_card"] = generate_target()
                st.rerun()

# ─────────────────────────────────────────
# 画面②：テスト実施画面
# ─────────────────────────────────────────
def show_test():
    target = st.session_state["target_card"]
    trial  = st.session_state["trial_num"]

    # フィードバック表示
    fb = st.session_state.get("feedback")
    if fb == "correct":
        st.markdown('<div style="background-color:rgba(34,197,94,0.2); color:#4ade80; padding:8px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:10px;">✅ 正解！</div>', unsafe_allow_html=True)
    elif fb == "incorrect":
        st.markdown('<div style="background-color:rgba(239,68,68,0.2); color:#f87171; padding:8px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:10px;">❌ 不正解</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:8px; margin-bottom:10px;">&nbsp;</div>', unsafe_allow_html=True)

    # ── 基準カード（直接クリック） ─────────
    st.markdown("<p style='text-align:center; color:#94a3b8; font-size:1rem; font-weight:bold;'>【基準カード】</p>", unsafe_allow_html=True)
    ref_cols = st.columns(4)
    for i, (col, card) in enumerate(zip(ref_cols, REFERENCE_CARDS)):
        with col:
            svg_html = generate_card_svg(card["color"], card["shape"], card["number"], size="small")
            
            # カードを描画
            st.markdown(f'<div class="ref-card">{svg_html}</div>', unsafe_allow_html=True)
            
            # カードの下に選択ボタンを配置（シンプルで確実な方式）
            card = REFERENCE_CARDS[i]
            st.button(
                f"▲ カード{i+1}を選ぶ",
                key=f"btn_{trial}_{i}",
                on_click=on_card_selected,
                args=(i,),
                use_container_width=True,
            )

    st.markdown("<hr style='border-color:#334155; margin:15px 0;'>", unsafe_allow_html=True)

    # ── ターゲットカード ─────────────────
    st.markdown("<p style='text-align:center; color:#fbbf24; font-size:1rem; font-weight:bold;'>【今から分類するカード】<br><span style='font-size:0.8rem; font-weight:normal; color:#94a3b8;'>上の基準カードを直接タップしてください</span></p>", unsafe_allow_html=True)
    _, tc_col, _ = st.columns([1.5, 1, 1.5])
    with tc_col:
        svg_html = generate_card_svg(target["color"], target["shape"], target["number"], size="large")
        st.markdown(f'<div style="height:160px; background:#f8fafc; border:4px solid #fbbf24; border-radius:12px; display:flex; justify-content:center; align-items:center; box-shadow:0 0 15px rgba(251,191,36,0.3);">{svg_html}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────
# 画面③：結果レポート
# ─────────────────────────────────────────
def show_results():
    df = pd.DataFrame(st.session_state["logs"])

    st.markdown("""<h2 style='color:#60a5fa; font-family:"BIZ UDPGothic",sans-serif; margin-bottom:0;'>📊 テスト結果レポート</h2>""", unsafe_allow_html=True)

    p = st.session_state.get("patient_name", "")
    e = st.session_state.get("examiner_name", "")
    if p or e:
        st.markdown(f"**患者名：** {p}　　**検査者：** {e}")

    total_trials    = len(df)
    total_correct   = (df["正誤"] == "○").sum()
    total_errors    = (df["正誤"] == "×").sum()
    categories      = st.session_state["categories_achieved"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総試行数", total_trials)
    col2.metric("達成カテゴリー", categories)
    col3.metric("総正解数", total_correct)
    col4.metric("総エラー数", total_errors)

    st.markdown("---")

    error_df = df[df["正誤"] == "×"]
    error_counts = error_df["エラー種別"].value_counts().reset_index()
    error_counts.columns = ["エラー種別", "回数"]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("エラー種別の内訳")
        error_color_map = {
            "ミルナー型保続": "#ef4444",
            "ネルソン型保続": "#f97316",
            "セット維持困難": "#eab308",
            "非保続性エラー": "#6b7280",
        }
        fig_pie = go.Figure(go.Pie(
            labels=error_counts["エラー種別"],
            values=error_counts["回数"],
            marker_colors=[error_color_map.get(x, "#6b7280") for x in error_counts["エラー種別"]],
            hole=0.4,
            textinfo="label+value+percent",
        ))
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", showlegend=False, margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("エラーの臨床的解釈")
        milner_n  = error_counts.query("エラー種別=='ミルナー型保続'")["回数"].sum() if "ミルナー型保続" in error_counts["エラー種別"].values else 0
        nelson_n  = error_counts.query("エラー種別=='ネルソン型保続'")["回数"].sum() if "ネルソン型保続" in error_counts["エラー種別"].values else 0
        ftm_n     = error_counts.query("エラー種別=='セット維持困難'")["回数"].sum() if "セット維持困難" in error_counts["エラー種別"].values else 0
        other_n   = error_counts.query("エラー種別=='非保続性エラー'")["回数"].sum() if "非保続性エラー" in error_counts["エラー種別"].values else 0

        st.markdown(f"""
| エラー種別 | 回数 | 解釈 |
|---|---|---|
| 🔴 ミルナー型保続 | {milner_n}回 | 過去の成功体験からの切り替え困難 |
| 🟠 ネルソン型保続 | {nelson_n}回 | 直前の自分の行動パターンからの脱却困難 |
| 🟡 セット維持困難 | {ftm_n}回 | 注意維持困難・ルール保持の不安定さ |
| ⬜ 非保続性エラー | {other_n}回 | 注意逸脱・ワーキングメモリ低下の疑い |
        """)

    st.markdown("---")

    st.subheader("全試行の詳細ログ")
    def highlight_errors(row):
        if row["正誤"] == "○":
            return ["background-color: rgba(34,197,94,0.1)"] * len(row)
        else:
            type_color = {
                "ミルナー型保続":  "rgba(239,68,68,0.2)",
                "ネルソン型保続":  "rgba(249,115,22,0.2)",
                "セット維持困難":  "rgba(234,179,8,0.2)",
                "非保続性エラー":  "rgba(107,114,128,0.2)",
            }
            color = type_color.get(row["エラー種別"], "rgba(107,114,128,0.1)")
            return [f"background-color: {color}"] * len(row)

    styled_df = df.style.apply(highlight_errors, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=300)

    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 結果をCSVでダウンロード",
        data=csv,
        file_name=f"cst_result_{p or 'patient'}.csv",
        mime="text/csv",
        type="primary"  # CSSハックの影響を受けないように指定
    )

    st.markdown("---")
    if st.button("🔄 テストをリセットして最初から", type="primary", use_container_width=True):
        reset_test()
        st.rerun()

# ─────────────────────────────────────────
# メイン
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
    /* ヘッダーとフッターを消す */
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* 余白を削る */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 800px;
    }

    /* 全体のダークテーマ */
    .stApp { background-color: #0f172a; color: #e2e8f0; }

    /* primaryボタン（スタート・リセット等の青いボタン）のデザイン */
    button[kind="primary"] {
        background-color: #1e40af !important;
        color: white !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px !important;
        transition: all 0.2s !important;
        padding: 10px 0 !important;
        font-size: 1rem !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover {
        background-color: #2563eb !important;
        border-color: #60a5fa !important;
    }

    /* 基準カードのデザイン */
    .ref-card {
        height: 120px;
        background: #f8fafc;
        border: 2px solid #cbd5e1;
        border-radius: 8px;
        display: flex;
        justify-content: center;
        align-items: center;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 6px;
    }

    /* 選択ボタンのデザイン（secondaryボタンを見やすく） */
    button[kind="secondary"] {
        background-color: #1e293b !important;
        color: #93c5fd !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-weight: bold !important;
        cursor: pointer !important;
        transition: background-color 0.15s, border-color 0.15s !important;
    }
    button[kind="secondary"]:hover {
        background-color: #2563eb !important;
        border-color: #60a5fa !important;
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

    init_state()

    if not st.session_state["started"]:
        show_start()
    elif st.session_state["finished"]:
        show_results()
    else:
        show_test()

if __name__ == "__main__":
    main()
