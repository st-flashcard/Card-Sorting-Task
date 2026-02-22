"""
Card Sorting Task
Streamlit版 臨床評価ツール
"""

import streamlit as st
import pandas as pd
import random
import plotly.graph_objects as go
import plotly.express as px

# ─────────────────────────────────────────
# 定数・設定
# ─────────────────────────────────────────
MAX_TRIALS = 64          # 総試行数
REQUIRED_CORRECT = 6    # 1カテゴリー達成に必要な連続正解数
MAX_CATEGORIES = 6      # 達成目標カテゴリー数

COLORS  = ["赤", "緑", "黄", "青"]
SHAPES  = ["三角", "星", "十字", "丸"]
NUMBERS = ["1", "2", "3", "4"]

COLOR_EMOJI  = {"赤": "🔴", "緑": "🟢", "黄": "🟡", "青": "🔵"}
SHAPE_EMOJI  = {"三角": "▲", "星": "★", "十字": "✚", "丸": "●"}
RULE_LABEL   = {"color": "色", "shape": "形", "number": "数"}
RULE_ORDER   = ["color", "shape", "number", "color", "shape", "number"]

# ─────────────────────────────────────────
# 刺激カード（基準4枚）固定定義
# ─────────────────────────────────────────
REFERENCE_CARDS = [
    {"color": "赤",  "shape": "三角", "number": "1"},
    {"color": "緑",  "shape": "星",   "number": "2"},
    {"color": "黄",  "shape": "十字", "number": "3"},
    {"color": "青",  "shape": "丸",   "number": "4"},
]

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
        "feedback": None,          # "correct" | "incorrect" | None
        "prev_wrong_dimension": None,  # ネルソン型判定用
        "prev_correct_rule": None,     # ミルナー型判定用（ルール変更直後のみ有効）
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
    """対象者がカードを選んだときに呼ばれる"""
    target  = st.session_state["target_card"]
    chosen  = REFERENCE_CARDS[ref_index]
    rule    = current_rule()

    # 正誤判定
    is_correct = target[rule] == chosen[rule]

    # ── エラー種別判定 ──────────────────
    error_type = None
    chosen_dimension = _match_dimension(target, chosen)

    if not is_correct:
        # ミルナー型：ルール変更直後で、前の正解ルールで選んでいる
        if (st.session_state["rule_just_changed"]
                and chosen_dimension == st.session_state["prev_correct_rule"]):
            error_type = "milner"

        # ネルソン型：前回の間違えた次元と同じ次元で今回も間違えた
        elif (st.session_state["prev_wrong_dimension"] is not None
              and chosen_dimension == st.session_state["prev_wrong_dimension"]
              and chosen_dimension != rule):
            error_type = "nelson"

        # セット維持困難：連続正解中（3回以上）に急に崩れた
        elif st.session_state["consecutive_correct"] >= 3:
            error_type = "failure_to_maintain"

        # それ以外：非保続性エラー
        else:
            error_type = "other"

    # ── ログ記録 ────────────────────────
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

    # ── 連続正解・カテゴリー管理 ─────────
    if is_correct:
        st.session_state["consecutive_correct"] += 1
        st.session_state["prev_wrong_dimension"] = None
        st.session_state["rule_just_changed"] = False

        if st.session_state["consecutive_correct"] >= REQUIRED_CORRECT:
            st.session_state["categories_achieved"] += 1
            st.session_state["consecutive_correct"] = 0
            # ルール変更
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

    # 終了判定
    if (st.session_state["trial_num"] >= MAX_TRIALS
            or st.session_state["categories_achieved"] >= MAX_CATEGORIES):
        st.session_state["finished"] = True


