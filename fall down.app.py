import streamlit as st
import pandas as pd
import datetime
import time

# --------------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 Custom CSS
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - Fall Guard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 다크 모드, EMR UI, 그리고 [디지털 계기판 & 팝업] 스타일 정의
st.markdown("""
<style>
    /* [전체 테마] */
    .stApp { background-color: #1e252b; color: #e0e0e0; }

    /* [헤더] 환자 정보 바 */
    .header-container {
        background-color: #263238; padding: 10px 20px; border-radius: 5px;
        border-top: 3px solid #0288d1; box-shadow: 0 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .header-info-text { font-size: 1.1em; color: #eceff1; margin-right: 15px; }
    .header-label { font-size: 0.8em; color: #b0bec5; }

    /* [좌측] 환자 리스트 카드 */
    .patient-card {
        padding: 8px; background-color: #2c3e50; border-left: 4px solid #546e7a;
        border-radius: 4px; margin-bottom: 5px; cursor: pointer;
    }

    /* [핵심] 디지털 계기판 스타일 (검은색 박스 + 네온 숫자) */
    .digital-monitor-container {
        background-color: #000000; 
        border: 2px solid #455a64; border-radius: 8px;
        padding: 15px; margin-top: 15px; margin-bottom: 5px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9);
    }
    .monitor-row { display: flex; justify-content: space-around; align-items: center; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 40px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #90a4ae; font-size: 12px; font-weight: bold; letter-spacing: 1px; }

    /* [팝업] 모달 스타일 */
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    
    /* 버튼 및 탭 스타일 */
    div.stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    div.stButton > button:hover { background-color: #455a64; border-color: #90a4ae; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #263238; color: #b0bec5; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #0277bd; color: white; }
    
    /* 하단 범례 */
    .legend-item { display: inline-block; padding: 2px 8px; margin-right: 5px; border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; text-align: center; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 2. 데이터 정의 (팝업에 띄울 위험요인 포함)
# --------------------------------------------------------------------------------
PATIENTS_DB = [
    {
        "id": "12345678", "bed": "04-01", "name": "김철수", "gender": "M", "age": 68,
        "height": 172, "weight": 70, "blood": "A+", "diag": "Unruptured cerebral aneurysm",
        "doc": "김뇌혈", "nurse": "이간호", "status_flags": ["항암전체", "DNR"],
        "fall_risk": 92, "sore_risk": 15, "factors": ["수면제 복용", "고령", "알부민 저하"] # 팝업용 데이터
    },
    {
        "id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 79,
        "height": 155, "weight": 53, "blood": "O+", "diag": "Stomach Cancer",
        "doc": "박위장", "nurse": "최간호", "status_flags": ["섬망", "NST", "Device"],
        "fall_risk": 45, "sore_risk": 60, "factors": ["섬망", "보행 장애"]
    },
    {
        "id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 45,
        "height": 178, "weight": 82, "blood": "B-", "diag": "Femur Fracture",
        "doc": "최정형", "nurse": "김간호", "status_flags": ["진료회송"],
        "fall_risk": 20, "sore_risk": 5, "factors": []
    },
    {
        "id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32,
        "height": 162, "weight": 55, "blood": "AB+", "diag": "Acute Appendicitis",
        "doc": "이외과", "nurse": "박간호", "status_flags": ["임신수유", "DRG"],
        "fall_risk": 10, "sore_risk": 0, "factors": []
    },
]

def get_orders(pt_name, date_obj):
    # 오더 더미 데이터
    base_orders = [
        {"구분": "약품", "오더명": "Tylenol ER 650mg", "용법": "1TAB PO TID", "상태": "확인"},
        {"구분": "식이", "오더명": "General Diet (Soft)", "용법": "매끼", "상태": "확인"},
        {"구분": "처치", "오더명": "Vital Sign Check", "용법": "q4hr", "상태": "수행완료"},
    ]
    if date_obj.day % 2 == 0:
        base_orders.append({"구분": "검사", "오더명": "CBC", "용법": "Routine", "상태": "검사후"})
    return pd.DataFrame(base_orders)


# --------------------------------------------------------------------------------
# 3. [핵심 기능] 팝업창 함수 (그림과 똑같은 구조: 왼쪽 -> 화살표 -> 오른쪽)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 **{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    # 3단 레이아웃: [위험요인] -> [화살표] -> [간호중재]
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    with c1:
        st.markdown("##### 🚨 감지된 위험요인")
        with st.container(border=True):
            if data['factors']:
                for f in data['factors']: st.error(f"• {f}")
            else: st.write("특이사항 없음")
            
    with c2:
        # 화살표 이모지 중앙 배치
        st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("##### ✅ 필수 간호 진술문")
        with st.container(border=True):
            if data['fall_risk'] >= 40: st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
            if "수면제" in str(data['factors']): st.checkbox("💊 수면제 투여 후 30분 관찰")
            if "알부민" in str(data['factors']): st.checkbox("🥩 영양팀 협진 의뢰")
            if data['sore_risk'] >= 14: st.checkbox("🧴 2시간마다 체위 변경")
            
    st.write("")
    if st.button("간호 수행 완료 및 닫기", type="primary", use_container_width=True):
        st.rerun()


# --------------------------------------------------------------------------------
# 4. 세션 초기화 및 레이아웃
# --------------------------------------------------------------------------------
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
if 'selected_date' not in st.session_state: st.session_state.selected_date = datetime.date.today()
if 'log_history' not in st.session_state: st.session_state.log_history = []

col_sidebar, col_main = st.columns([2, 8])
curr_pt = PATIENTS_DB[st.session_state.current_pt_idx]

# ==============================================================================
# [좌측 패널] 프로필, 상태버튼, *디지털 계기판*, 환자 리스트
# ==============================================================================
with col_sidebar:
    st.selectbox("근무 DUTY", ["Day", "Evening", "Night"])
    st.divider()

    # 1. 프로필 영역
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        st.markdown("""<div style="width:70px; height:80px; background:linear-gradient(135deg, #ce93d8, #ab47bc); border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:40px; color:white;">👤</div>""", unsafe_allow_html=True)
    with p_col2:
        st.caption("환자 상태 모니터링")
        if st.session_state.log_history: st.code(st.session_state.log_history[-1], language="text")
        else: st.info("대기중...")

    # 2. 상태 버튼 그리드
    status_buttons = ["항암전체", "NST", "DNR", "Device", "임신수유", "섬망", "DRG", "진료회송"]
    for i in range(0, 8, 4):
        cols = st.columns(4)
        for j in range(4):
            lbl = status_buttons[i+j]
            btn_type = "primary" if lbl == "섬망" else "secondary"
            if cols[j].button(lbl, key=lbl, type=btn_type, use_container_width=True):
                st.session_state.log_history.append(f"Checked: {lbl}")

    # --------------------------------------------------------------------------
    # [★ 복구 완료] 디지털 계기판 (00 | 00) 스타일
    # --------------------------------------------------------------------------
    
    # 색상 로직
    f_color = "#ff5252" if curr_pt['fall_risk'] >= 70 else ("#ffca28" if curr_pt['fall_risk'] >= 40 else "#00e5ff")
    s_color = "#ff5252" if curr_pt['sore_risk'] >= 50 else ("#ffca28" if curr_pt['sore_risk'] >= 14 else "#00e5ff")

    st.markdown(f"""
    <div class="digital-monitor-container">
        <div class="monitor-row">
            <div style="text-align:center; width:45%; border-right:1px solid #444;">
                <div class="monitor-label">FALL RISK</div>
                <div class="digital-number" style="color: {f_color};">{curr_pt['fall_risk']}</div>
            </div>
            <div style="text-align:center; width:45%;">
                <div class="monitor-label">SORE RISK</div>
                <div class="digital-number" style="color: {s_color};">{curr_pt['sore_risk']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # [★ 복구 완료] 팝업 버튼 (계기판 바로 아래)
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="primary", use_container_width=True):
        show_risk_details(curr_pt['name'], curr_pt)
    
    st.divider()

    # 4. Patient List
    st.markdown("#### 🛏️ Patient List")
    for idx, p in enumerate(PATIENTS_DB):
        marker = "✅" if idx == st.session_state.current_pt_idx else ""
        risk_dot = "🔴" if p['fall_risk'] >= 80 else ""
        if st.button(f"[{p['bed']}] {p['name']} {risk_dot} {marker}", key=f"pt_{idx}", use_container_width=True):
            st.session_state.current_pt_idx = idx
            st.rerun()
    
    # 5. 하단 메뉴
    st.write("")
    c1,c2,c3 = st.columns(3)
    c1.button("Memo"); c2.button("To-Do"); c3.button("Set")


# ==============================================================================
# [우측 메인 패널] 헤더, 정보, 오더 조회 (기존 EMR 레이아웃 유지)
# ==============================================================================
with col_main:
    # 1. 헤더
    st.markdown(f"""
    <div class="header-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 1.5em; font-weight: bold; color: #fff; margin-right: 20px;">🏥 SNUH</span>
                <span class="header-info-text"><span class="header-label">환자명:</span> <b>{curr_pt['name']}</b> ({curr_pt['id']})</span>
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

    # 3. 메인 탭 (오더 조회 등)
    d_col1, d_col2, d_col3 = st.columns([1, 2, 8])
    with d_col1:
        if st.button("◀ 이전"): st.session_state.selected_date -= datetime.timedelta(days=1); st.rerun()
    with d_col2:
        st.date_input("조회일자", value=st.session_state.selected_date, label_visibility="collapsed")
    with d_col3:
        if st.button("다음 ▶"): st.session_state.selected_date += datetime.timedelta(days=1); st.rerun()

    m_tab1, m_tab2, m_tab3 = st.tabs(["💊 오더조회", "🧪 검사결과", "📝 경과기록"])
    
    with m_tab1:
        df = get_orders(curr_pt['name'], st.session_state.selected_date)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with m_tab2:
        st.table(pd.DataFrame({"검사명": ["Hb", "WBC"], "결과": ["13.2", "7.5"]}))

# 하단 범례
st.markdown("---")
legends = [("수술전","#e57373"), ("수술중","#ba68c8"), ("검사후","#7986cb"), ("퇴원","#81c784"), ("신규오더","#ffb74d")]
html = '<div style="display:flex; gap:10px;">' + "".join([f'<span class="legend-item" style="background:{c}">{l}</span>' for l,c in legends]) + '</div>'
st.markdown(html, unsafe_allow_html=True)
