import streamlit as st
import pandas as pd
import datetime
import time
import joblib
import numpy as np
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
    }
    @keyframes slideIn { from { transform: translateX(120%); } to { transform: translateX(0); } }
    .alert-title { color: #ff5252; font-weight: bold; font-size: 1.4em; margin-bottom: 10px; }
    .alert-factors { background-color: #3e2723; padding: 12px; border-radius: 6px; color: #ffcdd2; font-size: 0.95em; border: 1px solid #ff5252; }

    /* 태그 및 기타 */
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
    .note-entry { background-color: #2c3e50; padding: 15px; border-radius: 5px; border-left: 4px solid #0288d1; margin-bottom: 10px; }
    .legend-item { display: inline-block; padding: 2px 8px; margin-right: 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 리소스 로딩 (에러 수정: importance 추출 추가)
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        # 1) 모델 로드
        model = joblib.load('risk_score_model.joblib')
        resources['model'] = model

        # 2) schema 로드
        with open('dashboard_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)
        resources['schema'] = schema
        resources['raw_cols'] = schema.get('raw_input_cols', [])
        resources['gender_mapping'] = schema.get('gender_mapping', {'M': 1, 'F': 0})
        resources['category_options'] = schema.get('category_options', {})

        # 3) cutoff (Top 20/40)
        ref = np.load('train_score_ref.npz', allow_pickle=True)
        resources['cutoff_top20'] = float(ref['cutoff_top20']) if 'cutoff_top20' in ref.files else 0.8
        resources['cutoff_top40'] = float(ref['cutoff_top40']) if 'cutoff_top40' in ref.files else 0.6

        # 4) [중요] 피처 중요도 추출 (KeyError 방지)
        if hasattr(model, 'feature_importances_'):
            resources['importance'] = pd.DataFrame({
                'feature': resources['raw_cols'],
                'importance': model.feature_importances_
            })
        elif hasattr(model, 'coef_'): # 로지스틱 회귀 등
            resources['importance'] = pd.DataFrame({
                'feature': resources['raw_cols'],
                'importance': np.abs(model.coef_[0])
            })
        else:
            resources['importance'] = None
            
    except Exception as e:
        st.error(f"리소스 로드 중 오류 발생: {e}")
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 4. 상태 및 데이터 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'alarm_confirmed' not in st.session_state: st.session_state.alarm_confirmed = False

# 시뮬레이션 기본값 설정
defaults = {
    'sim_sbp': 120, 'sim_dbp': 80, 'sim_pr': 80, 'sim_rr': 20, 
    'sim_bt': 36.5, 'sim_alb': 4.0, 'sim_crp': 0.5, 
    'sim_mental': '명료(Alert)', 'sim_meds': False, 'sim_severity': 3, 'sim_reaction': 'alert'
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

PATIENTS_BASE = [
    {"id": "12345678", "bed": "04-01", "name": "김수면", "gender": "M", "age": 78, "diag": "Pneumonia", "doc": "김뇌혈", "nurse": "이간호"},
    {"id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 65, "diag": "Stomach Cancer", "doc": "박위장", "nurse": "최간호"},
    {"id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 82, "diag": "Femur Fracture", "doc": "최정형", "nurse": "김간호"},
    {"id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32, "diag": "Appendicitis", "doc": "이외과", "nurse": "박간호"},
]

# --------------------------------------------------------------------------------
# 5. 예측 및 요인 탐지 함수 (통합)
# --------------------------------------------------------------------------------
def calculate_risk_and_factors(pt_static):
    if not res: return 0, 0.0, "저위험", []

    # 1) 모델 입력값 구성
    inputs = {
        "성별": res['gender_mapping'].get(pt_static['gender'], 1),
        "나이": float(pt_static['age']),
        "중증도분류": float(st.session_state.sim_severity),
        "SBP": float(st.session_state.sim_sbp),
        "DBP": float(st.session_state.sim_dbp),
        "RR": float(st.session_state.sim_rr),
        "PR": float(st.session_state.sim_pr),
        "BT": float(st.session_state.sim_bt),
        "내원시 반응": st.session_state.sim_reaction,
        "albumin": float(st.session_state.sim_alb),
        "crp": float(st.session_state.sim_crp),
    }

    # 2) 점수 예측
    X_input = pd.DataFrame([inputs], columns=res['raw_cols'])
    raw_score = float(res['model'].predict_proba(X_input)[0][1])
    
    if raw_score >= res['cutoff_top20']: group = "고위험"
    elif raw_score >= res['cutoff_top40']: group = "중위험"
    else: group = "저위험"

    display_score = min(int(round(raw_score * 100)), 100)

    # 3) 위험 요인 탐지 (규칙 기반)
    factors = []
    if pt_static['age'] >= 65: factors.append("고령")
    if st.session_state.sim_alb < 3.0: factors.append("알부민 저하")
    if st.session_state.sim_crp >= 5.0: factors.append("CRP 상승")
    if st.session_state.sim_sbp < 100: factors.append("저혈압")
    if st.session_state.sim_pr > 100: factors.append("빈맥")
    if st.session_state.sim_severity >= 4: factors.append("중증도 높음")
    if st.session_state.sim_meds: factors.append("고위험 약물")

    return display_score, raw_score, group, factors

# --------------------------------------------------------------------------------
# 6. 팝업 상세창
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, factors, current_score):
    st.info(f"🕒 분석 기준: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    tab1, tab2 = st.tabs(["🛡️ 맞춤형 간호중재", "📊 AI 판단 근거"])
    
    with tab1:
        c1, _, c2 = st.columns([1, 0.1, 1])
        with c1:
            st.markdown("##### 🚨 감지된 위험요인")
            if factors:
                for f in factors: st.error(f"• {f}")
            else: st.write("특이 사항 없음")
        with c2:
            st.markdown("##### ✅ 필수 간호 중재")
            chk_rail = st.checkbox("침상 난간 올림 확인", value=(current_score >= 40))
            chk_med = st.checkbox("수면제 투여 후 관찰", value=st.session_state.sim_meds)
            chk_edu = st.checkbox("낙상 예방 교육 시행", value=True)

        if st.button("간호 기록 저장 (Auto-Note)", type="primary", use_container_width=True):
            note = f"낙상위험평가({current_score}점): {', '.join(factors)} 확인됨. 중재 시행함."
            st.session_state.nursing_notes.insert(0, {"time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), "writer": "김분당", "content": note})
            st.toast("기록되었습니다!")
            time.sleep(1)
            st.rerun()

    with tab2:
        st.markdown("##### 🔍 피처 기여도 (Model Importance)")
        if res and res['importance'] is not None:
            # 
            chart = alt.Chart(res['importance']).mark_bar().encode(
                x=alt.X('importance:Q', title='기여도'),
                y=alt.Y('feature:N', sort='-x', title='변수명'),
                color=alt.value("#0288d1")
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("중요도 데이터를 불러올 수 없습니다.")

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])

with col_sidebar:
    st.markdown("### 🏥 환자 리스트")
    idx = st.radio("Bed No.", range(len(PATIENTS_BASE)), format_func=lambda i: f"[{PATIENTS_BASE[i]['bed']}] {PATIENTS_BASE[i]['name']}", label_visibility="collapsed")
    
    if idx != st.session_state.current_pt_idx:
        st.session_state.current_pt_idx = idx
        st.session_state.alarm_confirmed = False
        st.rerun()

    curr_pt = PATIENTS_BASE[idx]
    f_score, f_raw, f_group, f_factors = calculate_risk_and_factors(curr_pt)
    
    # 계기판
    is_danger = (f_raw >= res['cutoff_top20']) if res else False
    if not is_danger: st.session_state.alarm_confirmed = False
    
    alarm_class = "alarm-active" if (is_danger and not st.session_state.alarm_confirmed) else ""
    st.markdown(f"""
    <div class="digital-monitor-container {alarm_class}">
        <div class="score-box">
            <div class="monitor-label">FALL RISK</div>
            <div class="digital-number" style="color: {'#ff5252' if is_danger else '#00e5ff'};">{f_score}</div>
        </div>
        <div class="divider-line"></div>
        <div class="score-box">
            <div class="monitor-label">SORE RISK</div>
            <div class="digital-number" style="color: #ffca28;">15</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if is_danger and not st.session_state.alarm_confirmed:
        if st.button("🚨 알람 확인 (Confirm)", type="primary", use_container_width=True):
            st.session_state.alarm_confirmed = True
            st.rerun()

    if st.button("🔍 상세 분석 및 중재", use_container_width=True):
        show_risk_details(curr_pt['name'], f_factors, f_score)

with col_main:
    st.markdown(f"""
    <div class="header-container">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:1.3em; font-weight:bold;">🏥 {curr_pt['name']} ({curr_pt['gender']}/{curr_pt['age']}세) | ID: {curr_pt['id']}</div>
            <div style="color:#aaa;">{curr_pt['diag']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🛡️ 통합 뷰", "💊 오더", "📝 간호기록"])
    
    with t1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### ⚡ 실시간 데이터 입력")
            with st.container(border=True):
                st.number_input("SBP", key="sim_sbp")
                st.number_input("PR", key="sim_pr")
                st.slider("Albumin", 1.0, 5.0, key="sim_alb", step=0.1)
                st.number_input("CRP", key="sim_crp", step=0.1)
                st.selectbox("중증도분류", [1,2,3,4,5], index=2, key="sim_severity")
                st.checkbox("💊 고위험 약물 복용", key="sim_meds")
        with c2:
            st.markdown("##### 📊 상태 요약")
            if f_factors:
                for f in f_factors: st.markdown(f"<span class='risk-tag'>{f}</span>", unsafe_allow_html=True)
            else: st.info("정상 범위 내 관리 중")

    with t3:
        for note in st.session_state.nursing_notes:
            st.markdown(f"""<div class="note-entry"><b>{note['time']}</b><br>{note['content']}</div>""", unsafe_allow_html=True)

# 하단 고정 알람 박스 (res['importance'] 에러 방지 완료)
if is_danger and not st.session_state.alarm_confirmed:
    st.markdown(f"""
    <div class="custom-alert-box">
        <div class="alert-title">🚨 낙상 위험 급증!</div>
        <div class="alert-factors"><b>주요 요인:</b> {", ".join(f_factors) if f_factors else "복합 요인"}</div>
    </div>
    """, unsafe_allow_html=True)
