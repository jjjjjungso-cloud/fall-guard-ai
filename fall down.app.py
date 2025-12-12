import streamlit as st
import pandas as pd
import datetime
import time

# --------------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 Custom CSS 정의
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 다크 모드 및 EMR UI 스타일링
st.markdown("""
<style>
    /* [전체 테마] 어두운 네이비/그레이 톤 */
    .stApp {
        background-color: #1e252b;
        color: #e0e0e0;
    }

    /* [헤더] 상단 환자 정보 박스 */
    .header-container {
        background-color: #263238;
        padding: 10px 20px;
        border-radius: 5px;
        border-top: 3px solid #0288d1;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }
    .header-info-text { font-size: 1.1em; color: #eceff1; margin-right: 15px; }
    .header-label { font-size: 0.8em; color: #b0bec5; }
    
    /* [좌측 패널] 환자 리스트 카드 스타일 */
    .patient-card {
        padding: 8px;
        margin-bottom: 5px;
        background-color: #2c3e50;
        border-left: 4px solid #546e7a;
        border-radius: 4px;
        cursor: pointer;
        transition: 0.2s;
    }
    
    /* [버튼] 일반 버튼 스타일 커스텀 */
    div.stButton > button {
        background-color: #37474f;
        color: white;
        border: 1px solid #455a64;
        border-radius: 2px;
        font-size: 0.9em;
        padding: 4px 8px;
        height: auto;
    }
    div.stButton > button:hover {
        background-color: #455a64;
        border-color: #90a4ae;
        color: #fff;
    }
    
    /* [하단] 상태 범례 박스 */
    .legend-item {
        display: inline-block; padding: 2px 8px; margin-right: 5px;
        border-radius: 3px; font-size: 0.75em; font-weight: bold; color: white; text-align: center;
    }
    
    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 35px; white-space: nowrap; background-color: #263238; color: #b0bec5; border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0277bd; color: white;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 2. 더미 데이터(Dummy Data) 정의 (낙상/욕창 점수 추가)
# --------------------------------------------------------------------------------

PATIENTS_DB = [
    {
        "id": "12345678", "bed": "04-01", "name": "김철수", "gender": "M", "age": 68,
        "height": 172, "weight": 70, "blood": "A+", "diag": "Unruptured cerebral aneurysm",
        "doc": "김뇌혈", "nurse": "이간호", "status_flags": ["항암전체", "DNR"],
        "fall_risk": 92, "sore_risk": 15 # 낙상/욕창 점수 추가
    },
    {
        "id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 79,
        "height": 155, "weight": 53, "blood": "O+", "diag": "Stomach Cancer (Advanced)",
        "doc": "박위장", "nurse": "최간호", "status_flags": ["섬망", "NST", "Device"],
        "fall_risk": 45, "sore_risk": 60
    },
    {
        "id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 45,
        "height": 178, "weight": 82, "blood": "B-", "diag": "Femur Fracture",
        "doc": "최정형", "nurse": "김간호", "status_flags": ["진료회송"],
        "fall_risk": 20, "sore_risk": 5
    },
    {
        "id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32,
        "height": 162, "weight": 55, "blood": "AB+", "diag": "Acute Appendicitis",
        "doc": "이외과", "nurse": "박간호", "status_flags": ["임신수유", "DRG"],
        "fall_risk": 10, "sore_risk": 0
    },
]

def get_orders(pt_name, date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    base_orders = [
        {"구분": "약품", "오더코드": "MED_001", "오더명": "Tylenol ER 650mg", "용법": "1TAB PO TID", "상태": "확인"},
        {"구분": "식이", "오더코드": "DIET_02", "오더명": "General Diet (Soft)", "용법": "매끼", "상태": "확인"},
        {"구분": "처치", "오더코드": "NUR_101", "오더명": "Vital Sign Check", "용법": "q4hr", "상태": "수행완료"},
    ]
    if date_obj.day % 2 == 0:
        base_orders.append({"구분": "검사", "오더코드": "LAB_CBC", "오더명": "CBC (Complete Blood Count)", "용법": "Routine", "상태": "검사후"})
        base_orders.append({"구분": "주사", "오더코드": "INJ_NS", "오더명": "Normal Saline 1L", "용법": "IV KVO", "상태": "신규"})
    else:
        base_orders.append({"구분": "영상", "오더코드": "RAD_CT", "오더명": "Brain CT (Non-Contrast)", "용법": "Stat", "상태": "입원예정"})
    return pd.DataFrame(base_orders)


# --------------------------------------------------------------------------------
# 3. 세션 상태(State) 초기화
# --------------------------------------------------------------------------------
if 'current_pt_idx' not in st.session_state:
    st.session_state.current_pt_idx = 0

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.date.today()

if 'log_history' not in st.session_state:
    st.session_state.log_history = []


# --------------------------------------------------------------------------------
# 4. 레이아웃 구성 (Left 2 : Right 8)
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])

curr_pt = PATIENTS_DB[st.session_state.current_pt_idx]

# ==============================================================================
# [좌측 사이드 패널] 환자 프로필, 상태 버튼, 리스트
# ==============================================================================
with col_sidebar:
    # 1. 근무 Duty 선택
    st.selectbox("근무 DUTY", ["Day (07:00~)", "Evening (15:00~)", "Night (23:00~)"], key="duty_sel")
    st.divider()

    # 2. 환자 프로필 영역
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        st.markdown("""
        <div style="width: 70px; height: 80px; background: linear-gradient(135deg, #ce93d8, #ab47bc); 
                    border-radius: 6px; display: flex; align-items: center; justify-content: center; 
                    box-shadow: inset 0 0 10px rgba(0,0,0,0.2);">
            <div style="font-size: 40px; color: white; opacity: 0.8;">👤</div>
        </div>
        """, unsafe_allow_html=True)
    with p_col2:
        st.caption("환자 상태 모니터링")
        if st.session_state.log_history:
            st.code(st.session_state.log_history[-1], language="text")
        else:
            st.info("상태 대기중...")

    st.write("")

    # 3. 상태 버튼 그리드
    status_buttons = [
        ("항암전체", False), ("NST", False), ("DNR", False), ("Device", True),
        ("임신수유", False), ("섬망", True), ("DRG", False), ("진료회송", True)
    ]
    for i in range(0, len(status_buttons), 4):
        cols = st.columns(4)
        for j in range(4):
            idx = i + j
            if idx < len(status_buttons):
                lbl, _ = status_buttons[idx]
                btn_type = "primary" if lbl == "섬망" else "secondary"
                if cols[j].button(lbl, key=f"stat_btn_{idx}", type=btn_type, use_container_width=True):
                    log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] '{lbl}' 상태 확인"
                    st.session_state.log_history.append(log_msg)

    # --------------------------------------------------------------------------
    # [추가요구사항 반영] 낙상/욕창 디지털 계기판 영역
    # --------------------------------------------------------------------------
    st.write("") # 간격 띄우기
    
    # 1) 데이터 준비 (더미 값)
    fall_val = curr_pt.get("fall_risk", 0)
    sore_val = curr_pt.get("sore_risk", 0)

    # 2) 조건부 색상 로직 함수
    def get_risk_color(val):
        if val >= 80: return "#d32f2f" # 빨강 (High)
        elif val >= 50: return "#ef6c00" # 주황 (Medium)
        else: return "#2e7d32" # 초록 (Low)

    fall_color = get_risk_color(fall_val)
    sore_color = get_risk_color(sore_val)

    # 3) 스타일 정의 (흰색 배경, 검정 테두리, 디지털 느낌)
    card_style = """
        background-color: #ffffff;
        border: 2px solid #212121;
        border-radius: 4px;
        padding: 10px 0px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
    """

    # 4) 레이아웃 배치 (2개 박스 나란히)
    meter_c1, meter_c2 = st.columns(2)

    with meter_c1:
        st.markdown(f"""
        <div style="{card_style}">
            <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:5px;">낙상</div>
            <div style="font-size:28px; font-weight:900; color:{fall_color}; line-height:1.0;">{fall_val}%</div>
        </div>
        """, unsafe_allow_html=True)

    with meter_c2:
        st.markdown(f"""
        <div style="{card_style}">
            <div style="font-size:14px; font-weight:bold; color:#333; margin-bottom:5px;">욕창</div>
            <div style="font-size:28px; font-weight:900; color:{sore_color}; line-height:1.0;">{sore_val}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --------------------------------------------------------------------------

    st.divider()

    # 4. Patient List (환자 리스트)
    st.markdown("#### 🛏️ Patient List")
    for idx, p in enumerate(PATIENTS_DB):
        marker = "✅" if idx == st.session_state.current_pt_idx else ""
        # 리스트에도 위험도 살짝 표시
        risk_badge = "🔴" if p.get('fall_risk',0) >= 80 else ""
        btn_label = f"[{p['bed']}] {p['name']} {risk_badge} {marker}"
        
        if st.button(btn_label, key=f"pt_list_{idx}", use_container_width=True):
            st.session_state.current_pt_idx = idx
            st.rerun()

    # 5. 하단 기능 메뉴
    st.write("")
    m1, m2, m3 = st.columns(3)
    m1.button("Memo")
    m2.button("To-Do")
    m3.button("Set")


# ==============================================================================
# [우측 메인 패널] 헤더, 탭, 상세 조회
# ==============================================================================
with col_main:
    
    # 1. 최상단 헤더 바
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
                <b>김닥터(Prof)</b> 님 <br>
                {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        <div style="margin-top: 5px; color: #81d4fa;">
            <span class="header-label">진단명:</span> <b>{curr_pt['diag']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 의료진 정보
    i1, i2, i3, i4, i5 = st.columns([1, 1, 1, 1, 4])
    i1.info(f"전문의: {curr_pt['doc']}")
    i2.info(f"주치의: 이전공")
    i3.info(f"간호사: {curr_pt['nurse']}")
    i4.info("☎: 1234")
    
    st.write("")

    # 3. 메인 기능 영역
    d_col1, d_col2, d_col3 = st.columns([1, 2, 8])
    with d_col1:
        if st.button("◀ 이전"):
            st.session_state.selected_date -= datetime.timedelta(days=1)
            st.rerun()
    with d_col2:
        new_date = st.date_input("조회일자", value=st.session_state.selected_date, label_visibility="collapsed")
        if new_date != st.session_state.selected_date:
            st.session_state.selected_date = new_date
            st.rerun()
    with d_col3:
        if st.button("다음 ▶"):
            st.session_state.selected_date += datetime.timedelta(days=1)
            st.rerun()

    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["💊 오더조회", "🧪 검사결과", "💉 약 정보", "📝 경과기록"])

    with m_tab1:
        st.markdown(f"**[{st.session_state.selected_date}]** 오더 수행 내역")
        df_orders = get_orders(curr_pt['name'], st.session_state.selected_date)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)

    with m_tab2:
        st.info("검사 결과 조회 화면입니다.")
        st.table(pd.DataFrame({
            "검사명": ["WBC", "Hb", "Plt", "Cr", "BUN"],
            "결과값": ["7.5", "13.2", "240", "0.9", "15"],
            "참고치": ["4.0-10.0", "12.0-16.0", "150-450", "0.5-1.2", "8-20"]
        }))

    with m_tab3:
        st.warning("약품 상세 정보 조회 (준비중)")

    with m_tab4:
        st.text_area("경과 기록 입력", height=150, placeholder="특이사항을 입력하세요...")


# --------------------------------------------------------------------------------
# 5. 화면 하단 바 (상태 범례)
# --------------------------------------------------------------------------------
st.markdown("---")
legends = [
    ("수술전", "#e57373"), ("수술중", "#ba68c8"), ("수술후", "#9575cd"),
    ("검사후", "#7986cb"), ("전과준비", "#64b5f6"), ("입원예정", "#4db6ac"),
    ("퇴원", "#81c784"), ("신규오더", "#ffb74d"), ("확인오더", "#a1887f")
]
legend_html = '<div style="display:flex; flex-wrap:wrap; gap:10px;">'
for label, color in legends:
    legend_html += f'<span class="legend-item" style="background-color:{color};">{label}</span>'
legend_html += '</div>'

st.markdown(legend_html, unsafe_allow_html=True)
