import streamlit as st
import pandas as pd
import datetime
import time
import joblib
import numpy as np
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
        display: flex; justify-content: space-around; align-items: center;
    }
    @keyframes blink { 50% { border-color: #ff5252; box-shadow: 0 0 15px #ff5252; } }
    .alarm-active { animation: blink 1s infinite; border: 2px solid #ff5252 !important; }

    .score-box { text-align: center; width: 45%; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 36px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #90a4ae; font-size: 12px; font-weight: bold; letter-spacing: 1px; }
    .divider-line { width: 1px; height: 50px; background-color: #444; }

    /* 알람 박스 */
    .custom-alert-box {
        position: fixed; bottom: 30px; right: 30px; width: 350px;
        background-color: #263238; border-left: 8px solid #ff5252;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6); border-radius: 4px;
        padding: 20px; z-index: 9999; animation: slideIn 0.5s ease-out;
    }
    @keyframes slideIn { from { transform: translateX(120%); } to { transform: translateX(0); } }
    
    .alert-title { color: #ff5252; font-weight: bold; font-size: 1.3em; margin-bottom: 10px; }
    .alert-content { color: #eceff1; font-size: 1.0em; margin-bottom: 15px; line-height: 1.4; }
    .alert-factors { background-color: #3e2723; padding: 10px; border-radius: 4px; margin-bottom: 15px; color: #ffcdd2; font-size: 0.95em; border: 1px solid #ff5252; }
    
    .btn-confirm {
        display: block; background-color: #d32f2f; color: white; text-align: center; padding: 10px; 
        border-radius: 4px; font-weight: bold; cursor: pointer; transition: 0.2s; text-decoration: none;
    }
    .btn-confirm:hover { background-color: #b71c1c; }

    /* 기타 UI */
    .note-entry { background-color: #2c3e50; padding: 15px; border-radius: 5px; border-left: 4px solid #0288d1; margin-bottom: 10px; }
    .note-time { color: #81d4fa; font-weight: bold; margin-bottom: 5px; font-size: 0.9em; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
    .legend-item { display: inline-block; padding: 2px 8px; margin-right: 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; text-align: center; }
    
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    .stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #263238; color: #b0bec5; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #0277bd; color: white; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 리소스 로딩
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        resources['model'] = joblib.load('rf_fall_model.joblib')
        df_cols = pd.read_csv('rf_model_feature_columns.csv')
        resources['features'] = df_cols['feature'].tolist()
        try:
            resources['importance'] = pd.read_csv('rf_feature_importance_top10.csv')
        except:
            resources['importance'] = None
    except Exception as e:
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 4. 예측 및 보정 함수 (수정됨!)
# --------------------------------------------------------------------------------
def calculate_risk_score(pt_static, input_vals):
    # 1. AI 모델 예측
    base_score = 0
    if res and 'model' in res:
        model = res['model']
        feature_cols = res['features']
        
        input_data = {col: 0 for col in feature_cols}
        
        # 데이터 매핑
        input_data['나이'] = pt_static['age']
        input_data['성별'] = 1 if pt_static['gender'] == 'M' else 0
        input_data['SBP'] = input_vals['sbp']
        input_data['DBP'] = input_vals['dbp']
        input_data['PR'] = input_vals['pr']
        input_data['RR'] = input_vals['rr']
        input_data['BT'] = input_vals['bt']
        input_data['albumin'] = input_vals['albumin']
        input_data['crp'] = input_vals['crp']
        
        mental_map = {"명료(Alert)": "alert", "기면(Drowsy)": "verbal response", "혼미(Stupor)": "painful response"}
        m_val = mental_map.get(input_vals['mental'], "alert")
        if f"내원시 반응_{m_val}" in input_data: input_data[f"내원시 반응_{m_val}"] = 1

        try:
            input_df = pd.DataFrame([input_data])
            input_df = input_df[feature_cols]
            prob = model.predict_proba(input_df)[0][1]
            base_score = int(prob * 100)
        except:
            base_score = 10 

    # 2. [수정] 보정 로직 (가산점)
    calibration_score = 0
    
    # (1) 알부민 3.0 미만이면 +30점
    if input_vals['albumin'] < 3.0:
        calibration_score += 30
        
    # (2) 고위험 약물 복용 시(True) +30점
    if input_vals['meds'] == True:
        calibration_score += 30
        
    # (3) 나이 70세 이상 시 +10점
    if pt_static['age'] >= 70:
        calibration_score += 10
        
    # (4) 활력징후 이상
    if input_vals['sbp'] < 90 or input_vals['sbp'] > 180: calibration_score += 15
    if input_vals['pr'] > 100: calibration_score += 10
    if input_vals['bt'] > 37.5: calibration_score += 5

    final_score = base_score + calibration_score
    return min(final_score, 99)

# --------------------------------------------------------------------------------
# 5. 데이터 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'alarm_confirmed' not in st.session_state: st.session_state.alarm_confirmed = False

# 알람 확인 (단순 닫기)
if "confirm_alarm" in st.query_params:
    st.session_state.alarm_confirmed = True
    st.query_params.clear()

PATIENTS_BASE = [
    {"id": "12345678", "bed": "04-01", "name": "김수면", "gender": "M", "age": 78, "diag": "Pneumonia", "doc": "김뇌혈", "nurse": "이간호"},
    {"id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 65, "diag": "Stomach Cancer", "doc": "박위장", "nurse": "최간호"},
    {"id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 82, "diag": "Femur Fracture", "doc": "최정형", "nurse": "김간호"},
    {"id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32, "diag": "Appendicitis", "doc": "이외과", "nurse": "박간호"},
]

# --------------------------------------------------------------------------------
# 6. 팝업창
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, factors, current_score, input_vals):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    tab1, tab2 = st.tabs(["🛡️ 맞춤형 간호중재", "📊 AI 판단 근거"])
    
    with tab1:
        c1, c2, c3 = st.columns([1, 0.2, 1])
        with c1:
            st.markdown("##### 🚨 감지된 위험요인")
            with st.container(border=True):
                if factors:
                    for f in factors: st.error(f"• {f}")
                else: st.write("특이 위험 요인 없음")
        with c2:
            st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)
        with c3:
            st.markdown("##### ✅ 필수 간호 진술문")
            with st.container(border=True):
                chk_rail = st.checkbox("침상 난간(Side Rail) 올림 확인", value=(current_score >= 40))
                chk_med = st.checkbox("💊 수면제 투여 후 30분 관찰", value=input_vals['meds'])
                chk_nutri = st.checkbox("🥩 영양팀 협진 의뢰", value=(input_vals['albumin'] < 3.0))
                chk_edu = st.checkbox("📢 낙상 예방 교육 및 호출기 위치 안내", value=True)

        st.markdown("---")
        if st.button("간호 수행 완료 및 기록 저장 (Auto-Charting)", type="primary", use_container_width=True):
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            risk_str = ", ".join(factors) if factors else "없음"
            actions = []
            if chk_rail: actions.append("침상난간 올림 확인")
            if chk_med: actions.append("투약 후 관찰")
            if chk_nutri: actions.append("영양팀 협진")
            if chk_edu: actions.append("예방 교육")
            
            note_content = f"낙상위험평가({current_score}점) -> 위험요인({risk_str}) 확인 -> 중재({', '.join(actions)}) 시행함."
            st.session_state.nursing_notes.insert(0, {"time": current_time, "writer": "김분당", "content": note_content})
            st.toast("저장되었습니다!")
            time.sleep(1)
            st.rerun()

    with tab2:
        st.markdown("##### 🔍 환자 맞춤형 위험 요인 (Top 10)")
        if res and res['importance'] is not None:
            df_imp = res['importance'].copy().sort_values('importance', ascending=True).tail(10)
            colors = []
            for feature in df_imp['feature']:
                color = "#e0e0e0"
                # 알부민 3.0 미만 시 빨간색 강조
                if feature == "albumin" and input_vals['albumin'] < 3.0: color = "#ff5252"
                elif feature == "나이" and input_vals['age'] >= 65: color = "#ff5252"
                elif feature == "SBP" and (input_vals['sbp'] < 100 or input_vals['sbp'] > 160): color = "#ff5252"
                elif feature == "PR" and input_vals['pr'] > 100: color = "#ff5252"
                colors.append(color)
            df_imp['color'] = colors
            
            chart = alt.Chart(df_imp).mark_bar().encode(
                x=alt.X('importance', title='기여도'),
                y=alt.Y('feature', sort='-x', title='변수명'),
                color=alt.Color('color', scale=None)
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("중요도 데이터가 없습니다.")

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃 구성
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])
curr_pt_base = PATIENTS_BASE[st.session_state.current_pt_idx]

# [좌측 패널]
with col_sidebar:
    st.selectbox("근무 DUTY", ["Day", "Evening", "Night"])
    st.divider()

    st.markdown("### 🏥 재원 환자")
    idx = st.radio("환자 리스트", range(len(PATIENTS_BASE)), format_func=lambda i: f"[{PATIENTS_BASE[i]['bed']}] {PATIENTS_BASE[i]['name']}", label_visibility="collapsed")
    if idx != st.session_state
