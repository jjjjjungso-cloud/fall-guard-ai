import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. [설정] 페이지 설정 (Wide Mode & 사이드바 확장)
# --------------------------------------------------------------------------------
st.set_page_config(page_title="SNUH BESTCARE 2.0 - Fall Guard", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------------
# 2. [스타일] EMR 다크모드 + 디지털 계기판 + 환자정보바 CSS
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    /* 기본 폰트 및 배경 (다크 네이비) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    .stApp { 
        background-color: #1e2b3e; /* 베스트케어 메인 배경색 */
        color: #e0e0e0; 
        font-family: 'Noto Sans KR', sans-serif; 
    }
    
    /* [상단] 환자 정보 스트립 (Patient Info Bar) */
    .patient-strip {
        background: linear-gradient(to bottom, #3a4b66, #2a364a);
        padding: 8px 15px; 
        border-top: 3px solid #f39c12; /* 상단 포인트 컬러 */
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border-radius: 4px;
    }
    .profile-box {
        background-color: #d65db1; /* 프로필 아이콘 배경 (분홍) */
        width: 45px; height: 45px; border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; margin-right: 15px; box-shadow: inset 0 0 10px rgba(0,0,0,0.2);
    }
    .pt-info-text { font-size: 13px; color: #ddd; line-height: 1.4; margin-right: 15px; border-right: 1px solid #555; padding-right: 15px; }
    .pt-name-large { font-size: 20px; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px black; margin-right: 10px; }
    
    /* [카드] 컨텐츠 박스 스타일 */
    .css-card {
        background-color: #263859; padding: 20px; border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #3a4b66;
    }

    /* [하단] 디지털 계기판 (검은색 모니터 박스) */
    .digital-monitor-container {
        background-color: #000000; 
        border: 2px solid #555; border-radius: 8px;
        padding: 15px; margin-top: 10px;
        box-shadow: inset 0 0 30px rgba(0,0,0,0.9);
    }
    .monitor-row { display: flex; justify-content: space-around; align-items: center; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 55px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 15px rgba(255,255,255,0.4); margin-top: 5px;
    }
    .monitor-label { color: #888; font-size: 14px; font-weight: bold; letter-spacing: 1px; }

    /* 위험 요인 태그 */
    .risk-tag {
        display: inline-block; padding: 4px 10px; border-radius: 15px; 
        font-size: 13px; margin: 2px; font-weight: bold; background-color: rgba(255,0,0,0.2); border: 1px solid #ff4444; color: #ffcccc;
    }
    
    /* 팝업(모달) 스타일 */
    div[data-testid="stDialog"] { background-color: #2e3b4e; color: white; }
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] { background-color: #151f2e; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { background-color: #2b3648; color: #aaa; border-radius: 4px 4px 0 0; padding: 5px 20px; }
    .stTabs [aria-selected="true"] { background-color: #005eb8; color: white; font-weight: bold; }
    
    /* 버튼 스타일 */
    .stButton > button { background-color: #005eb8; color: white; border: none; font-weight: bold; }
    .stButton > button:hover { background-color: #004a99; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. [데이터] 환자 DB (기존 데이터 + 욕창 점수/침상번호 추가)
# --------------------------------------------------------------------------------
patient_db = {
    '김수면': {'bed': '04-01', 'reg': '12345', 'info': 'M/78세', 'diag': 'Pneumonia (폐렴)', 'score': 92, 'braden': 12, 'factors': ['수면제 복용', '고령', '알부민 저하(2.8)'], 'ward': '72병동', 'albumin': 2.8},
    '이보행': {'bed': '04-02', 'reg': '67890', 'info': 'F/65세', 'diag': 'Cerebral Infarction (뇌경색)', 'score': 72, 'braden': 14, 'factors': ['편마비', '보행 장애'], 'ward': '응급실', 'albumin': 3.8},
    '박섬망': {'bed': '05-01', 'reg': '11223', 'info': 'M/82세', 'diag': 'Femur Fracture (대퇴골절)', 'score': 45, 'braden': 13, 'factors': ['섬망', '수액 라인'], 'ward': '72병동', 'albumin': 3.5},
    '최안전': {'bed': '05-02', 'reg': '44556', 'info': 'F/40세', 'diag': 'Acute Appendicitis', 'score': 15, 'braden': 18, 'factors': [], 'ward': '응급실', 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 4. [기능] 팝업창 함수 (상세 분석 및 중재)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 분석", width="large")
def show_risk_details(name, data):
    st.info(f"🕒 **{datetime.now().strftime('%Y-%m-%d %H:%M')}** 기준, {name} 님의 분석 결과입니다.")
    
    # 3단 레이아웃: 위험요인 -> 화살표 -> 간호중재
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    with c1:
        st.markdown("##### 🚨 감지된 위험요인 List")
        with st.container(border=True):
            if data['factors']:
                for f in data['factors']: st.error(f"• {f}")
            else: st.write("특이사항 없음")
            
    with c2:
        st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("##### ✅ 필수 간호 진술문")
        with st.container(border=True):
            # 점수/요인 기반 체크리스트 자동 생성
            if data['score'] >= 40:
                st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
                st.checkbox("낙상 고위험 표지판 부착")
            if "수면제" in str(data['factors']):
                st.checkbox("💊 수면제 투여 후 30분 관찰")
            if data['albumin'] < 3.0:
                st.checkbox("🥩 영양팀 협진 의뢰 (알부민 저하)")
            if data['braden'] <= 14:
                st.checkbox("🧴 2시간마다 체위 변경 (욕창 위험)")
                
    st.write("")
    if st.button("간호 수행 완료 및 닫기", type="primary", use_container_width=True):
        st.rerun()

# --------------------------------------------------------------------------------
# 5. [레이아웃] 메인 화면 구성
# --------------------------------------------------------------------------------

# (1) 사이드바: 환자 리스트 (침상 번호 스타일)
with st.sidebar:
    st.markdown("### 🏥 재원 환자 (Ward 72)")
    # 라디오 버튼 커스텀 (침상번호 표시)
    selected_pt_name = st.radio(
        "환자 선택",
        list(patient_db.keys()),
        format_func=lambda x: f"[{patient_db[x]['bed']}] {x}", 
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("※ 침상 번호를 클릭하여 환자를 변경하세요.")
    st.image("https://via.placeholder.com/250x100/151f2e/666666?text=Memo+Area", use_column_width=True)

# 선택된 환자 데이터 로드
pt = patient_db[selected_pt_name]

# (2) 상단 환자 정보 스트립 (EMR 스타일 완벽 재현)
st.markdown(f"""
<div class="patient-strip">
    <div style="display:flex; align-items:center;">
        <div class="profile-box">👤</div> <div style="display:flex; align-items:center;">
            <div class="pt-name-large">{selected_pt_name}</div>
            <div class="pt-info-text">등록번호: {pt['reg']}</div>
            <div class="pt-info-text">{pt['info']}</div>
            <div class="pt-info-text">진단명: {pt['diag']}</div>
            <div class="pt-info-text" style="border:none;">주치의: 김닥터</div>
        </div>
    </div>
    <div>
        <div style="text-align:right; font-size:12px; color:#ccc;">최근접속: {datetime.now().strftime('%Y.%m.%d')}</div>
        <div style="background:#ff5252; color:white; padding:2px 10px; font-size:12px; border-radius:3px; text-align:center; margin-top:2px;">알러지: 없음</div>
    </div>
</div>
""", unsafe_allow_html=True)

# (3) 메인 탭 (Fall-Guard AI 기능을 '통합뷰' 탭에 배치)
tab1, tab2, tab3 = st.tabs(["🛡️ Fall-Guard AI (통합뷰)", "💊 오더수행", "📝 간호기록"])

with tab1:
    col_left, col_right = st.columns([1.2, 2])
    
    # === [왼쪽 패널] AI 모니터링 & 디지털 계기판 ===
    with col_left:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown("##### 🚨 AI 실시간 감시 (Real-time Monitor)")
        st.info("AI가 분석한 낙상/욕창 위험도입니다. 하단 점수를 클릭하면 상세 분석이 가능합니다.")
        
        # 위험 요인 태그
        st.write("**[감지된 주요 위험 요인]**")
        tags_html = ""
        for f in pt['factors']:
            tags_html += f"<span class='risk-tag'>{f}</span>"
        if not pt['factors']: tags_html = "<span style='color:#00e5ff'>✔ 특이사항 없음</span>"
        st.markdown(tags_html, unsafe_allow_html=True)

        # 색상 로직 (점수에 따라 변함)
        f_color = "#ff4444" if pt['score'] >= 70 else ("#ffbb33" if pt['score'] >= 40 else "#00e5ff")
        b_color = "#ff4444" if pt['braden'] <= 12 else ("#ffbb33" if pt['braden'] <= 14 else "#00e5ff")

        # [디지털 계기판] 00 | 00 스타일
        st.markdown(f"""
        <div class="digital-monitor-container">
            <div class="monitor-row">
                <div style="text-align:center; width:45%; border-right:1px solid #333;">
                    <div class="monitor-label">FALL RISK</div>
                    <div class="digital-number" style="color: {f_color};">{pt['score']}</div>
                    <div style="color:{f_color}; font-size:12px;">{'🔴 고위험' if pt['score']>=70 else '🟢 저위험'}</div>
                </div>
                <div style="text-align:center; width:45%;">
                    <div class="monitor-label">BRADEN</div>
                    <div class="digital-number" style="color: {b_color};">{pt['braden']}</div>
                    <div style="color:{b_color}; font-size:12px;">{'🔴 고위험' if pt['braden']<=12 else '🟢 저위험'}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        # 팝업 버튼 (계기판 아래)
        if st.button("🔍 상세 분석 및 중재 입력 (Pop-up)", type="secondary", use_container_width=True):
            show_risk_details(selected_pt_name, pt)
        st.markdown('</div>', unsafe_allow_html=True)

    # === [오른쪽 패널] 간호 중재 체크리스트 (기존 코드 기능) ===
    with col_right:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.markdown(f"##### ✅ {selected_pt_name} 환자 우선순위 중재")
        
        # 체크리스트 로직 (메인 화면에서도 바로 체크 가능하게)
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**[환경/안전]**")
            st.checkbox("낙상 표지판 부착 확인", value=True if pt['score'] >= 60 else False, key="chk_sign")
            st.checkbox("침상 난간(Side Rail) 고정", value=True, key="chk_rail")
            if "섬망" in str(pt['factors']):
                st.checkbox("야간 조명 점등 및 억제대 확인", key="chk_delirium")
        
        with cols[1]:
            st.markdown("**[환자/약물]**")
            if "수면제" in str(pt['factors']):
                st.checkbox("투약 후 30분 침상 안정 교육", key="chk_sleep")
            if pt['albumin'] < 3.0:
                st.checkbox("🚫 영양팀 협진 의뢰 (알부민 저하)", key="chk_nutri")
            st.checkbox("보호자 상주 및 호출기 교육", key="chk_call")

        st.markdown("---")
        st.caption("※ 위 체크리스트는 AI가 추천하는 우선순위 항목입니다.")
        if st.button("간호 수행 완료 및 기록 (Save)", key="save_main"):
            with st.spinner("EMR 서버 전송 중..."):
                time.sleep(0.5)
            st.success("✅ EMR 간호기록에 성공적으로 저장되었습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

        # (장식용) 트렌드 차트
        st.markdown("##### 📈 위험도 변화 추이 (24hr Trend)")
        chart_data = pd.
