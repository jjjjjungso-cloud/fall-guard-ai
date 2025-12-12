import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. [설정] 페이지 설정 (Wide Mode)
# --------------------------------------------------------------------------------
st.set_page_config(page_title="SNUH BESTCARE 2.0", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------------
# 2. [스타일] 실제 EMR(바탕화면.jpg) 느낌을 살리는 CSS
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    /* 폰트 및 기본 배경 (EMR 다크 그레이) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    .stApp { 
        background-color: #333333; /* 바탕화면.jpg의 배경색 */
        color: #e0e0e0; 
        font-family: 'Noto Sans KR', sans-serif; 
    }
    
    /* [상단] 환자 정보 스트립 (분홍색 프로필 아이콘 재현) */
    .patient-strip {
        background: linear-gradient(to bottom, #4a5b70, #2e3b4e);
        padding: 5px 10px; 
        border-top: 3px solid #f39c12; /* 상단 오렌지 라인 */
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .profile-box {
        background-color: #d65db1; /* 프로필 사진 배경 (분홍색) */
        width: 50px; height: 50px; border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        font-size: 30px; margin-right: 15px; box-shadow: inset 0 0 10px rgba(0,0,0,0.2);
    }
    .pt-info-text { font-size: 14px; color: #fff; line-height: 1.4; }
    .pt-name-large { font-size: 20px; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px black; }
    
    /* [하단] 디지털 계기판 (검은색 박스) - 요청하신 위치 */
    .digital-monitor-container {
        margin-top: 20px; /* 위쪽 여백 */
        background-color: #000000; 
        border: 2px solid #555; border-radius: 8px;
        padding: 15px; 
        box-shadow: inset 0 0 30px rgba(0,0,0,0.9);
    }
    .monitor-row { display: flex; justify-content: space-around; align-items: center; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 60px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 15px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #888; font-size: 14px; font-weight: bold; letter-spacing: 1px; }
    
    /* 팝업 스타일 */
    div[data-testid="stDialog"] { background-color: #2e3b4e; color: white; }
    
    /* 사이드바 스타일 (침상 리스트 느낌) */
    section[data-testid="stSidebar"] { background-color: #252525; }
    .sidebar-bed-item {
        background-color: #3a3a3a; border-left: 4px solid #888; padding: 8px; margin-bottom: 5px; cursor: pointer;
    }
    .bed-active { border-left: 4px solid #00e5ff; background-color: #444; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 1px; background-color: #222; }
    .stTabs [data-baseweb="tab"] {
        background-color: #333; color: #aaa; border: 1px solid #444; padding: 5px 15px; font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #005eb8; /* 선택된 탭 파란색 */
        color: white; font-weight: bold; border-top: 2px solid #00aaff;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. [데이터] 환자 케이스 (진단명 등 추가)
# --------------------------------------------------------------------------------
patient_db = {
    '김수면': {'bed': '04-01', 'reg': '12345', 'info': 'M/78세', 'diag': 'Pneumonia (폐렴)', 'score': 92, 'braden': 12, 'factors': ['수면제', '알부민(2.8)'], 'albumin': 2.8},
    '이보행': {'bed': '04-02', 'reg': '67890', 'info': 'F/65세', 'diag': 'Cerebral Infarction (뇌경색)', 'score': 72, 'braden': 14, 'factors': ['편마비', '보행장애'], 'albumin': 3.8},
    '박섬망': {'bed': '05-01', 'reg': '11223', 'info': 'M/82세', 'diag': 'Femur Fracture (대퇴골절)', 'score': 45, 'braden': 13, 'factors': ['섬망', '수액라인'], 'albumin': 3.5},
    '최안전': {'bed': '05-02', 'reg': '44556', 'info': 'F/40세', 'diag': 'Acute Appendicitis', 'score': 15, 'braden': 18, 'factors': [], 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 4. [기능] 팝업 함수 (그림과 동일한 UI)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준, {name} 님의 분석 결과입니다.")
    
    c1, c2, c3 = st.columns([1, 0.2, 1])
    with c1:
        st.markdown("##### 🚨 위험요인 (Risk Factors)")
        with st.container(border=True):
            if data['factors']:
                for f in data['factors']: st.error(f"• {f}")
            else: st.write("특이사항 없음")
    with c2:
        st.markdown("<div style='font-size:40px; text-align:center; margin-top:50px;'>➡</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("##### ✅ 필수 간호 중재 (Intervention)")
        with st.container(border=True):
            if data['score'] >= 40: st.checkbox("침상 난간(Side Rail) 올림", value=True)
            if "수면제" in str(data['factors']): st.checkbox("💊 수면제 투여 후 30분 관찰")
            if data['albumin'] < 3.0: st.checkbox("🥩 영양팀 협진 의뢰")
            if data['braden'] <= 14: st.checkbox("🧴 2시간마다 체위 변경")
            
    if st.button("간호 수행 완료 및 닫기", type="primary", use_container_width=True):
        st.rerun()

# --------------------------------------------------------------------------------
# 5. [메인] 화면 구성
# --------------------------------------------------------------------------------

# (1) 사이드바: 환자 리스트 (침상 번호 스타일)
with st.sidebar:
    st.markdown("### 🏥 재원 환자 (Ward 72)")
    selected_pt_name = st.radio(
        "환자 선택",
        list(patient_db.keys()),
        format_func=lambda x: f"[{patient_db[x]['bed']}] {x}", # 침상번호 표시
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("※ 침상 번호를 클릭하여 환자를 변경하세요.")

pt = patient_db[selected_pt_name]

# (2) 상단 환자 정보 스트립 (EMR 스타일 재현)
st.markdown(f"""
<div class="patient-strip">
    <div style="display:flex; align-items:center;">
        <div class="profile-box">👤</div> <div>
            <div class="pt-name-large">{selected_pt_name} <span style="font-size:14px; font-weight:normal;">({pt['reg']})</span></div>
            <div class="pt-info-text">{pt['info']} | {pt['diag']}</div>
            <div class="pt-info-text">주치의: 김닥터 | 입원일: 2025-12-01</div>
        </div>
    </div>
    <div>
        <div style="text-align:right; font-size:12px; color:#ccc;">최근접속: {datetime.now().strftime('%Y.%m.%d')}</div>
        <div style="background:#ff5252; color:white; padding:2px 8px; font-size:12px; border-radius:2px; text-align:center;">알러지: 없음</div>
    </div>
</div>
""", unsafe_allow_html=True)

# (3) 메인 탭 (통합뷰 / 오더 / 간호기록)
tab1, tab2, tab3 = st.tabs(["📌 통합상세뷰(Summary)", "💊 오더수행(Order)", "📝 간호기록(Note)"])

with tab1:
    col_main, col_sub = st.columns([2, 1])
    
    # === [왼쪽] AI 분석 패널 ===
    with col_main:
        st.markdown(f"#### 🛡️ AI 낙상/욕창 실시간 감시")
        st.info("💡 실시간 EMR 데이터를 분석하여 산출된 결과입니다. 하단 점수를 클릭하면 상세 내용을 볼 수 있습니다.")

        # 위험 요인 태그 (상단 배치)
        st.write("**[감지된 주요 위험 요인]**")
        if pt['factors']:
            for f in pt['factors']:
                st.markdown(f"<span style='background:#4a2c2c; color:#ffcccc
