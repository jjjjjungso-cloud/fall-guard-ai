import streamlit as st
import pandas as pd
import datetime
import time
import joblib
import numpy as np
import altair as alt  # 시각화 라이브러리

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
# 2. 스타일 (CSS) - EMR 다크모드, 알람 효과, 디지털 계기판
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

    /* 디지털 계기판 (검은색 박스) */
    .digital-monitor-container {
        background-color: #000000; border: 2px solid #455a64; border-radius: 8px;
        padding: 15px; margin-top: 15px; margin-bottom: 5px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9);
        transition: border 0.3s;
    }
    /* 알람 애니메이션 (빨간 테두리 깜빡임) */
    @keyframes blink { 50% { border-color: #ff5252; box-shadow: 0 0 15px #ff5252; } }
    .alarm-active { animation: blink 1s infinite; border: 2px solid #ff5252 !important; }

    .digital-number {
        font-family: 'Consolas', monospace; font-size: 40px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #90a4ae; font-size: 12px; font-weight: bold; letter-spacing: 1px; }

    /* 간호기록 */
    .note-entry {
        background-color: #2c3e50; padding: 15px; border-radius: 5px;
        border-left: 4px solid #0288d1; margin-bottom: 10px; font-size: 0.95em; line-height: 1.5;
    }
    
    /* 기타 UI */
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    .stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 리소스 로딩 (모델, 변수명, 중요도 데이터)
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        # 1. AI 모델
        resources['model'] = joblib.load('rf_fall_model.joblib')
        # 2. 변수 리스트
        df_cols = pd.read_csv('rf_model_feature_columns.csv')
        resources['features'] = df_cols['feature'].tolist()
        # 3. 중요도 데이터 (XAI용)
        try:
            resources['importance'] = pd.read_csv('rf_feature_importance_top10.csv')
        except:
            resources['importance'] = None
    except Exception as e:
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 4. 예측 함수
# --------------------------------------------------------------------------------
def predict_fall_risk(input_vals):
    if res is None or 'model' not in res: return 0
    
    model = res['model']
    feature_cols = res['features']
    
    input_data = {col: 0 for col in feature_cols}
    
    # 입력값 매핑
    input_data['나이'] = input_vals.get('age', 60)
    input_data['SBP'] = input_vals.get('sbp', 120)
    input_data['DBP'] = input_vals.get('dbp', 80)
    input_data['PR'] = input_vals.get('pr', 80)
    input_data['RR'] = input_vals.get('rr', 20)
    input_data['BT'] = input_vals.get('bt', 36.5)
    input_data['albumin'] = input_vals.get('albumin', 4.0)
    input_data['crp'] = input_vals.get('crp', 0.5)
    
    if input_vals.get('gender') == 'M': input_data['성별'] = 1
    
    # 증상/상태 매핑 (간단 예시)
    if 'symptom' in input_vals:
        s_col = f"주증상_{input_vals['symptom']}"
        if s_col in input_data: input_data[s_col] = 1
        
    try:
        input_df = pd.DataFrame([input_data])
        input_df = input_df[feature_cols]
        prob = model.predict_proba(input_df)[0][1]
        return int(prob * 100)
    except:
        return 0

# --------------------------------------------------------------------------------
# 5. 팝업창 (XAI + 스마트 차팅)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, factors, current_score, input_vals):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    tab1, tab2 = st.tabs(["🛡️ 맞춤형 간호중재", "📊 AI 판단 근거 (XAI)"])
    
    # [Tab 1] 간호 중재 & 자동 차팅
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
                chk_med = st.checkbox("💊 수면제 투여 후 30분 관찰", value=("수면제" in str(factors)))
                chk_nutri = st.checkbox("🥩 영양팀 협진 의뢰", value=("알부민" in str(factors)))
                chk_edu = st.checkbox("📢 낙상 예방 교육 및 호출기 위치 안내", value=True)

        st.markdown("---")
        if st.button("간호 수행 완료 및 기록 저장 (Auto-Charting)", type="primary", use_container_width=True):
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            risk_str = ", ".join(factors) if factors else "없음"
            actions = []
            if chk_rail: actions.append("침상난간 2개 이상 올림 확인")
            if chk_med: actions.append("수면제 투여 후 30분간 의식상태 관찰")
            if chk_nutri: actions.append("영양 불균형 교정을 위해 협진 의뢰")
            if chk_edu: actions.append("낙상 예방 교육 시행")
            
            note_content = f"낙상위험평가({current_score}점) -> 위험요인({risk_str}) 확인 -> 중재({', '.join(actions)}) 시행함. 안전한 환경 조성 후 관찰함."
            st.session_state.nursing_notes.insert(0, {"time": current_time, "writer": "김분당", "content": note_content})
            st.toast("✅ 간호기록 저장 완료!", icon="💾")
            time.sleep(1)
            st.rerun()

    # [Tab 2] XAI 시각화 (환자 맞춤형 하이라이트)
    with tab2:
        st.markdown("##### 🔍 환자 맞춤형 위험 요인 분석")
        st.caption("AI 중요도 상위 항목 중, **현재 환자에게 해당되는 위험 항목을 붉은색**으로 표시합니다.")
        
        if res and res['importance'] is not None:
            df_imp = res['importance'].copy().sort_values('importance', ascending=True).tail(10)
            
            # 색상/텍스트 로직
            colors = []
            texts = []
            for feature in df_imp['feature']:
                color = "#e0e0e0" # 기본 회색
                txt = ""
                
                # 시뮬레이션 입력값(input_vals)과 비교
                if feature == "나이":
                    val = input_vals.get('age', 0)
                    if val >= 65: color = "#ff5252"; txt = f"{val}세 (고령)"
                    else: txt = f"{val}세"
                elif feature == "albumin":
                    val = input_vals.get('albumin', 4.0)
                    if val < 3.0: color = "#ff5252"; txt = f"{val} (저하)"
                    else: txt = f"{val}"
                elif feature == "SBP":
                    val = input_vals.get('sbp', 120)
                    if val < 100 or val > 160: color = "#ff5252"; txt = f"{val} (비정상)"
                    else: txt = f"{val}"
                else:
                    txt = "-"
                
                colors.append(color)
                texts.append(txt)
            
            df_imp['color'] = colors
            df_imp['text'] = texts
            
            # Altair 차트
            chart = alt.Chart(df_imp).mark_bar().encode(
                x=alt.X('importance', title='기여도'),
                y=alt.Y('feature', sort='-x', title='변수명'),
                color=alt.Color('color', scale=None),
                tooltip=['feature', 'importance']
            ).properties(height=350)
            
            text_layer = chart.mark_text(align='left', dx=3).encode(text='text')
            st.altair_chart(chart + text_layer, use_container_width=True)
        else:
            st.info("중요도 데이터 파일이 없습니다.")

# --------------------------------------------------------------------------------
# 6. 데이터 초기화 및 기본 환자 정보
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0

PATIENTS_BASE = [
    {"id": "12345678", "bed": "04-01", "name": "김수면", "gender": "M", "diag": "Pneumonia", "doc": "김뇌혈", "nurse": "이간호"},
    {"id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "diag": "Stomach Cancer", "doc": "박위장", "nurse": "최간호"},
    {"id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "diag": "Femur Fracture", "doc": "최정형", "nurse": "김간호"},
    {"id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "diag": "Appendicitis", "doc": "이외과", "nurse": "박간호"},
]

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])

# [좌측 패널]
with col_sidebar:
    st.selectbox("근무 DUTY", ["Day", "Evening", "Night"])
    st.divider()

    # 1. 환자 선택
    st.markdown("### 🏥 재원 환자")
    idx = st.radio("환자 리스트", range(len(PATIENTS_BASE)), format_func=lambda i: f"[{PATIENTS_BASE[i]['bed']}] {PATIENTS_BASE[i]['name']}", label_visibility="collapsed")
    st.session_state.current_pt_idx = idx
    curr_pt_base = PATIENTS_BASE[idx]
    st.markdown("---")
    
    # 2. [핵심] 실시간 데이터 입력 (Simulation)
    with st.expander("⚡ 실시간 데이터 입력 (Simulation)", expanded=True):
        age_val = 68 if idx == 0 else (79 if idx == 1 else 45)
        
        input_vals = {}
        input_vals['age'] = st.number_input("나이 (Age)", value=age_val, step=1)
        c1, c2 = st.columns(2)
        input_vals['sbp'] = c1.number_input("SBP", value=120, step=10)
        input_vals['dbp'] = c2.number_input("DBP", value=80, step=10)
        
        input_vals['albumin'] = st.slider("Albumin (영양)", 1.0, 5.5, 3.5, 0.1)
        
        # 고정값 (데모용)
        input_vals['pr'] = 80; input_vals['rr'] = 20; input_vals['bt'] = 36.5; input_vals['crp'] = 0.5
        input_vals['gender'] = curr_pt_base['gender']
        input_vals['symptom'] = "OTHERS"; input_vals['mental'] = "alert"
        
        # 위험 요인 텍스트 생성
        detected_factors = []
        if input_vals['age'] >= 65: detected_factors.append("고령")
        if input_vals['albumin'] < 3.0: detected_factors.append("알부민 저하")
        if input_vals['sbp'] < 100: detected_factors.append("저혈압")

    # 3. AI 예측 실행
    fall_score = predict_fall_risk(input_vals)
    sore_score = 15
    
    # 4. 디지털 계기판 + [알람 기능]
    f_color = "#ff5252" if fall_score >= 60 else ("#ffca28" if fall_score >= 30 else "#00e5ff")
    s_color = "#ff5252" if sore_score >= 18 else ("#ffca28" if sore_score >= 15 else "#00e5ff")
    
    # [알람 로직] 점수가 60 이상이면 테두리 깜빡임 + Toast 팝업
    alarm_class = ""
    if fall_score >= 60:
        alarm_class = "alarm-active"
        st.toast(f"🚨 [경고] {curr_pt_base['name']}님 낙상 고위험 감지! ({fall_score}점)", icon="🚨")

    st.markdown(f"""
    <div class="digital-monitor-container {alarm_class}">
        <div class="monitor-row">
            <div style="text-align:center; width:45%; border-right:1px solid #444;">
                <div class="monitor-label">FALL RISK</div>
                <div class="digital-number" style="color: {f_color};">{fall_score}</div>
            </div>
            <div style="text-align:center; width:45%;">
                <div class="monitor-label">SORE RISK</div>
                <div class="digital-number" style="color: {s_color};">{sore_score}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="primary", use_container_width=True):
        show_risk_details(curr_pt_base['name'], detected_factors, fall_score, input_vals)

# [우측 메인 패널]
with col_main:
    st.markdown(f"""
    <div class="header-container">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center;">
                <span style="font-size:1.5em; font-weight:bold; color:white; margin-right:20px;">🏥 SNUH</span>
                <span class="header-info-text"><span class="header-label">환자명:</span> <b>{curr_pt_base['name']}</b> ({curr_pt_base['id']})</span>
                <span class="header-info-text"><span class="header-label">성별:</span> {curr_pt_base['gender']}</span>
                <span class="header-info-text"><span class="header-label">진단명:</span> <span style="color:#4fc3f7;">{curr_pt_base['diag']}</span></span>
            </div>
            <div style="color:#b0bec5; font-size:0.9em;">김분당 간호사 | {datetime.datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🛡️ 통합뷰", "💊 오더", "📝 간호기록(Auto-Note)"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info("👈 좌측 '실시간 데이터 입력' 패널에서 수치를 변경해보세요. AI가 즉시 위험도를 재계산합니다.")
            st.markdown(f"**[현재 입력된 V/S 및 Lab]**")
            st.json(input_vals)
        with c2:
            st.markdown(f"**[감지된 위험 요인]**")
            for f in detected_factors:
                st.markdown(f"<span class='risk-tag'>{f}</span>", unsafe_allow_html=True)

    with tab2: st.write("오더 화면입니다.")

    with tab3:
        st.markdown("##### 📋 간호진술문 (Nursing Note)")
        for note in st.session_state.nursing_notes:
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-time">📅 {note['time']} | 작성자: {note['writer']}</div>
                <div>{note['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.text_area("추가 기록", height=100)
        st.button("저장")

st.markdown("---")
legends = [("수술전","#e57373"), ("수술중","#ba68c8"), ("검사후","#7986cb"), ("퇴원","#81c784"), ("신규오더","#ffb74d")]
html = '<div style="display:flex; gap:10px;">' + "".join([f'<span class="legend-item" style="background:{c}">{l}</span>' for l,c in legends]) + '</div>'
st.markdown(html, unsafe_allow_html=True)