def _match_dimension(target, chosen):
    """ターゲットと選択カードが一致している次元を返す（最初に見つかったもの）"""
    for dim in ["color", "shape", "number"]:
        if target[dim] == chosen[dim]:
            return dim
    return None  # 全次元不一致

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
# UI部品：カード表示
# ─────────────────────────────────────────
def render_card(card: dict, size="normal", label=None, key=None, on_click=None):
    c_emoji = COLOR_EMOJI.get(card["color"], "")
    s_emoji = SHAPE_EMOJI.get(card["shape"], "")
    n       = card["number"]

    if size == "large":
        html = f"""
        <div style="
            background:#1e293b; border:3px solid #60a5fa;
            border-radius:16px; padding:24px 20px; text-align:center;
            min-width:120px; font-family:'BIZ UDPGothic',sans-serif;
            box-shadow:0 0 20px rgba(96,165,250,0.3);">
          <div style="font-size:2.8rem; line-height:1.2;">{c_emoji}{s_emoji}</div>
          <div style="font-size:1.4rem; color:#93c5fd; margin-top:6px;">{n}個</div>
          <div style="font-size:0.85rem; color:#64748b; margin-top:4px;">
            {card['color']}・{card['shape']}・{n}
          </div>
        </div>"""
        st.markdown(html, unsafe_allow_html=True)
    else:
        # 選択ボタン用：Streamlitのボタン内にHTML埋め込みは難しいので
        # カード表示 + ボタンを縦に並べる
        st.markdown(f"""
        <div style="
            background:#0f172a; border:2px solid #334155;
            border-radius:12px; padding:12px 8px; text-align:center;
            font-family:'BIZ UDPGothic',sans-serif;">
          <div style="font-size:1.8rem;">{c_emoji}{s_emoji}</div>
          <div style="font-size:1rem; color:#94a3b8;">{n}個</div>
          <div style="font-size:0.7rem; color:#475569; margin-top:2px;">
            {card['color']}・{card['shape']}・{n}
          </div>
        </div>""", unsafe_allow_html=True)
        if on_click is not None:
            st.button(
                f"カード{label}を選ぶ",
                key=key,
                on_click=on_click,
                use_container_width=True,
            )

