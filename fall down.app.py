import streamlit as st
import pandas as pd
import datetime
import time
import joblib  # AI 모델 로딩
import numpy as np

# --------------------------------------------------------------------------------
# 1. 페이지 설정 (반드시 코드 맨 처음에 와야 함)
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - AI System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------------------------------
# 2. [핵심] 리소스 로딩 (모델, 변수명, 중요도 데이터)
# --------------------------------------------------------------------------------
@st.cache_resource
def load_resources():
    resources = {}
    try:
        # 1. AI 모델 (뇌)
        resources['model'] = joblib.load('rf_fall_model.joblib')
        
        # 2. 변수 리스트 (처방전)
        df_cols = pd.read_csv('rf_model_feature_columns.csv')
        resources['features'] = df_cols['feature'].tolist()
        
        # 3. 중요도 데이터 (근거) - 파일이 없어도 에러 안 나게 처리
        try:
            resources['importance'] = pd.read_csv('rf_feature_importance_top10.csv')
        except:
            resources['importance'] = None
            
    except Exception as e:
        # 파일이 하나라도 없으면 None 반환 (앱이 꺼지는 것 방지)
        return None
    return resources

res = load_resources()

# --------------------------------------------------------------------------------
# 3. [핵심] 예측 함수 (환자 정보 -> 점수 변환)
# --------------------------------------------------------------------------------
def predict_fall_risk(pt_info):
    # 모델 로딩 실패 시 0점 처리
    if res is None or 'model' not in res: return 0
    
    model = res['model']
    feature_cols = res['features']
    
    # 1. 입력 데이터 0으로 초기화
    input_data = {col: 0 for col in feature_cols}
    
    # 2. 환자 정보 매핑 (KeyError 방지용 get 사용)
    input_data['나이'] = pt_info.get('age', 60)
    input_data['SBP'] = pt_info.get('sbp', 120)
    input_data['DBP'] = pt_info.get('dbp', 80)
    input_data['PR'] = pt_info.get('pr', 80)
    input_data['RR'] = pt_info.get('rr', 20)
    input_data['BT'] = pt_info.get('bt', 36.5)
    input_data['albumin'] = pt_info.get('albumin', 4.0)
    input_data['crp'] = pt_info.get('crp', 0.5)
    
    # 성별 처리
    if pt_info.get('gender') == 'M': input_data['성별'] = 1
    
    try:
        # DataFrame 변환 및 예측
        input_df = pd.DataFrame([input_data])
        input_df = input_df[feature_cols] # 순서 강제 맞춤
        prob = model.predict_proba(input_df)[0][1]
        return int(prob * 100)
    except:
        return 0

