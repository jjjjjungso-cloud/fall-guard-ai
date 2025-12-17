import streamlit as st
import pandas as pd
import datetime
import time
import joblib  # 모델 로딩용 라이브러리
import numpy as np

# --------------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - Smart Charting",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------------------------------------
# 2. [핵심] AI 모델 및 설정 로딩
# --------------------------------------------------------------------------------
@st.cache_resource
def load_ai_model():
    try:
        # 1. 모델 파일 로딩
        model = joblib.load('rf_fall_model.joblib')
        
        # 2. 학습할 때 썼던 컬럼 이름 로딩 (순서 중요!)
        # csv 파일을 읽어서 컬럼 리스트로 변환
        feature_df = pd.read_csv('rf_model_feature_columns.csv')
        feature_columns = feature_df['feature'].tolist()
        
        return model, feature_columns
    except Exception as e:
        st.error(f"모델 파일 로딩 실패: {e}")
        return None, []

model, feature_cols = load_ai_model()

# --------------------------------------------------------------------------------
# 3. [핵심] 환자 데이터 -> AI 입력 데이터 변환 함수
# --------------------------------------------------------------------------------
def predict_fall_risk(patient_info):
    if model is None: return 0  # 모델 없으면 0점 반환

    # 1. 모델이 필요한 모든 변수를 0으로 초기화한 딕셔너리 생성
    input_data = {col: 0 for col in feature_cols}
    
    # 2. 환자 정보를 AI 변수에 매핑 (One-Hot Encoding 수동 처리)
    # (주의: 실제 병원 데이터 연동 시에는 이 부분이 자동화되어야 함)
    
    # [수치형 변수 매핑]
    input_data['나이'] = patient_info.get('age', 60)
    input_data['SBP'] = patient_info.get('sbp', 120) # 혈압(수축기)
    input_data['DBP'] = patient_info.get('dbp', 80)  # 혈압(이완기)
    input_data['PR'] = patient_info.get('pr', 80)    # 맥박
    input_data['RR'] = patient_info.get('rr', 20)    # 호흡
    input_data['BT'] = patient_info.get('bt', 36.5)  # 체온
    input_data['albumin'] = patient_info.get('albumin', 4.0)
    input_data['crp'] = patient_info.get('crp', 0.5)
    
    # [범주형 변수 매핑] - 예: 성별이 남자면 '성별' 컬럼에 1 (모델 학습 방식에 따라 다를 수 있음)
    if patient_info.get('gender') == 'M':
        input_data['성별'] = 1  # 학습 데이터가 남성을 1로 했다고 가정
    else:
        input_data['성별'] = 0

    # [원-핫 인코딩 변수 매핑] - 예: '내원시 반응_alert'
    # 환자 정보에 'mental'이 'alert'이면 해당 컬럼을 1로 설정
    mental_status = patient_info.get('mental', 'alert').lower()
    if f"내원시 반응_{mental_status}" in input_data:
        input_data[f"내원시 반응_{mental_status}"] = 1
        
    # [증상 매핑]
    symptom = patient_info.get('symptom', 'OTHERS')
    if f"주증상_{symptom}" in input_data:
        input_data[f"주증상_{symptom}"] = 1

    # 3. 데이터프레임으로 변환 (모델 입력용)
    input_df = pd.DataFrame([input_data])
    
    # 컬럼 순서 강제 정렬 (매우 중요)
    input_df = input_df[feature_cols]

    # 4. 예측 수행
    try:
        # predict_proba는 [0일확률, 1일확률]을 반환함. 1(낙상)일 확률을 가져옴
        prob = model.predict_proba(input_df)[0][1]
        score = int(prob * 100)
        return score
    except:
        return 0

