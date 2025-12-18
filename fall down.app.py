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
# 1. 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - AI System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------------------------------
# 2. 리소스 로딩 (모델 중요도 로직 포함)
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        resources['model'] = joblib.load('risk_score_model.joblib')
        with open('dashboard_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)
        resources['schema'] = schema
        resources['raw_cols'] = schema.get('raw_input_cols', [])
        resources['gender_mapping'] = schema.get('gender_mapping', {'M': 1, 'F': 0})
        
        ref = np.load('train_score_ref.npz', allow_pickle=True)
        scores_sorted = np.array(ref.get('train_scores_sorted', [])).astype(float)
        resources['train_scores_sorted'] = scores_sorted
        resources['cutoff_top20'] = float(np.quantile(scores_sorted, 0.80))
        resources['cutoff_top40'] = float(np.quantile(scores_sorted, 0.60))

        if hasattr(resources['model'], 'feature_importances_'):
            resources['importance'] = pd.DataFrame({
                'feature': resources['raw_cols'],
                'importance': resources['model'].feature_importances_
            })
        else:
            resources['importance'] = None
    except:
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 3. 데이터 및 함수 정의
# --------------------------------------------------------------------------------
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
    """선택된 환자의 기본 시뮬레이션 값을 세션 상태에 적용"""
    preset = PATIENT_SIM_PRESETS.get(str(patient_id), {
        "sim_sbp": 120, "sim_dbp": 80, "sim_pr": 80, "sim_rr": 20, 
        "sim_bt": 36.5, "sim_alb": 4.0, "sim_crp": 0.5, "sim_severity": 3, "sim_reaction": "alert"
    })
    for k, v in preset.items():
        st.session_state[k] = v
    st.session_state.alarm_confirmed = False

def calculate_risk_score(pt_static):
    """현재 세션 상태의 값을 기반으로 점수 계산"""
    if not res: return 0, 0.0, "저위험"
    
    inputs = {
        "성별": res['gender_mapping'].get(pt_static['gender'], 1),
        "나이": float(pt_static['age']),
        "중증도분류": float(st.session_state.get("sim_severity", 3)),
        "SBP": float(st.session_state.get("sim_sbp", 120)),
        "DBP": float(st.session_state.get("sim_dbp", 80)),
        "RR": float(st.session_state.get("sim_rr", 20)),
        "PR": float(st.session_state.get("sim_pr", 80)),
        "BT": float(st.session_state.get("sim_bt", 36.5)),
        "내원시 반응": st.session_state.get("sim_reaction", "alert"),
        "albumin": float(st.session_state.get("sim_alb", 4.0)),
        "crp": float(st.session_state.get("sim_crp", 0.5))
    }
    
    X_input = pd.DataFrame([inputs], columns=res['raw_cols'])
    raw_score = float(res['model'].predict_proba(X_input)[0][1])
    
    if raw_score >= res['cutoff_top20']: group = "고위험"
    elif raw_score >= res['cutoff_top40']: group = "중위험"
    else: group = "저위험"
    
    return min(int(round(raw_score * 100)), 99), raw_score, group

# --------------------------------------------------------------------------------
# 4. 세션 상태 초기화 및 스타일
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "08:00", "writer": "김분당", "content": "활력징후 정상."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'alarm_confirmed' not in st.session_state: st.session_state.alarm_confirmed = False

st.markdown("""<style>... CSS 생략 (기존과 동일) ...</style>""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 5. 사이드바 (실시간 계산 로직 포함)
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])

with col_sidebar:
    st.markdown("### 🏥 재원 환자")
    # 환자 선택 라디오 버튼
    idx = st.radio("리스트", range(len(PATIENTS_BASE)), 
                   format_func=lambda i: f"[{PATIENTS_BASE[i]['bed']}] {PATIENTS_BASE[i]['name']}", 
                   label_visibility="collapsed")
    
    # 환자가 바뀌었을 때만 프리셋 적용 후 리런
    if idx != st.session_state.current_pt_idx:
        st.session_state.current_pt_idx = idx
        apply_patient_preset(PATIENTS_BASE[idx]['id'])
        st.rerun()

    curr_pt = PATIENTS_BASE[idx]
    
    # [핵심] 모든 위젯의 최신 값을 반영하여 계산
    fall_score, fall_raw, fall_group = calculate_risk_score(curr_pt)
    is_top20 = fall_raw >= res['cutoff_top20'] if res else False

    # 계기판 출력
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

    if st.button("🚨 알람 확인 (Confirm)", use_container_width=True) and is_top20:
        st.session_state.alarm_confirmed = True
        st.rerun()

# --------------------------------------------------------------------------------
# 6. 메인 패널
# --------------------------------------------------------------------------------
with col_main:
    # 헤더 출력
    st.markdown(dedent(f"""
        <div class="header-container">
            <span style="font-size:1.5em; font-weight:bold; color:white;">🏥 SNUH | {curr_pt['name']} ({curr_pt['id']})</span>
        </div>
    """), unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🛡️ 통합뷰 (AI Simulation)", "💊 오더", "📝 간호기록"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### ⚡ 실시간 데이터 입력")
            with st.container(border=True):
                # [중요] 버튼 클릭 시 상태 변경 후 반드시 rerun()을 호출해야 사이드바 점수가 갱신됨
                if st.button("🔁 현재 환자 예시값으로 초기화", use_container_width=True):
                    apply_patient_preset(curr_pt["id"])
                    st.rerun() 
                
                # 각 입력 위젯은 st.session_state[key]와 자동 연동됨
                st.number_input("SBP (수축기)", step=5, key="sim_sbp")
                st.slider("Albumin (영양)", 1.0, 5.0, step=0.1, key="sim_alb")
                st.selectbox("중증도분류", [1, 2, 3, 4, 5], key="sim_severity")
                
        with c2:
            st.markdown("##### 📊 실시간 스코어 가이드")
            st.write(f"현재 예측 확률: {fall_raw:.4f}")
            if is_top20:
                st.error("⚠️ 고위험군: 침상 난간 확인 및 낙상 주의 표지판 부착 필요")
            else:
                st.success("✅ 저위험군: 일반적 낙상 예방 지침 준수")

    with tab3:
        for note in st.session_state.nursing_notes:
            st.markdown(f"<div class='note-entry'>{note['time']} | {note['content']}</div>", unsafe_allow_html=True)
