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
    initial_sidebar_state="collapsed" # 실제 PC 프로그램 느낌을 위해 기본 사이드바는 숨김
)

# 다크 모드 및 EMR UI 스타일링을 위한 CSS 주입
st.markdown("""
<style>
    /* [전체 테마] 어두운 네이비/그레이 톤 (시력 보호) */
    .stApp {
        background-color: #1e252b; /* 베이스 배경 */
        color: #e0e0e0; /* 기본 글자색 */
    }

    /* [헤더] 상단 환자 정보 박스 */
    .header-container {
        background-color: #263238;
        padding: 10px 20px;
        border-radius: 5px;
        border-top: 3px solid #0288d1; /* 상단 포인트 컬러 (파랑) */
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
    .patient-card:hover { background-color: #34495e; border-left-color: #29b6f6; }
    .patient-card-active { background-color: #37474f; border-left-color: #00e676; border: 1px solid #00e676; }

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
    
    /* [상태 아이콘] 섬망 등 상태 버튼 스타일 (Grid용) */
    /* Streamlit 버튼은 CSS 클래스 지정이 어려워 type='primary' 등을 활용해 구분 */
    
    /* [하단] 상태 범례 박스 */
    .legend-item {
        display: inline-block;
        padding: 2px 8px;
        margin-right: 5px;
        border-radius: 3px;
        font-size: 0.75em;
        font-weight: bold;
        color: white;
        text-align: center;
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
# 2. 더미 데이터(Dummy Data) 정의
# --------------------------------------------------------------------------------

# 2-1. 환자 리스트 데이터
PATIENTS_DB = [
    {
        "id": "12345678", "bed": "04-01", "name": "김철수", "gender": "M", "age": 68,
        "height": 172, "weight": 70, "blood": "A+", "diag": "Unruptured cerebral aneurysm",
        "doc": "김뇌혈", "nurse": "이간호", "status_flags": ["항암전체", "DNR"]
    },
    {
        "id": "87654321", "bed": "04-02", "name": "이영희", "gender": "F", "age": 79,
        "height": 155, "weight": 53, "blood": "O+", "diag": "Stomach Cancer (Advanced)",
        "doc": "박위장", "nurse": "최간호", "status_flags": ["섬망", "NST", "Device"]
    },
    {
        "id": "11223344", "bed": "05-01", "name": "박민수", "gender": "M", "age": 45,
        "height": 178, "weight": 82, "blood": "B-", "diag": "Femur Fracture",
        "doc": "최정형", "nurse": "김간호", "status_flags": ["진료회송"]
    },
    {
        "id": "99887766", "bed": "05-02", "name": "정수진", "gender": "F", "age": 32,
        "height": 162, "weight": 55, "blood": "AB+", "diag": "Acute Appendicitis",
        "doc": "이외과", "nurse": "박간호", "status_flags": ["임신수유", "DRG"]
    },
]

# 2-2. 오더(Order) 데이터 생성 함수
def get_orders(pt_name, date_obj):
    # 날짜의 홀/짝에 따라 오더 내용을 다르게 보여주어 동적인 느낌 부여
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
    st.session_state.current_pt_idx = 0  # 기본 선택 환자 인덱스

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.date.today()

if 'log_history' not in st.session_state:
    st.session_state.log_history = []  # 클릭 로그 저장용


# --------------------------------------------------------------------------------
# 4. 레이아웃 구성 (Left 2 : Right 8)
# --------------------------------------------------------------------------------
col_sidebar, col_main = st.columns([2, 8])

# 현재 선택된 환자 객체 가져오기
curr_pt = PATIENTS_DB[st.session_state.current_pt_idx]


# ==============================================================================
# [좌측 사이드 패널] 환자 프로필, 상태 버튼, 리스트
# ==============================================================================
with col_sidebar:
    # 1. 근무 Duty 선택
    st.selectbox("근무 DUTY", ["Day (07:00~)", "Evening (15:00~)", "Night (23:00~)"], key="duty_sel")
    
    st.divider() # 구분선

    # 2. 환자 프로필 & 상태 카드 (요청하신 이미지 UI 구현)
    # 상단: 프로필 이미지 + 빈 공간(또는 간략 정보)
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        # 보라색 배경의 실루엣 아이콘 (HTML/CSS로 구현)
        st.markdown("""
        <div style="width: 70px; height: 80px; background: linear-gradient(135deg, #ce93d8, #ab47bc); 
                    border-radius: 6px; display: flex; align-items: center; justify-content: center; 
                    box-shadow: inset 0 0 10px rgba(0,0,0,0.2);">
            <div style="font-size: 40px; color: white; opacity: 0.8;">👤</div>
        </div>
        """, unsafe_allow_html=True)
    with p_col2:
        st.caption("환자 상태 모니터링")
        # 로그 표시 영역 (최근 1건만)
        if st.session_state.log_history:
            st.code(st.session_state.log_history[-1], language="text")
        else:
            st.info("상태 버튼을 눌러보세요")

    st.write("") # 여백

    # 3. 상태 버튼 그리드 (4열 2행) - 이미지 참고 구현
    # 버튼 목록 정의 (라벨, 강조여부)
    status_buttons = [
        ("항암전체", False), ("NST", False), ("DNR", False), ("Device", True), # Device: Pink Text style (simulated)
        ("임신수유", False), ("섬망", True), ("DRG", False), ("진료회송", True)  # 섬망: Highlight style
    ]
    
    # 4개씩 나누어 배치
    for i in range(0, len(status_buttons), 4):
        cols = st.columns(4)
        for j in range(4):
            idx = i + j
            if idx < len(status_buttons):
                lbl, is_highlight = status_buttons[idx]
                
                # 섬망 버튼 등 강조가 필요한 경우 type="primary" 사용
                btn_type = "primary" if lbl == "섬망" else "secondary"
                
                # 버튼 클릭 상호작용
                if cols[j].button(lbl, key=f"stat_btn_{idx}", type=btn_type, use_container_width=True):
                    # 로그 기록
                    log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] '{lbl}' 상태 확인"
                    st.session_state.log_history.append(log_msg)

    # 4. 하단 컬러 아이콘 (혈액형, 감염 등) - 이미지 하단 4개 버튼
    c1, c2, c3, c4 = st.columns(4)
    c1.error("🩸\n혈액")  # 빨강
    c2.warning("💊\n투약") # 주황
    c3.success("🏃\n낙상") # 초록
    c4.info("R\n재활")   # 파랑

    st.divider()

    # 5. Patient List (환자 리스트)
    st.markdown("#### 🛏️ Patient List")
    
    # 리스트 생성 (버튼처럼 동작)
    for idx, p in enumerate(PATIENTS_DB):
        # 선택된 환자 표시용 이모지
        marker = "✅" if idx == st.session_state.current_pt_idx else ""
        btn_label = f"[{p['bed']}] {p['name']} {marker}"
        
        # 전체 너비 버튼으로 리스트 아이템 구현
        if st.button(btn_label, key=f"pt_list_{idx}", use_container_width=True):
            st.session_state.current_pt_idx = idx
            st.rerun() # 화면 갱신

    # 6. 하단 기능 메뉴
    st.write("")
    m1, m2, m3 = st.columns(3)
    m1.button("Memo")
    m2.button("To-Do")
    m3.button("Set")


# ==============================================================================
# [우측 메인 패널] 헤더, 탭, 상세 조회
# ==============================================================================
with col_main:
    
    # -------------------------------------------------------
    # 1. 최상단 헤더 바 (HTML/CSS 활용)
    # -------------------------------------------------------
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
                접속시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        <div style="margin-top: 5px; color: #81d4fa;">
            <span class="header-label">진단명:</span> <b>{curr_pt['diag']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------
    # 2. 의료진 정보 (2nd Row)
    # -------------------------------------------------------
    # EMR 상단 탭바 스타일 흉내
    i1, i2, i3, i4, i5 = st.columns([1, 1, 1, 1, 4])
    i1.info(f"전문의: {curr_pt['doc']}")
    i2.info(f"주치의: 이전공")
    i3.info(f"간호사: {curr_pt['nurse']}")
    i4.info("☎: 1234")
    
    st.write("") # 간격

    # -------------------------------------------------------
    # 3. 메인 기능 영역 (날짜 선택 + 오더 조회)
    # -------------------------------------------------------
    
    # 날짜 네비게이션
    d_col1, d_col2, d_col3 = st.columns([1, 2, 8])
    with d_col1:
        if st.button("◀ 이전"):
            st.session_state.selected_date -= datetime.timedelta(days=1)
            st.rerun()
    with d_col2:
        # 날짜 선택기
        new_date = st.date_input("조회일자", value=st.session_state.selected_date, label_visibility="collapsed")
        if new_date != st.session_state.selected_date:
            st.session_state.selected_date = new_date
            st.rerun()
    with d_col3:
        if st.button("다음 ▶"):
            st.session_state.selected_date += datetime.timedelta(days=1)
            st.rerun()

    # 메인 탭 (오더, 검사, 약 등)
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["💊 오더조회", "🧪 검사결과", "💉 약 정보", "📝 경과기록"])

    with m_tab1:
        # 오더 테이블 출력
        st.markdown(f"**[{st.session_state.selected_date}]** 오더 수행 내역")
        df_orders = get_orders(curr_pt['name'], st.session_state.selected_date)
        
        # 데이터프레임 스타일링 (use_container_width로 가로 꽉 차게)
        st.dataframe(
            df_orders, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "상태": st.column_config.TextColumn("상태", help="오더의 현재 진행 상태")
            }
        )

    with m_tab2:
        st.info("검사 결과 조회 화면입니다.")
        # 예시 테이블
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
st.markdown("---") # 구분선
# 범례 아이템 HTML 생성
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