# --------------------------------------------------------------------------------
# 4. 스타일 (CSS)
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    .stApp { background-color: #1e252b; color: #e0e0e0; font-family: 'Noto Sans KR', sans-serif; }
    .header-container { background-color: #263238; padding: 10px 20px; border-radius: 5px; border-top: 3px solid #0288d1; box-shadow: 0 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px; }
    .header-info-text { font-size: 1.1em; color: #eceff1; margin-right: 15px; }
    .header-label { font-size: 0.8em; color: #b0bec5; }
    .patient-card { padding: 8px; background-color: #2c3e50; border-left: 4px solid #546e7a; border-radius: 4px; margin-bottom: 5px; cursor: pointer; }
    .digital-monitor-container { background-color: #000000; border: 2px solid #455a64; border-radius: 8px; padding: 15px; margin-top: 15px; margin-bottom: 5px; box-shadow: inset 0 0 20px rgba(0,0,0,0.9); }
    .digital-number { font-family: 'Consolas', monospace; font-size: 45px; font-weight: 900; line-height: 1.0; text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px; }
    .monitor-label { color: #90a4ae; font-size: 13px; font-weight: bold; letter-spacing: 1px; }
    .note-entry { background-color: #2c3e50; padding: 15px; border-radius: 5px; border-left: 4px solid #0288d1; margin-bottom: 10px; font-size: 0.95em; line-height: 1.5; }
    .note-time { color: #81d4fa; font-weight: bold; margin-bottom: 5px; font-size: 0.9em; }
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    .stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 5. 데이터 및 세션 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'selected_date' not in st.session_state: st.session_state.selected_date = datetime.date.today()
if 'log_history' not in st.session_state: st.session_state.log_history = []

# [환자 DB 업데이트] 모델 입력에 필요한 V/S 및 검사결과 더미 데이터 추가
PATIENTS_DB = [
    {
        "id": "12345678", "bed": "04-01", "name": "김철수", "gender": "M", "age": 68,
        "height": 172, "weight": 70, "blood": "A+", "diag": "Pneumonia",
        "doc": "김뇌혈", "nurse": "이간호", "status_flags": ["항암전체", "DNR"],
        "factors": ["수면제 복용", "고령"], 
        # -- AI 모델용 데이터 --
        "sbp": 140, "dbp": 90, "pr": 92, "rr": 22, "bt": 37.2, "albumin": 2.8, "crp": 5.0, "mental": "alert", "symptom": "RESPIRATORY"
    },
    {
        "id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 79,
        "height": 155, "weight": 53, "blood": "O+", "diag": "Stomach Cancer",
        "doc": "박위장", "nurse": "최간호", "status_flags": ["섬망", "NST", "Device"],
        "factors": ["섬망", "보행 장애"],
        # -- AI 모델용 데이터 --
        "sbp": 110, "dbp": 70, "pr": 80, "rr": 18, "bt": 36.5, "albumin": 3.8, "crp": 0.3, "mental": "verbal response", "symptom": "GI"
    },
    {
        "id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 45,
        "height": 178, "weight": 82, "blood": "B-", "diag": "Femur Fracture",
        "doc": "최정형", "nurse": "김간호", "status_flags": ["진료회송"],
        "factors": [],
        # -- AI 모델용 데이터 --
        "sbp": 120, "dbp": 80, "pr": 75, "rr": 16, "bt": 36.6, "albumin": 4.2, "crp": 0.1, "mental": "alert", "symptom": "MSK_PAIN"
    },
    {
        "id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32,
        "height": 162, "weight": 55, "blood": "AB+", "diag": "Acute Appendicitis",
        "doc": "이외과", "nurse": "박간호", "status_flags": ["임신수유", "DRG"],
        "factors": [],
        # -- AI 모델용 데이터 --
        "sbp": 118, "dbp": 78, "pr": 70, "rr": 14, "bt": 36.4, "albumin": 4.5, "crp": 0.2, "mental": "alert", "symptom": "GI"
    },
]

def get_orders(pt_name, date_obj):
    base_orders = [
        {"구분": "약품", "오더명": "Tylenol ER 650mg", "용법": "1TAB PO TID", "상태": "확인"},
        {"구분": "식이", "오더명": "General Diet (Soft)", "용법": "매끼", "상태": "확인"},
        {"구분": "처치", "오더명": "Vital Sign Check", "용법": "q4hr", "상태": "수행완료"},
    ]
    return pd.DataFrame(base_orders)

# --------------------------------------------------------------------------------
# 6. [핵심 기능] 팝업창 & 자동 차팅 로직
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    with c1:
        st.markdown("##### 🚨 감지된 위험요인")
        with st.container(border=True):
            if data['factors']:
                for f in data['factors']: st.error(f"• {f}")
            else: st.write("특이사항 없음")
            
    with c2:
        st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("##### ✅ 필수 간호 진술문 선택")
        with st.container(border=True):
            chk_rail = False
            chk_med = False
            chk_nutri = False
            chk_position = False
            
            # 예측 점수 가져오기 (실시간 계산)
            current_risk_score = predict_fall_risk(data)
            
            if current_risk_score >= 40:
                chk_rail = st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
            if "수면제" in str(data['factors']):
                chk_med = st.checkbox("💊 수면제 투여 후 30분 관찰")
            if data['albumin'] < 3.0:
                chk_nutri = st.checkbox("🥩 영양팀 협진 의뢰 (알부민 저하)")
            
            chk_edu = st.checkbox("📢 낙상 예방 교육 및 호출기 위치 안내", value=True)

    st.markdown("---")
    if st.button("간호 수행 완료 및 기록 저장 (Auto-Charting)", type="primary", use_container_width=True):
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        risk_factors_str = ", ".join(data['factors']) if data['factors'] else "특이 위험요인 없음"
        actions = []
        if chk_rail: actions.append("침상난간 2개 이상 올림 확인")
        if chk_med: actions.append("수면제 투여 후 30분간 의식상태/거동 관찰함")
        if chk_nutri: actions.append("영양 불균형 교정을 위해 영양팀 협진 의뢰함")
        if chk_edu: actions.append("환자 및 보호자에게 낙상 위험성 알리고 호출기 사용법 교육함")
        
        action_str = ", ".join(actions)
        final_note_content = f"""낙상위험요인 확인함({risk_factors_str}) -> 중재시행 -> 
{action_str}. 낙상 예방을 위한 안전한 환경 조성하고 지속적으로 관찰함."""

        new_note = {"time": current_time, "writer": "김분당", "content": final_note_content}
        st.session_state.nursing_notes.insert(0, new_note)
        st.toast("✅ 간호기록에 성공적으로 저장되었습니다!", icon="💾")
        time.sleep(1)
        st.rerun()

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])
curr_pt = PATIENTS_DB[st.session_state.current_pt_idx]
curr_pt_name = curr_pt['name']

# [좌측 사이드바]
with col_sidebar:
    st.markdown("### 🏥 재원 환자")
    idx = st.radio("환자 리스트", range(len(PATIENTS_DB)), format_func=lambda i: f"[{PATIENTS_DB[i]['bed']}] {PATIENTS_DB[i]['name']}", label_visibility="collapsed")
    st.session_state.current_pt_idx = idx
    st.markdown("---")
    
    # [핵심] AI 예측 실행
    fall_score = predict_fall_risk(curr_pt)
    # 욕창 점수는 AI 모델이 없으므로 일단 15점으로 고정 (추후 연동 가능)
    sore_score = 15 
    
    # 디지털 계기판
    f_color = "#ff5252" if fall_score >= 60 else ("#ffca28" if fall_score >= 30 else "#00e5ff")
    s_color = "#ff5252" if sore_score >= 18 else ("#ffca28" if sore_score >= 15 else "#00e5ff") # Braden scale 역순 고려 필요하나 예시상 단순화
    
    st.markdown(f"""
    <div class="digital-monitor-container">
        <div class="monitor-row">
            <div style="text-align:center; width:45%; border-right:1px solid #444;">
                <div class="monitor-label">FALL RISK</div>
                <div class="digital-number" style="color:{f_color};">{fall_score}</div>
            </div>
            <div style="text-align:center; width:45%;">
                <div class="monitor-label">SORE RISK</div>
                <div class="digital-number" style="color:{s_color};">{sore_score}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="primary", use_container_width=True):
        show_risk_details(curr_pt_name, curr_pt)

# [우측 메인 화면]
with col_main:
    st.markdown(f"""
    <div class="header-container">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center;">
                <span style="font-size:1.5em; font-weight:bold; color:white; margin-right:20px;">🏥 SNUH</span>
                <span class="header-info-text"><span class="header-label">환자명:</span> <b>{curr_pt_name}</b> ({curr_pt['reg']})</span>
                <span class="header-info-text">{curr_pt['info']}</span>
                <span class="header-info-text" style="color:#4fc3f7;">{curr_pt['diag']}</span>
            </div>
            <div style="color:#b0bec5; font-size:0.9em;">김분당 간호사 | {datetime.datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🛡️ 통합뷰", "💊 오더", "📝 간호기록(Auto-Note)"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info("좌측 패널의 '상세 분석' 버튼을 눌러 자동 차팅을 시도해보세요.")
            st.markdown(f"**[현재 위험 요인]**")
            for f in curr_pt['factors']:
                st.markdown(f"<span class='risk-tag'>{f}</span>", unsafe_allow_html=True)
        with c2:
            st.markdown("**[V/S Summary]**")
            st.dataframe(pd.DataFrame({'SBP':[curr_pt['sbp']], 'DBP':[curr_pt['dbp']], 'PR':[curr_pt['pr']], 'BT':[curr_pt['bt']]}), hide_index=True)

    with tab2: st.write("오더 화면")

    with tab3:
        st.markdown("##### 📝 간호진술문 (Nursing Note)")
        for note in st.session_state.nursing_notes:
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-time">📅 {note['time']} | 작성자: {note['writer']}</div>
                <div>{note['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.text_area("추가 기록 입력", placeholder="내용을 입력하세요...", height=100)
        st.button("수기 기록 저장")

st.markdown("---")
legends = [("수술전","#e57373"), ("수술중","#ba68c8"), ("검사후","#7986cb"), ("퇴원","#81c784"), ("신규오더","#ffb74d")]
html = '<div style="display:flex; gap:10px;">' + "".join([f'<span class="legend-item" style="background:{c}">{l}</span>' for l,c in legends]) + '</div>'
st.markdown(html, unsafe_allow_html=True)