# --------------------------------------------------------------------------------
# 4. 스타일 (CSS) - EMR 다크모드
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    .stApp { background-color: #1e252b; color: #e0e0e0; font-family: 'Noto Sans KR', sans-serif; }

    /* 헤더 스타일 */
    .header-container {
        background-color: #263238; padding: 10px 20px; border-radius: 5px;
        border-top: 3px solid #0288d1; box-shadow: 0 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .header-info-text { font-size: 1.1em; color: #eceff1; margin-right: 15px; }
    .header-label { font-size: 0.8em; color: #b0bec5; }

    /* 디지털 계기판 (검은색) */
    .digital-monitor-container {
        background-color: #000000; border: 2px solid #455a64; border-radius: 8px;
        padding: 15px; margin-top: 15px; margin-bottom: 5px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9);
    }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 40px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #90a4ae; font-size: 12px; font-weight: bold; letter-spacing: 1px; }

    /* 간호기록 텍스트 영역 */
    .note-entry {
        background-color: #2c3e50; padding: 15px; border-radius: 5px;
        border-left: 4px solid #0288d1; margin-bottom: 10px; font-size: 0.95em; line-height: 1.5;
    }
    .note-time { color: #81d4fa; font-weight: bold; margin-bottom: 5px; font-size: 0.9em; }

    /* 기타 UI 스타일 */
    .patient-card { padding: 8px; background-color: #2c3e50; border-left: 4px solid #546e7a; border-radius: 4px; margin-bottom: 5px; cursor: pointer; }
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    .stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #263238; color: #b0bec5; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #0277bd; color: white; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
    .legend-item { display: inline-block; padding: 2px 8px; margin-right: 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 5. 데이터 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    st.session_state.nursing_notes = [{"time": "2025-12-12 08:00", "writer": "김분당", "content": "활력징후 측정함. 특이사항 없음."}]
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'selected_date' not in st.session_state: st.session_state.selected_date = datetime.date.today()
if 'log_history' not in st.session_state: st.session_state.log_history = []

# [환자 DB] AI 예측에 필요한 상세 데이터 포함
PATIENTS_DB = [
    {
        "id": "12345678", "bed": "04-01", "name": "김철수", "gender": "M", "age": 68,
        "height": 172, "weight": 70, "blood": "A+", "diag": "Pneumonia",
        "doc": "김뇌혈", "nurse": "이간호", "status_flags": ["항암전체", "DNR"],
        "factors": ["수면제 복용", "고령", "알부민 저하"], 
        "sbp": 140, "dbp": 90, "pr": 92, "rr": 22, "bt": 37.2, "albumin": 2.8, "crp": 5.0, "sore_risk": 15
    },
    {
        "id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 79,
        "height": 155, "weight": 53, "blood": "O+", "diag": "Stomach Cancer",
        "doc": "박위장", "nurse": "최간호", "status_flags": ["섬망", "NST", "Device"],
        "factors": ["섬망", "보행 장애"],
        "sbp": 110, "dbp": 70, "pr": 80, "rr": 18, "bt": 36.5, "albumin": 3.8, "crp": 0.3, "sore_risk": 60
    },
    {
        "id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 45,
        "height": 178, "weight": 82, "blood": "B-", "diag": "Femur Fracture",
        "doc": "최정형", "nurse": "김간호", "status_flags": ["진료회송"],
        "factors": [],
        "sbp": 120, "dbp": 80, "pr": 75, "rr": 16, "bt": 36.6, "albumin": 4.2, "crp": 0.1, "sore_risk": 5
    },
    {
        "id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32,
        "height": 162, "weight": 55, "blood": "AB+", "diag": "Acute Appendicitis",
        "doc": "이외과", "nurse": "박간호", "status_flags": ["임신수유", "DRG"],
        "factors": [],
        "sbp": 118, "dbp": 78, "pr": 70, "rr": 14, "bt": 36.4, "albumin": 4.5, "crp": 0.2, "sore_risk": 0
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
# 6. [핵심 기능] 팝업 (중재 선택 + AI 근거 그래프)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data, current_score):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    # 탭 구성: 중재 vs 근거
    tab1, tab2 = st.tabs(["🛡️ 맞춤형 간호중재", "📊 AI 판단 근거 (XAI)"])
    
    # [Tab 1] 간호 중재 및 자동 차팅
    with tab1:
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
            st.markdown("##### ✅ 필수 간호 진술문")
            with st.container(border=True):
                chk_rail = False
                chk_med = False
                chk_nutri = False
                chk_position = False
                
                if current_score >= 40:
                    chk_rail = st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
                if "수면제" in str(data['factors']):
                    chk_med = st.checkbox("💊 수면제 투여 후 30분 관찰")
                if data['albumin'] < 3.0:
                    chk_nutri = st.checkbox("🥩 영양팀 협진 의뢰 (알부민 저하)")
                if data['sore_risk'] >= 14:
                    chk_position = st.checkbox("🧴 2시간마다 체위 변경 (욕창 위험)")
                
                chk_edu = st.checkbox("📢 낙상 예방 교육 및 호출기 위치 안내", value=True)

        st.markdown("---")
        
        # 저장 버튼 (자동 차팅)
        if st.button("간호 수행 완료 및 기록 저장 (Auto-Charting)", type="primary", use_container_width=True):
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            risk_factors_str = ", ".join(data['factors']) if data['factors'] else "특이 위험요인 없음"
            
            actions = []
            if chk_rail: actions.append("침상난간 2개 이상 올림 확인")
            if chk_med: actions.append("수면제 투여 후 30분간 의식상태/거동 관찰함")
            if chk_nutri: actions.append("영양 불균형 교정을 위해 영양팀 협진 의뢰함")
            if chk_position: actions.append("피부 통합성 유지를 위해 2시간마다 체위 변경 시행함")
            if chk_edu: actions.append("환자 및 보호자에게 낙상 위험성 알리고 호출기 사용법 교육함")
            
            action_str = ", ".join(actions)
            final_note_content = f"""낙상위험요인 확인함({risk_factors_str}) -> 중재시행 -> 
{action_str}. 낙상 예방을 위한 안전한 환경 조성하고 지속적으로 관찰함."""

            new_note = {"time": current_time, "writer": "김분당", "content": final_note_content}
            st.session_state.nursing_notes.insert(0, new_note)
            st.toast("✅ 간호기록에 성공적으로 저장되었습니다!", icon="💾")
            time.sleep(1)
            st.rerun()

    # [Tab 2] AI 판단 근거 (Feature Importance)
    with tab2:
        st.markdown("##### 🤖 AI 모델의 주요 판단 기준 (Top 10)")
        st.caption("AI가 낙상 위험도를 예측할 때 어떤 변수를 중요하게 고려했는지 보여줍니다.")
        
        if res and 'importance' in res and res['importance'] is not None:
            df_imp = res['importance']
            st.bar_chart(df_imp.set_index('feature'), color="#005eb8")
        else:
            st.info("중요도 데이터 파일(rf_feature_importance_top10.csv)이 없습니다.")

# --------------------------------------------------------------------------------
# 7. 메인 레이아웃 구성
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])
curr_pt = PATIENTS_DB[st.session_state.current_pt_idx]
curr_pt_name = curr_pt['name']

# ==============================================================================
# [좌측 패널]
# ==============================================================================
with col_sidebar:
    st.selectbox("근무 DUTY", ["Day", "Evening", "Night"])
    st.divider()

    # 1. 프로필
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        st.markdown("""<div style="width:70px; height:80px; background:linear-gradient(135deg, #ce93d8, #ab47bc); border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:40px; color:white;">👤</div>""", unsafe_allow_html=True)
    with p_col2:
        st.caption("환자 상태 모니터링")
        if st.session_state.log_history: st.code(st.session_state.log_history[-1], language="text")
        else: st.info("대기중...")

    # 2. 상태 버튼
    status_buttons = ["항암전체", "NST", "DNR", "Device", "임신수유", "섬망", "DRG", "진료회송"]
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            lbl = status_buttons[i+j]
            btn_type = "primary" if lbl == "섬망" else "secondary"
            if cols[j].button(lbl, key=lbl, type=btn_type, use_container_width=True):
                st.session_state.log_history.append(f"Checked: {lbl}")

    # --------------------------------------------------------------------------
    # [핵심] 디지털 계기판 (AI 예측값 적용)
    # --------------------------------------------------------------------------
    fall_score = predict_fall_risk(curr_pt)
    sore_score = curr_pt.get('sore_risk', 15)
    
    f_color = "#ff5252" if fall_score >= 60 else ("#ffca28" if fall_score >= 30 else "#00e5ff")
    s_color = "#ff5252" if sore_score >= 18 else ("#ffca28" if sore_score >= 15 else "#00e5ff")

    st.markdown(f"""
    <div class="digital-monitor-container">
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

    # 팝업 버튼
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="primary", use_container_width=True):
        show_risk_details(curr_pt_name, curr_pt, fall_score)
    
    st.divider()

    # 4. 환자 리스트
    st.markdown("#### 🛏️ Patient List")
    for idx, p in enumerate(PATIENTS_DB):
        marker = "✅" if idx == st.session_state.current_pt_idx else ""
        risk_dot = "🔴" if predict_fall_risk(p) >= 60 else ""
        if st.button(f"[{p['bed']}] {p['name']} {risk_dot} {marker}", key=f"pt_{idx}", use_container_width=True):
            st.session_state.current_pt_idx = idx
            st.rerun()
            
    # 5. 하단 메뉴
    st.write("")
    c1,c2,c3 = st.columns(3)
    c1.button("Memo"); c2.button("To-Do"); c3.button("Set")


# ==============================================================================
# [우측 패널]
# ==============================================================================
with col_main:
    # 1. 헤더
    st.markdown(f"""
    <div class="header-container">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center;">
                <span style="font-size:1.5em; font-weight:bold; color:white; margin-right:20px;">🏥 SNUH</span>
                <span class="header-info-text"><span class="header-label">환자명:</span> <b>{curr_pt_name}</b> ({curr_pt['id']})</span>
                <span class="header-info-text"><span class="header-label">성별/나이:</span> {curr_pt['gender']}/{curr_pt['age']}세</span>
                <span class="header-info-text"><span class="header-label">신체:</span> {curr_pt['height']}cm / {curr_pt['weight']}kg</span>
                <span class="header-info-text"><span class="header-label">혈액형:</span> <span style="color:#ef5350; font-weight:bold;">{curr_pt['blood']}</span></span>
            </div>
            <div style="text-align: right; color: #b0bec5; font-size: 0.9em;">
                <b>김닥터(Prof)</b> 님 <br> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        <div style="margin-top: 5px; color: #81d4fa;">
            <span class="header-label">진단명:</span> <b>{curr_pt['diag']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 의료진 정보
    i1, i2, i3, i4 = st.columns([1, 1, 1, 5])
    i1.info(f"전문의: {curr_pt['doc']}")
    i2.info("주치의: 이전공")
    i3.info(f"간호사: {curr_pt['nurse']}")

    st.write("")

    # 3. 메인 탭
    d_col1, d_col2, d_col3 = st.columns([1, 2, 8])
    with d_col1:
        if st.button("◀ 이전"): st.session_state.selected_date -= datetime.timedelta(days=1); st.rerun()
    with d_col2:
        st.date_input("조회일자", value=st.session_state.selected_date, label_visibility="collapsed")
    with d_col3:
        if st.button("다음 ▶"): st.session_state.selected_date += datetime.timedelta(days=1); st.rerun()

    m_tab1, m_tab2, m_tab3 = st.tabs(["💊 오더조회", "🧪 검사결과", "📝 간호기록(Auto-Note)"])
    
    with m_tab1:
        df = get_orders(curr_pt['name'], st.session_state.selected_date)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with m_tab2:
        st.table(pd.DataFrame({"검사명": ["Hb", "WBC"], "결과": ["13.2", "7.5"]}))

    # [핵심] 간호기록 탭
    with m_tab3:
        st.markdown("##### 📋 간호진술문 (Nursing Note)")
        st.caption("※ 좌측 [상세 분석] 팝업에서 저장하면 이곳에 자동 입력됩니다.")
        
        for note in st.session_state.nursing_notes:
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-time">📅 {note['time']} | 작성자: {note['writer']}</div>
                <div>{note['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.text_area("추가 기록 입력", placeholder="내용을 입력하세요...", height=100)
        st.button("수기 기록 저장")

# 하단 범례
st.markdown("---")
legends = [("수술전","#e57373"), ("수술중","#ba68c8"), ("검사후","#7986cb"), ("퇴원","#81c784"), ("신규오더","#ffb74d")]
html = '<div style="display:flex; gap:10px;">' + "".join([f'<span class="legend-item" style="background:{c}">{l}</span>' for l,c in legends]) + '</div>'
st.markdown(html, unsafe_allow_html=True)