# ─────────────────────────────────────────
# 画面①：スタート画面
# ─────────────────────────────────────────
def show_start():
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px;">
      <h1 style="font-size:2.2rem; color:#60a5fa; font-family:'BIZ UDPGothic',sans-serif;">
        🧠 Card Sorting Task
      </h1>
      <p style="color:#94a3b8; font-size:1rem;">
        認知的柔軟性評価ツール（カード分類課題）
      </p>
    </div>""", unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("患者名（任意）", key="patient_name")
            st.text_input("検査者名（任意）", key="examiner_name")
            st.markdown("---")
            st.markdown(f"""
            **テスト設定**
            - 総試行数：最大 **{MAX_TRIALS}** 回
            - 連続正解でカテゴリー達成：**{REQUIRED_CORRECT}** 回
            - 達成目標カテゴリー数：**{MAX_CATEGORIES}** カテゴリー
            """)
            st.markdown("---")
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
    cats   = st.session_state["categories_achieved"]
    consec = st.session_state["consecutive_correct"]

    # ── ヘッダー ─────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("試行回数", f"{trial + 1} / {MAX_TRIALS}")
    col_b.metric("達成カテゴリー", f"{cats} / {MAX_CATEGORIES}")
    col_c.metric("現在の連続正解", f"{consec} / {REQUIRED_CORRECT}")

    st.markdown("---")

    # ── フィードバック ───────────────────
    fb = st.session_state.get("feedback")
    if fb == "correct":
        st.success("✅ 正解！")
    elif fb == "incorrect":
        st.error("❌ 不正解")

    # ── 刺激カード（基準4枚）表示 ─────────
    st.markdown(
        "<p style='text-align:center; color:#94a3b8; font-size:0.9rem;'>【基準カード】</p>",
        unsafe_allow_html=True
    )
    ref_cols = st.columns(4)
    for i, (col, card) in enumerate(zip(ref_cols, REFERENCE_CARDS)):
        with col:
            c_emoji = COLOR_EMOJI[card["color"]]
            s_emoji = SHAPE_EMOJI[card["shape"]]
            st.markdown(f"""
            <div style="background:#1e293b; border:2px solid #334155;
                        border-radius:10px; padding:10px; text-align:center;">
              <div style='font-size:1.6rem;'>{c_emoji}{s_emoji}</div>
              <div style='font-size:0.9rem; color:#94a3b8;'>{card['number']}個</div>
              <div style='font-size:0.65rem; color:#475569;'>
                {card['color']}・{card['shape']}・{card['number']}
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ターゲットカード ─────────────────
    st.markdown(
        "<p style='text-align:center; color:#fbbf24; font-size:0.9rem; font-weight:bold;'>【分類するカード】</p>",
        unsafe_allow_html=True
    )
    _, tc_col, _ = st.columns([1.5, 1, 1.5])
    with tc_col:
        c_emoji = COLOR_EMOJI[target["color"]]
        s_emoji = SHAPE_EMOJI[target["shape"]]
        st.markdown(f"""
        <div style="background:#1e293b; border:3px solid #fbbf24;
                    border-radius:16px; padding:20px; text-align:center;
                    box-shadow:0 0 20px rgba(251,191,36,0.3);">
          <div style='font-size:2.8rem;'>{c_emoji}{s_emoji}</div>
          <div style='font-size:1.2rem; color:#fbbf24;'>{target['number']}個</div>
          <div style='font-size:0.75rem; color:#78716c;'>
            {target['color']}・{target['shape']}・{target['number']}
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown(
        "<p style='text-align:center; color:#94a3b8; margin-top:16px;'>どの基準カードと同じグループですか？</p>",
        unsafe_allow_html=True
    )

    # ── 選択ボタン ───────────────────────
    btn_cols = st.columns(4)
    for i, (col, card) in enumerate(zip(btn_cols, REFERENCE_CARDS)):
        with col:
            c_emoji = COLOR_EMOJI[card["color"]]
            s_emoji = SHAPE_EMOJI[card["shape"]]
            st.markdown(f"""
            <div style="background:#0f172a; border:1px solid #334155;
                        border-radius:10px; padding:10px; text-align:center; margin-bottom:4px;">
              <div style='font-size:1.6rem;'>{c_emoji}{s_emoji}</div>
              <div style='font-size:0.8rem; color:#64748b;'>{card['number']}個</div>
            </div>""", unsafe_allow_html=True)
            st.button(
                f"カード {i+1}",
                key=f"btn_{trial}_{i}",
                on_click=on_card_selected,
                args=(i,),
                use_container_width=True,
            )

# ─────────────────────────────────────────
# 画面③：結果レポート
# ─────────────────────────────────────────
def show_results():
    df = pd.DataFrame(st.session_state["logs"])

    st.markdown("""
    <h2 style='color:#60a5fa; font-family:"BIZ UDPGothic",sans-serif;'>
      📊 テスト結果レポート
    </h2>""", unsafe_allow_html=True)

    # 患者・検査者情報
    p = st.session_state.get("patient_name", "")
    e = st.session_state.get("examiner_name", "")
    if p or e:
        st.markdown(f"**患者名：** {p}　　**検査者：** {e}")

    # ── 総合スコア ───────────────────────
    total_trials    = len(df)
    total_correct   = (df["正誤"] == "○").sum()
    total_errors    = (df["正誤"] == "×").sum()
    categories      = st.session_state["categories_achieved"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総試行数",           total_trials)
    col2.metric("達成カテゴリー数",    categories)
    col3.metric("総正解数",           total_correct)
    col4.metric("総エラー数",         total_errors)

    st.markdown("---")

    # ── エラー種別集計 ─────────────────
    error_df = df[df["正誤"] == "×"]
    error_counts = error_df["エラー種別"].value_counts().reset_index()
    error_counts.columns = ["エラー種別", "回数"]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("エラー種別の内訳")
        error_labels_order = ["ミルナー型保続","ネルソン型保続","セット維持困難","非保続性エラー"]
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
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            showlegend=False,
            margin=dict(t=20,b=20,l=20,r=20),
        )
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
| 🔴 ミルナー型保続 | {milner_n}回 | 過去の成功体験からの切り替え困難（前頭葉機能） |
| 🟠 ネルソン型保続 | {nelson_n}回 | 直前の自分の行動パターンからの脱却困難 |
| 🟡 セット維持困難 | {ftm_n}回 | 注意維持困難・ルール保持の不安定さ |
| ⬜ 非保続性エラー | {other_n}回 | 注意逸脱・ワーキングメモリ低下の疑い |
        """)

    st.markdown("---")

    # ── 試行ごとの正誤推移グラフ ──────────
    st.subheader("試行ごとの正誤推移")
    df_plot = df.copy()
    df_plot["正誤_数値"] = df_plot["正誤"].map({"○": 1, "×": 0})
    # 10試行ごとの正解率
    df_plot["ブロック"] = ((df_plot["試行"] - 1) // 10) * 10 + 5
    block_summary = df_plot.groupby("ブロック")["正誤_数値"].mean().reset_index()
    block_summary.columns = ["試行（中点）", "正解率"]

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=block_summary["試行（中点）"],
        y=block_summary["正解率"],
        mode="lines+markers",
        line=dict(color="#60a5fa", width=2),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(96,165,250,0.1)",
    ))
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.8)",
        font_color="#e2e8f0",
        yaxis=dict(title="正解率", range=[0,1], tickformat=".0%",
                   gridcolor="#1e293b"),
        xaxis=dict(title="試行番号", gridcolor="#1e293b"),
        margin=dict(t=20,b=40,l=60,r=20),
    )
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # ── 全試行履歴テーブル ───────────────
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
    st.dataframe(styled_df, use_container_width=True, height=400)

    # CSVダウンロード
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 結果をCSVでダウンロード",
        data=csv,
        file_name=f"cst_result_{p or 'patient'}.csv",
        mime="text/csv",
    )

    st.markdown("---")
    if st.button("🔄 テストをリセットして最初から", type="secondary"):
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

    # ダークテーマ調整CSS
    st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    .stButton > button {
        background-color: #1e40af;
        color: white;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #2563eb;
        border-color: #60a5fa;
    }
    [data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px;
    }
    .stDataFrame { border-radius: 8px; }
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
