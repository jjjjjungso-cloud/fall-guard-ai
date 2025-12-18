import streamlit as st
import pandas as pd
import datetime
import time
import joblib
import numpy as np
from textwrap import dedent
import json
import altair as alt

# --------------------------------------------------------------------------------
# 1. 페이지 설정 및 상태 관리
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - AI System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------------------------------
# 2. 스타일 (CSS)
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    .stApp { background-color: #1e252b; color: #e0e0e0; font-family: 'Noto Sans KR', sans-serif; }

    /* 헤더 */
    .header-container {
        background-color: #263238; padding: 10px 20px; border-radius: 5px;
        border-top: 3px solid #0288d1; box-shadow: 0 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .header-info-text { font-size: 1.1em; color: #eceff1; margin-right: 15px; }

    /* 디지털 계기판 */
    .digital-monitor-container {
        background-color: #000000; border: 2px solid #455a64; border-radius: 8px;
        padding: 15px; margin-top: 15px; margin-bottom: 5px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9); transition: border 0.3s;
        display: flex !important; flex-direction: row !important;
        justify-content: space-around !important; align-items: center !important;
    }
    @keyframes blink { 50% { border-color: #ff5252; box-shadow: 0 0 15px #ff5252; } }
    .alarm-active { animation: blink 1s infinite; border: 2px solid #ff5252 !important; }

    .score-box { text-align: center; width: 45%; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .digital-number { font-family: 'Consolas', monospace; font-size: 36px; font-weight: 900; line-height: 1.0; text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px; }
    .monitor-label { color: #90a4ae; font-size: 12px; font-weight: bold; letter-spacing: 1px; }
    .divider-line { width: 1px; height: 50px; background-color: #444; }

    /* 알람 박스 */
    .custom-alert-box {
        position: fixed; bottom: 30px; right: 30px; width: 380px; height: auto;
        background-color: #263238; border-left: 8px solid #ff5252;
        box-shadow: 0 6px 25px rgba(0,0,0,0.7); border-radius: 8px;
        padding: 20px; z-index: 9999; animation: slideIn 0.5s ease-out;
        font-family: 'Noto Sans KR', sans-serif;
    }
    @keyframes slideIn { from { transform: translateX(120%); } to { transform: translateX(0); } }
    .alert-title { color: #ff5252; font-weight: bold; font-size: 1.4em; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
    .alert-content { color: #eceff1; font-size: 1.0em; margin-bottom: 15px; line-height: 1.5; }
    .alert-factors { background-color: #3e2723; padding: 12px; border-radius: 6px; margin-bottom: 20px; color: #ffcdd2; font-size: 0.95em; border: 1px solid #ff5252; }

    /* 기타 UI */
    .note-entry { background-color: #2c3e50; padding: 15px; border-radius: 5px; border-left: 4px solid #0288d1; margin-bottom: 10px; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
    .legend-item { display: inline-block; padding: 2px 8px; margin-right: 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; text-align: center; }
    
    div.stButton > button {
        width: 100%; background-color: #d32f2f; color: white; border: none; padding: 12px 0;
        border-radius: 6px; font-weight: bold; font-size: 1.1em; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: background-color 0.3s, transform 0.2s;
    }
    div.stButton > button:hover { background-color: #b71c1c; transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 리소스 로딩 (KeyError 방지 수정 포함)
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        # 1) 모델
        model = joblib.load('risk_score_model.joblib')
        resources['model'] = model

        # 2) schema
        with open('dashboard_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)
        resources['schema'] = schema
        resources['raw_cols'] = schema.get('raw_input_cols', [])
        resources['category_options'] = schema.get('category_options', {})
        resources['gender_mapping'] = schema.get('gender_mapping', {'M': 1, 'F': 0})

        # 3) train score reference
        ref = np.load('train_score_ref.npz', allow_pickle=True)
        scores_sorted = np.array(ref.get('train_scores_sorted', [])).astype(float)
        resources['train_scores_sorted'] = scores_sorted
        resources['cutoff_top20'] = float(np.quantile(scores_sorted, 0.80))
        resources['cutoff_top40'] = float(np.quantile(scores_sorted, 0.60))

        # 4) [중요] 피처 중요도 로드 (KeyError 해결)
        if hasattr(model, 'feature_importances_'):
            resources['importance'] = pd.DataFrame({
                'feature': resources['raw_cols'],
                'importance': model.feature_importances_
            })
        else:
            resources['importance'] = None

    except Exception:
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 4. 상태 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'alarm_confirmed' not in st.session_state: st.session_state.alarm_confirmed = False

def confirm_alarm():
    st.session_state.alarm_confirmed = True

PATIENTS_BASE = [
    {"id": "12345678", "bed": "04-01", "name": "김수연", "gender": "M", "age": 78, "diag": "Pneumonia"},
    {"id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 65, "diag": "Stomach Cancer"},
    {"id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 82, "diag": "Femur Fracture"},
    {"id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32, "diag": "Appendicitis"},
]

PATIENT_SIM_PRESETS = {
    "12345678": {"sim_sbp": 120, "sim_dbp": 78, "sim_pr": 78, "sim_rr": 18, "sim_bt": 36.6, "sim_alb": 4.1, "sim_crp": 0.3, "sim_severity": 2, "sim_reaction": "alert"},
    "11223344": {"sim_sbp": 115, "sim_dbp": 75, "sim_pr": 88, "sim_rr": 20, "sim_bt": 37.2, "sim_alb": 3.0, "sim_crp": 4.0, "sim_severity": 3, "sim_reaction": "alert"},
    "99887766": {"sim_sbp": 110, "sim_dbp": 70, "sim_pr": 96, "sim_rr": 22, "sim_bt": 37.6, "sim_alb": 2.6, "sim_crp": 6.0, "sim_severity": 3, "sim_reaction": "verbal response"},
}

def apply_patient_preset(patient_id):
    preset = PATIENT_SIM_PRESETS.get(str(patient_id), {"sim_sbp": 120, "sim_dbp": 80, "sim_pr": 80, "sim_rr": 20, "sim_bt": 36.5, "sim_alb": 4.0, "sim_crp": 0.5, "sim_severity": 3, "sim_reaction": "alert"})
    for k, v in preset.items():
        st.session_state[k] = v
    st.session_state.alarm_confirmed = False

# 시뮬레이션 변수 초기화
for k in ["sim_sbp", "sim_dbp", "sim_pr", "sim_rr", "sim_bt", "sim_alb", "sim_crp", "sim_severity", "sim_reaction"]:
    if k not in st.session_state: st.session_state[k] = 120 if "sbp" in k else (80 if "dbp" in k else 3)

# --------------------------------------------------------------------------------
# 5. 예측 및 분석 함수
# --------------------------------------------------------------------------------
def calculate_risk_score(pt_static):
    if not res: return 0, 0.0, "저위험"
    inputs = {
        "성별": res['gender_mapping'].get(pt_static['gender'], 1),
        "나이": float(pt_static['age']),
        "중증도분류": float(st.session_state.sim_severity),
        "SBP": float(st.session_state.sim_sbp), "DBP": float(st.session_state.sim_dbp),
        "RR": float(st.session_state.sim_rr), "PR": float(st.session_state.sim_pr),
        "BT": float(st.session_state.sim_bt), "내원시 반응": st.session_state.sim_reaction,
        "albumin": float(st.session_state.sim_alb), "crp": float(st.session_state.sim_crp)
    }
    X_input = pd.DataFrame([inputs], columns=res['raw_cols'])
    raw_score = float(res['model'].predict_proba(X_input)[0][1])
    
    if raw_score >= res['cutoff_top20']: group = "고위험"
    elif raw_score >= res['cutoff_top40']: group = "중위험"
    else: group = "저위험"
    
    return min(int(round(raw_score * 100)), 99), raw_score, group

# --------------------------------------------------------------------------------
# 6. 팝업창
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, factors, current_score):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준 분석 결과")
    tab1, tab2 = st.tabs(["🛡️ 맞춤형 간호중재", "📊 AI 판단 근거"])
    with tab1:
        st.markdown("##### 🚨 감지된 위험요인")
        for f in factors: st.error(f"• {f}")
        if st.button("간호 기록 저장", type="primary", use_container_width=True):
            st.session_state.nursing_notes.insert(0, {"time": datetime.datetime.now().strftime('%H:%M'), "writer": "김분당", "content": f"낙상위험({current_score}점) 확인 및 중재 시행."})
            st.rerun()
    with tab2:
        if res and res['importance'] is not None:
            chart = alt.Chart(res['importance']).mark_bar().encode(x='importance', y=alt.Y('feature', sort='-x'), color=alt.value("#0288d1")).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃 (Syntax Error 수정 지점)
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])
curr_pt = PATIENTS_BASE[st.session_state.current_pt_idx]

with col_sidebar:
    st.markdown("### 🏥 재원 환자")
    idx = st.radio("리스트", range(len(PATIENTS_BASE)), format_func=lambda i: f"[{PATIENTS_BASE[i]['bed']}] {PATIENTS_BASE[i]['name']}", label_visibility="collapsed")
    if idx != st.session_state.current_pt_idx:
        st.session_state.current_pt_idx = idx
        apply_patient_preset(PATIENTS_BASE[idx]['id'])
        st.rerun()
    
    fall_score, fall_raw, fall_group = calculate_risk_score(curr_pt)
    is_top20 = fall_raw >= res['cutoff_top20'] if res else False
    
    # [수정] dedent 괄호 위치 수정
    alarm_class = "alarm-active" if (is_top20 and not st.session_state.alarm_confirmed) else ""
    st.markdown(dedent(f"""
        <div class="digital-monitor-container {alarm_class}">
            <div class="score-box">
                <div class="monitor-label">FALL RISK</div>
                <div class="digital-number" style="color: {'#ff5252' if is_top20 else '#00e5ff'};">{fall_score}</div>
            </div>
            <div class="divider-line"></div>
            <div class="score-box">
                <div class="monitor-label">SORE RISK</div>
                <div class="digital-number" style="color: #ffca28;">15</div>
            </div>
        </div>
    """), unsafe_allow_html=True)
    
    factors = ["고령"] if curr_pt['age'] >= 65 else []
    if st.session_state.sim_alb < 3.0: factors.append("알부민 저하")
    
    if st.button("🔍 상세 분석", type="primary", use_container_width=True):
        show_risk_details(curr_pt['name'], factors, fall_score)

with col_main:
    # [수정] dedent 괄호 위치 수정
    st.markdown(dedent(f"""
        <div class="header-container">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:center;">
                    <span style="font-size:1.5em; font-weight:bold; color:white; margin-right:20px;">🏥 SNUH</span>
                    <span class="header-info-text"><b>{curr_pt['name']}</b> ({curr_pt['gender']}/{curr_pt['age']}세)</span>
                    <span class="header-info-text">ID: {curr_pt['id']}</span>
                </div>
                <div style="color:#b0bec5; font-size:0.9em;">{datetime.datetime.now().strftime('%Y-%m-%d')}</div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🛡️ 통합뷰", "💊 오더", "📝 간호기록"])
    with t1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### ⚡ 실시간 데이터 입력")
            st.number_input("SBP", key="sim_sbp")
            st.slider("Albumin", 1.0, 5.0, key="sim_alb", step=0.1)
            st.selectbox("중증도", [1,2,3,4,5], key="sim_severity")
        with c2:
            st.markdown("##### 📊 상태 요약")
            if factors:
                for f in factors: st.markdown(f"<span class='risk-tag'>{f}</span>", unsafe_allow_html=True)

    with t3:
        for note in st.session_state.nursing_notes:
            st.markdown(f"""<div class="note-entry">{note['time']} | {note['content']}</div>""", unsafe_allow_html=True)

# 알람 (Confirm 버튼 포함)
if is_top20 and not st.session_state.alarm_confirmed:
    st.markdown(f"""
        <div class="custom-alert-box">
            <div class="alert-title">🚨 낙상 고위험 감지! ({fall_score}점)</div>
            <div class="alert-content">환자의 상태 변화로 위험도가 상승했습니다.</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("확인 (Confirm)", key="confirm_alarm_btn"):
        confirm_alarm()
        st.rerun()
