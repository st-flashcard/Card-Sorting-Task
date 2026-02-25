import streamlit as st
import random
import time
import pandas as pd

# 画面を広く使う設定（タブレット向け）
st.set_page_config(layout="wide", page_title="Stroop Task")

# 色の設定（画面で見やすいように黄色は少し濃いめにしています）
COLORS = {
    "あか": "red",
    "あお": "blue",
    "きいろ": "#d4a017", # 見やすい暗めの黄色
    "みどり": "green"
}
COLOR_NAMES = list(COLORS.keys())

# --- セッション状態（データ保存）の初期化 ---
if "phase" not in st.session_state:
    st.session_state.phase = "start" # start, practice, part1, part2, result
if "trial" not in st.session_state:
    st.session_state.trial = 0
if "results" not in st.session_state:
    st.session_state.results = []
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "current_word" not in st.session_state:
    st.session_state.current_word = ""
if "current_color" not in st.session_state:
    st.session_state.current_color = ""

# --- 問題を作成する関数 ---
def next_trial(condition):
    word = random.choice(COLOR_NAMES)
    if condition == "congruent":
        # 一致条件（文字と色が同じ）
        color = word
    else:
        # 不一致条件（文字と色が違う）
        color = random.choice([c for c in COLOR_NAMES if c != word])
    
    st.session_state.current_word = word
    st.session_state.current_color = color
    st.session_state.start_time = time.time() # 問題提示の瞬間の時間を記録

# --- ボタンが押された時の処理 ---
def handle_click(selected_color):
    # 反応時間を計算（現在時刻 - 問題が出た時刻）
    reaction_time = time.time() - st.session_state.start_time
    # 正誤判定（選んだボタンが「文字の色」と同じなら正解）
    is_correct = (selected_color == st.session_state.current_color)
    
    # 記録を保存
    condition = "一致" if st.session_state.phase == "part1" else "不一致"
    st.session_state.results.append({
        "条件": condition,
        "試行": st.session_state.trial + 1,
        "文字": st.session_state.current_word,
        "色": st.session_state.current_color,
        "回答": selected_color,
        "正誤": "〇" if is_correct else "×",
        "反応時間(秒)": round(reaction_time, 3)
    })
    
    st.session_state.trial += 1

# --- 画面の描画 ---
st.title("🧠 ストループ課題アプリ（Stroop Task）")

# 【1】スタート画面
if st.session_state.phase == "start":
    st.markdown("### 【ルール】\n文字の意味ではなく、**文字が塗られている「色」**のボタンをできるだけ早く押してください。")
    if st.button("Part 1（一致条件）をスタート", use_container_width=True):
        st.session_state.phase = "part1"
        st.session_state.trial = 0
        next_trial("congruent")
        st.rerun()

# 【2】テスト画面（Part1 & Part2）
elif st.session_state.phase in ["part1", "part2"]:
    # 試行回数の設定（ここではお試しで各5回に設定しています。後で増やせます）
    MAX_TRIALS = 5 
    
    if st.session_state.trial < MAX_TRIALS:
        condition_text = "Part 1 (文字と色が一致)" if st.session_state.phase == "part1" else "Part 2 (文字と色が不一致)"
        st.write(f"進行状況: {condition_text} - {st.session_state.trial + 1} / {MAX_TRIALS} 問目")
        
        # HTMLを使って色付きの大きな文字を表示
        word = st.session_state.current_word
        color_code = COLORS[st.session_state.current_color]
        html_text = f"<div style='text-align: center; font-size: 100px; font-weight: bold; color: {color_code}; margin-bottom: 30px;'>{word}</div>"
        st.markdown(html_text, unsafe_allow_html=True)
        
        # 回答ボタンを4つ並べる
        cols = st.columns(4)
        for i, color_name in enumerate(COLOR_NAMES):
            with cols[i]:
                # on_clickを使って、ボタンが押された瞬間にhandle_click関数を動かす
                if st.button(color_name, key=f"btn_{i}", use_container_width=True, on_click=handle_click, args=(color_name,)):
                    # 次の問題を用意する
                    if st.session_state.phase == "part1":
                        next_trial("congruent")
                    else:
                        next_trial("incongruent")
        
    else:
        # 規定の回数が終わった時の処理
        if st.session_state.phase == "part1":
            st.warning("Part 1 が終了しました！次は文字と色が【違う】問題が出ます。")
            if st.button("Part 2（不一致条件）をスタート", use_container_width=True):
                st.session_state.phase = "part2"
                st.session_state.trial = 0
                next_trial("incongruent")
                st.rerun()
        else:
            st.success("すべてのテストが終了しました！")
            if st.button("結果を見る", use_container_width=True):
                st.session_state.phase = "result"
                st.rerun()

# 【3】結果画面
elif st.session_state.phase == "result":
    st.markdown("## 📊 評価結果")
    df = pd.DataFrame(st.session_state.results)
    
    # 条件ごとの平均反応時間を計算
    part1_df = df[df["条件"] == "一致"]
    part2_df = df[df["条件"] == "不一致"]
    
    mean_rt1 = part1_df["反応時間(秒)"].mean() if not part1_df.empty else 0
    mean_rt2 = part2_df["反応時間(秒)"].mean() if not part2_df.empty else 0
    interference = mean_rt2 - mean_rt1 # ここが干渉効果！
    
    st.write(f"- **Part 1 (一致) 平均反応時間:** {mean_rt1:.3f} 秒")
    st.write(f"- **Part 2 (不一致) 平均反応時間:** {mean_rt2:.3f} 秒")
    st.markdown(f"### 🛑 ストループ干渉時間: **{interference:.3f} 秒**遅くなりました")
    
    st.write("▼ 全試行のログ")
    st.dataframe(df)
    
    if st.button("最初からやり直す", use_container_width=True):
        st.session_state.clear()
        st.rerun()
