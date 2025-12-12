import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="SNUH Ward EMR - Smart Charting",
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
        font-family: 'Consolas', monospace; font-size: 45px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 10px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #90a4ae; font-size: 13px; font-weight: bold; letter-spacing: 1px; }

    /* 간호기록 텍스트 영역 스타일 */
    .note-entry {
        background-color: #2c3e50; padding: 15px; border-radius: 5px;
        border-left: 4px solid #0288d1; margin-bottom: 10px; font-size: 0.95em; line-height: 1.5;
    }
    .note-time { color: #81d4fa; font-weight: bold; margin-bottom: 5px; font-size: 0.9em; }

    /* 기타 스타일 */
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    .stButton > button { background-color: #37474f; color: white; border: 1px solid #455a64; }
    .risk-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin: 2px; border: 1px solid #ff5252; color: #ff867c; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 데이터 및 세션 초기화
# --------------------------------------------------------------------------------
if 'nursing_notes' not in st.session_state:
    # 기본 간호기록 데이터 (예시)
    st.session_state.nursing_notes = [
        {
            "time": "2025-12-12 08:00",
            "writer": "김분당",
            "content": "활력징후 측정함. dyspnea없음. DOE없음. Room air상태에서 산소포화도 적정수준(97%) 유지중임. 오심&구토 없음. 복부 불편감 없음."
        }
    ]

# 환자 DB
PATIENTS_DB = {
    '김수면': {'bed': '04-01', 'reg': '12345678', 'info': 'M/78', 'diag': 'Pneumonia', 'score': 92, 'braden': 12, 'factors': ['수면제 복용', '고령', '알부민 저하'], 'albumin': 2.8},
    '이보행': {'bed': '04-02', 'reg': '87654321', 'info': 'F/65', 'diag': 'Cerebral Infarction', 'score': 72, 'braden': 14, 'factors': ['편마비', '보행장애'], 'albumin': 3.8},
    '박섬망': {'bed': '05-01', 'reg': '11223344', 'info': 'M/82', 'diag': 'Femur Fracture', 'score': 45, 'braden': 13, 'factors': ['섬망', '수액라인'], 'albumin': 3.5},
    '정수진': {'bed': '05-02', 'reg': '55667788', 'info': 'F/32', 'diag': 'Acute Appendicitis', 'score': 15, 'braden': 18, 'factors': [], 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 4. [핵심 기능] 팝업창 & 자동 차팅 로직
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 **{datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    # 1. 위험요인 표시
    with c1:
        st.markdown("##### 🚨 감지된 위험요인")
        with st.container(border=True):
            if data['factors']:
                for f in data['factors']: st.error(f"• {f}")
            else: st.write("특이사항 없음")
            
    with c2:
        st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)

    # 2. 간호중재 체크리스트 (State 관리)
    with c3:
        st.markdown("##### ✅ 필수 간호 진술문 선택")
        with st.container(border=True):
            # 체크박스 상태를 변수에 저장
            chk_rail = False
            chk_med = False
            chk_nutri = False
            chk_position = False
            
            if data['score'] >= 40:
                chk_rail = st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
            if "수면제" in str(data['factors']):
                chk_med = st.checkbox("💊 수면제 투여 후 30분 관찰")
            if data['albumin'] < 3.0:
                chk_nutri = st.checkbox("🥩 영양팀 협진 의뢰 (알부민 저하)")
            if data['braden'] <= 14:
                chk_position = st.checkbox("🧴 2시간마다 체위 변경 (욕창 위험)")
            
            # 기본 교육 항목
            chk_edu = st.checkbox("📢 낙상 예방 교육 및 호출기 위치 안내", value=True)

    st.markdown("---")
    
    # 3. [저장 버튼] 클릭 시 자동 차팅 로직 실행
    if st.button("간호 수행 완료 및 기록 저장 (Auto-Charting)", type="primary", use_container_width=True):
        # (1) 문장 생성 로직
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        risk_factors_str = ", ".join(data['factors']) if data['factors'] else "특이 위험요인 없음"
        
        actions = []
        if chk_rail: actions.append("침상난간 2개 이상 올림 확인")
        if chk_med: actions.append("수면제 투여 후 30분간 의식상태/거동 관찰함")
        if chk_nutri: actions.append("영양 불균형 교정을 위해 영양팀 협진 의뢰함")
        if chk_position: actions.append("피부 통합성 유지를 위해 2시간마다 체위 변경 시행함")
        if chk_edu: actions.append("환자 및 보호자에게 낙상 위험성 알리고 호출기 사용법 교육함")
        
        action_str = ", ".join(actions)
        
        # (2) 최종 문장 조립 (선생님이 원하신 포맷)
        final_note_content = f"""낙상위험요인 확인함({risk_factors_str}) -> 중재시행 -> 
{action_str}. 낙상 예방을 위한 안전한 환경 조성하고 지속적으로 관찰함."""

        # (3) 세션에 저장 (DB 저장 흉내)
        new_note = {
            "time": current_time,
            "writer": "김분당",
            "content": final_note_content
        }
        st.session_state.nursing_notes.insert(0, new_note) # 최신 글을 맨 위로
        
        # (4) 알림 및 닫기
        st.toast("✅ 간호기록에 성공적으로 저장되었습니다!", icon="💾")
        time.sleep(1)
        st.rerun()

# --------------------------------------------------------------------------------
# 5. 메인 레이아웃
# --------------------------------------------------------------------------------
if 'current_pt_idx' not in st.session_state: st.session_state.current_pt_idx = 0
col_sidebar, col_main = st.columns([2, 8])
curr_pt = list(PATIENTS_DB.values())[st.session_state.current_pt_idx]
curr_pt_name = list(PATIENTS_DB.keys())[st.session_state.current_pt_idx]

# [좌측 사이드바]
with col_sidebar:
    st.markdown("### 🏥 재원 환자")
    idx = st.radio("환자 리스트", range(len(PATIENTS_DB)), format_func=lambda i: f"[{list(PATIENTS_DB.values())[i]['bed']}] {list(PATIENTS_DB.keys())[i]}", label_visibility="collapsed")
    st.session_state.current_pt_idx = idx
    st.markdown("---")
    
    # 디지털 계기판 (00 | 00)
    f_color = "#ff5252" if curr_pt['score'] >= 70 else ("#ffca28" if curr_pt['score'] >= 40 else "#00e5ff")
    b_color = "#ff5252" if curr_pt['braden'] <= 12 else ("#ffca28" if curr_pt['braden'] <= 14 else "#00e5ff")
    
    st.markdown(f"""
    <div class="digital-monitor-container">
        <div style="display:flex; justify-content:space-around; align-items:center;">
            <div style="text-align:center; width:45%;">
                <div class="monitor-label">FALL RISK</div>
                <div class="digital-number" style="color:{f_color};">{curr_pt['score']}</div>
            </div>
            <div style="text-align:center; width:45%;">
                <div class="monitor-label">BRADEN</div>
                <div class="digital-number" style="color:{b_color};">{curr_pt['braden']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 상세 분석 버튼
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="primary", use_container_width=True):
        show_risk_details(curr_pt_name, curr_pt)

# [우측 메인 화면]
with col_main:
    # 헤더
    st.markdown(f"""
    <div class="header-container">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center;">
                <span style="font-size:1.5em; font-weight:bold; color:white; margin-right:20px;">🏥 SNUH</span>
                <span class="header-info-text"><span class="header-label">환자명:</span> <b>{curr_pt_name}</b> ({curr_pt['reg']})</span>
                <span class="header-info-text">{curr_pt['info']}</span>
                <span class="header-info-text" style="color:#4fc3f7;">{curr_pt['diag']}</span>
            </div>
            <div style="color:#b0bec5; font-size:0.9em;">김분당 간호사 | {datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 탭 메뉴
    tab1, tab2, tab3 = st.tabs(["🛡️ 통합뷰", "💊 오더", "📝 간호기록(Auto-Note)"])

    # [Tab 1] 통합뷰
    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info("좌측 패널의 '상세 분석' 버튼을 눌러 자동 차팅을 시도해보세요.")
            st.markdown(f"**[현재 위험 요인]**")
            for f in curr_pt['factors']:
                st.markdown(f"<span class='risk-tag'>{f}</span>", unsafe_allow_html=True)
        with c2:
            st.markdown("**[V/S Summary]**")
            st.dataframe(pd.DataFrame({'BP':['120/80'], 'HR':[88], 'RR':[20], 'BT':[36.5]}), hide_index=True)

    # [Tab 2] 오더 (생략)
    with tab2: st.write("오더 화면")

    # [Tab 3] 간호기록 (여기가 핵심!)
    with tab3:
        st.markdown("##### 📝 간호진술문 (Nursing Note)")
        
        # 저장된 기록 출력 (최신순)
        for note in st.session_state.nursing_notes:
            st.markdown(f"""
            <div class="note-entry">
                <div class="note-time">📅 {note['time']} | 작성자: {note['writer']}</div>
                <div>{note['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # 수기 입력창 (추가 기록용)
        st.text_area("추가 기록 입력", placeholder="내용을 입력하세요...", height=100)
        st.button("수기 기록 저장")
