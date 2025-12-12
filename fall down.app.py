import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. [설정] 페이지 및 스타일
# --------------------------------------------------------------------------------
st.set_page_config(page_title="SNUH Fall-Guard", layout="wide")

st.markdown("""
<style>
    /* 전체 배경: EMR 다크 네이비 */
    .stApp { background-color: #1e2b3e; color: #e0e0e0; }
    
    /* 팝업창(모달) 스타일 조정 */
    div[data-testid="stDialog"] {
        background-color: #263859; color: white;
    }
    
    /* 상단 헤더 */
    .header-bar {
        background-color: #151f2e; padding: 15px; border-bottom: 2px solid #005eb8;
        display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;
    }

    /* 디지털 계기판 스타일 (00 | 00) */
    .digital-monitor {
        background-color: #000000; border: 2px solid #555; border-radius: 8px;
        padding: 20px; display: flex; justify-content: space-around; align-items: center;
        box-shadow: inset 0 0 30px rgba(0,0,0,0.9); margin-bottom: 10px;
    }
    .monitor-label { color: #aaa; font-size: 16px; font-weight: bold; margin-bottom: 5px; }
    .digital-number {
        font-family: 'Consolas', monospace; font-size: 60px; font-weight: 900; line-height: 1.0;
        text-shadow: 0 0 15px rgba(255,255,255,0.4);
    }
    .divider { width: 2px; height: 60px; background-color: #444; }

    /* 상세 보기 버튼 스타일 */
    .detail-btn-area { text-align: center; margin-top: 10px; }
    
    /* 폰트 설정 */
    h1, h2, h3, h4, p, div, span, label { font-family: 'Malgun Gothic', sans-serif; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. [데이터] 환자 케이스
# --------------------------------------------------------------------------------
patient_db = {
    '12345 김수면 (M/78)': {'score': 92, 'braden': 12, 'factors': ['수면제 복용', '알부민(2.8)', '고령'], 'ward': '72병동', 'albumin': 2.8},
    '67890 이보행 (F/65)': {'score': 72, 'braden': 14, 'factors': ['편마비', '보행 장애'], 'ward': '응급실', 'albumin': 3.8},
    '11223 박섬망 (M/82)': {'score': 45, 'braden': 13, 'factors': ['섬망', '수액 라인'], 'ward': '72병동', 'albumin': 3.5},
    '44556 최안전 (F/40)': {'score': 15, 'braden': 18, 'factors': [], 'ward': '응급실', 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 3. [기능] 팝업창(Dialog) 함수 구현 (그려주신 그림 UI)
# --------------------------------------------------------------------------------
@st.dialog("낙상/욕창 위험도 정밀 예측", width="large")
def show_risk_details(pt_data):
    # 1. 상단 문구 (그림의 "2025... 확률은 ()%입니다")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.info(f"🕒 **{now_str}** 기준, 24시간 이내 낙상할 확률은 **{pt_data['score']}%** 입니다.")
    
    st.write("") # 여백
    
    # 2. 좌우 배치 (위험요인 -> 화살표 -> 간호중재)
    c1, c2, c3 = st.columns([1, 0.2, 1])
    
    # [왼쪽 박스] 위험요인 List
    with c1:
        st.markdown("##### 🚨 감지된 위험요인 List")
        with st.container(border=True):
            if pt_data['factors']:
                for f in pt_data['factors']:
                    st.error(f"• {f}")
            else:
                st.write("특이 위험 요인 없음")
                
    # [중간] 화살표 (그림의 ➡ 모양)
    with c2:
        st.markdown("<div style='display:flex; height:200px; align-items:center; justify-content:center; font-size:40px;'>➡</div>", unsafe_allow_html=True)

    # [오른쪽 박스] 간호진술문(중재) List
    with c3:
        st.markdown("##### ✅ 필수 간호 진술문")
        with st.container(border=True):
            # 점수에 따른 동적 체크리스트
            if pt_data['score'] >= 40:
                st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
                st.checkbox("낙상 고위험 표지판 부착")
            if "수면제" in str(pt_data['factors']):
                st.checkbox("💊 수면제 투여 후 30분 관찰")
            if pt_data['albumin'] < 3.0:
                st.checkbox("🥩 영양팀 협진 의뢰 (알부민 저하)")
            if pt_data['braden'] <= 14:
                st.checkbox("🧴 2시간마다 체위 변경 (욕창 위험)")
                
    st.write("") # 여백
    
    # 3. 하단 저장 버튼
    if st.button("간호 수행 완료 및 닫기", type="primary", use_container_width=True):
        st.balloons()
        time.sleep(1)
        st.rerun()

# --------------------------------------------------------------------------------
# 4. [메인] 화면 구성
# --------------------------------------------------------------------------------

# 헤더
st.markdown("""
<div class="header-bar">
    <div style="font-size:18px; font-weight:bold; color:white;">
        SNUH <span style="color:#aaa;">환자 모니터링 대시보드</span>
    </div>
    <div style="font-size:14px; color:#ccc;">김분당 간호사</div>
</div>
""", unsafe_allow_html=True)

# 메인 레이아웃
col_left, col_right = st.columns([1.2, 2.5])

with col_left:
    st.markdown("##### 🔍 환자 선택")
    selected_pt_key = st.selectbox("환자 리스트", list(patient_db.keys()), label_visibility="collapsed")
    pt = patient_db[selected_pt_key]

    st.markdown("##### 📋 실시간 감시 (Monitor)")
    
    # 점수 색상 로직
    fall_color = "#ff4444" if pt['score'] >= 70 else ("#ffbb33" if pt['score'] >= 40 else "#00e5ff")
    ulcer_color = "#ff4444" if pt['braden'] <= 12 else ("#ffbb33" if pt['braden'] <= 14 else "#00e5ff")

    # [디지털 계기판 UI]
    st.markdown(f"""
    <div class="digital-monitor">
        <div style="text-align:center; width:45%;">
            <div class="monitor-label">낙상 위험도</div>
            <div class="digital-number" style="color: {fall_color};">{pt['score']}</div>
        </div>
        <div class="divider"></div>
        <div style="text-align:center; width:45%;">
            <div class="monitor-label">욕창 위험도</div>
            <div class="digital-number" style="color: {ulcer_color};">{pt['braden']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # [핵심] 팝업 띄우는 버튼
    st.markdown("---")
    st.info("👇 점수를 클릭하여 상세 내용을 확인하세요")
    if st.button("🔍 상세 분석 및 중재 기록 열기", type="secondary", use_container_width=True):
        show_risk_details(pt) # 팝업 함수 호출!

with col_right:
    # 오른쪽은 일반적인 EMR 차트 화면 흉내
    st.markdown(f"#### 📄 {selected_pt_key.split()[1]} 환자 EMR 차트")
    
    # 탭 메뉴
    tab1, tab2, tab3 = st.tabs(["경과기록(Progress Note)", "투약(Order)", "검사결과(Lab)"])
    
    with tab1:
        st.markdown(f"""
        <div style="background-color:#263859; padding:15px; border-radius:5px; height:300px;">
            <p style="color:#aaa;">[2025-12-12 14:00 간호기록]</p>
            <p>V/S stable함. 점심 식사 전량 섭취함.<br>
            보호자에게 낙상 주의 교육 실시하였으나, 환자 인지력 저하로 지속적인 관찰 필요함.</p>
            <p style="color:#aaa;">[2025-12-12 10:00 투약]</p>
            <p>처방된 수면제 PO 투여함.</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_area("추가 기록 작성", placeholder="특이사항 입력...")
