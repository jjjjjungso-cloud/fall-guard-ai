import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. [설정] 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(page_title="SNUH Ward EMR - Fall Guard", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------------
# 2. [스타일] EMR 다크모드 + 디지털 계기판 + 팝업 스타일
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    /* 기본 배경 및 폰트 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    .stApp { background-color: #1e252b; color: #e0e0e0; font-family: 'Noto Sans KR', sans-serif; }

    /* [상단] 환자 정보 스트립 */
    .patient-strip {
        background: linear-gradient(to bottom, #37474f, #263238);
        padding: 10px 15px; border-top: 3px solid #039be5;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border-radius: 4px;
    }
    .profile-box {
        background-color: #ec407a; /* 분홍색 프로필 배경 */
        width: 45px; height: 45px; border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; margin-right: 15px; color: white;
    }
    .pt-info-item { margin-right: 15px; border-right: 1px solid #555; padding-right: 15px; font-size: 0.9em; color: #cfd8dc; }
    .pt-name-large { font-size: 1.4em; font-weight: bold; color: white; margin-right: 10px; }

    /* [핵심] 디지털 계기판 스타일 (검은색 박스) */
    .digital-monitor-container {
        background-color: #000000; 
        border: 2px solid #455a64; border-radius: 8px;
        padding: 20px; margin-top: 15px; margin-bottom: 15px;
        box-shadow: inset 0 0 30px rgba(0,0,0,0.8);
    }
    .monitor-row { display: flex; justify-content: space-around; align-items: center; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 60px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 15px rgba(255,255,255,0.4); margin-top: 10px;
    }
    .monitor-label { color: #90a4ae; font-size: 14px; font-weight: bold; letter-spacing: 1px; }
    
    /* 위험 요인 태그 */
    .risk-tag {
        display: inline-block; padding: 4px 12px; border-radius: 15px; 
        font-size: 13px; margin: 3px; font-weight: bold; 
        background-color: rgba(255, 82, 82, 0.15); border: 1px solid #ff5252; color: #ff867c;
    }

    /* 팝업(모달) 스타일 */
    div[data-testid="stDialog"] { background-color: #263238; color: #eceff1; }
    
    /* 사이드바 환자 리스트 버튼 */
    .stButton button { width: 100%; text-align: left; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #37474f; color: #b0bec5; border: none; }
    .stTabs [aria-selected="true"] { background-color: #0288d1; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. [데이터] 환자 DB
# --------------------------------------------------------------------------------
patient_db = {
    '김수면': {'bed': '04-01', 'reg': '12345678', 'info': 'M/78', 'diag': 'Pneumonia', 'score': 92, 'braden': 12, 'factors': ['수면제', '알부민(2.8)', '고령'], 'albumin': 2.8},
    '이보행': {'bed': '04-02', 'reg': '87654321', 'info': 'F/65', 'diag': 'Cerebral Infarction', 'score': 72, 'braden': 14, 'factors': ['편마비', '보행장애'], 'albumin': 3.8},
    '박섬망': {'bed': '05-01', 'reg': '11223344', 'info': 'M/82', 'diag': 'Femur Fracture', 'score': 45, 'braden': 13, 'factors': ['섬망', '수액라인'], 'albumin': 3.5},
    '정수진': {'bed': '05-02', 'reg': '55667788', 'info': 'F/32', 'diag': 'Acute Appendicitis', 'score': 15, 'braden': 18, 'factors': [], 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 4. [기능] 팝업 함수 (그려주신 그림 구조 반영)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 **{datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    # 레이아웃: [왼쪽 박스] -> [화살표] -> [오른쪽 박스]
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    with c1:
        st.markdown("##### 🚨 위험요인 (Risk Factors)")
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
            if data['score'] >= 40: st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
            if "수면제" in str(data['factors']): st.checkbox("💊 수면제 투여 후 30분 관찰")
            if data['albumin'] < 3.0: st.checkbox("🥩 영양팀 협진 의뢰")
            if data['braden'] <= 14: st.checkbox("🧴 2시간마다 체위 변경")
            
    st.write("")
    if st.button("간호 수행 완료 및 닫기", type="primary", use_container_width=True):
        st.rerun()

# --------------------------------------------------------------------------------
# 5. [레이아웃] 메인 화면 구성
# --------------------------------------------------------------------------------

# (1) 사이드바: 환자 리스트
with st.sidebar:
    st.title("🏥 Ward 72")
    st.selectbox("근무 Duty", ["Day", "Evening", "Night"])
    st.markdown("---")
    
    # 환자 선택 (라디오 버튼)
    selected_pt_name = st.radio(
        "환자 리스트",
        list(patient_db.keys()),
        format_func=lambda x: f"[{patient_db[x]['bed']}] {x}",
        label_visibility="collapsed"
    )

pt = patient_db[selected_pt_name]

# (2) 상단 환자 정보 스트립 (EMR 스타일)
st.markdown(f"""
<div class="patient-strip">
    <div style="display:flex; align-items:center;">
        <div class="profile-box">👤</div>
        <div style="display:flex; align-items:center;">
            <div class="pt-name-large">{selected_pt_name}</div>
            <div class="pt-info-item">ID: {pt['reg']}</div>
            <div class="pt-info-item">{pt['info']}</div>
            <div class="pt-info-item" style="color:#81d4fa; font-weight:bold;">{pt['diag']}</div>
            <div class="pt-info-item" style="border:none;">Dr. 김주치</div>
        </div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:0.8em; color:#b0bec5;">Login: 김간호</div>
        <div style="font-size:0.8em; color:#b0bec5;">{datetime.now().strftime('%Y-%m-%d')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# (3) 메인 탭 (여기에 디지털 계기판 배치!)
tab1, tab2, tab3 = st.tabs(["🛡️ Fall-Guard (통합뷰)", "💊 오더조회", "📝 간호기록"])

with tab1:
    # 2단 분할 (왼쪽: AI 모니터 / 오른쪽: 체크리스트)
    col_left, col_right = st.columns([1.2, 2])
    
    # === [왼쪽] AI 모니터링 영역 ===
    with col_left:
        st.markdown("#### 🚨 AI Risk Monitor")
        st.info("실시간 데이터 분석 결과입니다.")
        
        # 위험요인 태그
        st.write("**[감지된 주요 위험 요인]**")
        tags_html = ""
        for f in pt['factors']:
            tags_html += f"<span class='risk-tag'>{f}</span>"
        if not pt['factors']: tags_html = "<span style='color:#00e676'>✔ 특이사항 없음</span>"
        st.markdown(tags_html, unsafe_allow_html=True)

        # ----------------------------------------------------
        # [★ 여기입니다] 디지털 계기판 (00 | 00)
        # ----------------------------------------------------
        # 점수에 따른 색상 결정
        f_color = "#ff5252" if pt['score'] >= 70 else ("#ffca28" if pt['score'] >= 40 else "#00e5ff")
        b_color = "#ff5252" if pt['braden'] <= 12 else ("#ffca28" if pt['braden'] <= 14 else "#00e5ff")
        
        st.markdown(f"""
        <div class="digital-monitor-container">
            <div class="monitor-row">
                <div style="text-align:center; width:45%; border-right:1px solid #444;">
                    <div class="monitor-label">FALL RISK SCORE</div>
                    <div class="digital-number" style="color: {f_color};">{pt['score']}</div>
                    <div style="color:{f_color}; font-size:12px;">{'🔴 고위험' if pt['score']>=70 else '🟢 저위험'}</div>
                </div>
                <div style="text-align:center; width:45%;">
                    <div class="monitor-label">BRADEN SCALE</div>
                    <div class="digital-number" style="color: {b_color};">{pt['braden']}</div>
                    <div style="color:{b_color}; font-size:12px;">{'🔴 고위험' if pt['braden']<=12 else '🟢 저위험'}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # [★ 여기입니다] 팝업 버튼
        st.write("")
        if st.button("🔍 상세 분석 및 중재 기록 열기 (Click)", type="primary", use_container_width=True):
            show_risk_details(selected_pt_name, pt)

    # === [오른쪽] 빠른 체크리스트 (기존 유지) ===
    with col_right:
        st.markdown(f"#### ✅ {selected_pt_name}님 우선순위 중재")
        with st.container(border=True):
            st.caption("AI가 추천하는 필수 간호 활동입니다.")
            
            # 빠른 체크리스트
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**[안전/환경]**")
                st.checkbox("침상 난간 올림", value=True, key="main_rail")
                st.checkbox("낙상 표지판 부착", key="main_sign")
            with cols[1]:
                st.markdown("**[환자/약물]**")
                if "수면제" in str(pt['factors']):
                    st.checkbox("수면제 투여 후 관찰", key="main_sleep")
                if pt['albumin'] < 3.0:
                    st.checkbox("영양팀 협진 의뢰", key="main_nutri")
            
            st.write("")
            if st.button("저장 (Save)", key="main_save"):
                with st.spinner("저장 중..."):
                    time.sleep(0.5)
                st.success("저장 완료")

with tab2:
    st.write("오더 조회 화면입니다.")

with tab3:
    st.write("간호 기록 화면입니다.")
