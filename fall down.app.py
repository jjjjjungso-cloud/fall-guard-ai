import streamlit as st
import pandas as pd
import time

# --------------------------------------------------------------------------------
# 1. [설정] 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(page_title="SNUH Fall-Guard", layout="wide")

# --------------------------------------------------------------------------------
# 2. [CSS] EMR 버튼 스타일 (그라데이션 & 입체감 구현)
# --------------------------------------------------------------------------------
st.markdown("""
<style>
    /* 전체 배경: EMR 다크 네이비 */
    .stApp { background-color: #1e2b3e; color: #e0e0e0; }
    
    /* 상단 헤더 */
    .header-bar {
        background-color: #151f2e; padding: 10px 20px; border-bottom: 2px solid #005eb8;
        display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;
    }

    /* EMR 아이콘 버튼 그리드 레이아웃 */
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr); /* 한 줄에 4개 */
        gap: 10px;
        margin-bottom: 20px;
    }

    /* 기본 버튼 스타일 (회색/남색 그라데이션) */
    .emr-button {
        background: linear-gradient(to bottom, #3c4a60, #2b3648);
        border: 1px solid #111;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.5);
        color: #bbb;
        height: 100px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }

    /* [핵심] 낙상 버튼 (동적 스타일) */
    .fall-button-high {
        background: linear-gradient(to bottom, #ff6b6b, #c0392b); /* 빨강 그라데이션 */
        color: white !important;
        border: 2px solid #ffcccc;
        animation: pulse 2s infinite; /* 깜빡이는 효과 */
    }
    .fall-button-mod {
        background: linear-gradient(to bottom, #f1c40f, #f39c12); /* 노랑 그라데이션 */
        color: black !important;
    }
    .fall-button-low {
        background: linear-gradient(to bottom, #2ecc71, #27ae60); /* 초록 그라데이션 */
        color: white !important;
    }

    /* 점수 텍스트 */
    .score-text {
        font-size: 28px;
        font-weight: 900;
        margin-top: 5px;
        line-height: 1.0;
    }
    
    .label-text { font-size: 14px; font-weight: bold; margin-bottom: 2px; }
    
    /* 깜빡임 애니메이션 (고위험군용) */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. [데이터] 환자 케이스
# --------------------------------------------------------------------------------
patient_db = {
    '12345 김수면 (M/78)': {'score': 92, 'factors': ['수면제', '알부민(2.8)'], 'ward': '72병동', 'albumin': 2.8},
    '67890 이보행 (F/65)': {'score': 72, 'factors': ['편마비'], 'ward': '응급실', 'albumin': 3.8},
    '11223 박섬망 (M/82)': {'score': 45, 'factors': ['섬망'], 'ward': '72병동', 'albumin': 3.5},
    '44556 최안전 (F/40)': {'score': 15, 'factors': [], 'ward': '응급실', 'albumin': 4.2}
}

# --------------------------------------------------------------------------------
# 4. [헤더]
# --------------------------------------------------------------------------------
st.markdown("""
<div class="header-bar">
    <div style="font-size:18px; font-weight:bold; color:white;">
        SNUH <span style="color:#aaa;">환자 대시보드</span>
    </div>
    <div style="font-size:14px; color:#ccc;">김분당 간호사</div>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 5. [메인 화면]
# --------------------------------------------------------------------------------
col_left, col_right = st.columns([1.2, 2.5])

with col_left:
    st.markdown("##### 🔍 환자 선택")
    selected_pt_key = st.selectbox("label", list(patient_db.keys()), label_visibility="collapsed")
    pt = patient_db[selected_pt_key]

    st.markdown("##### 📋 환자 상태 (Patient Status)")
    
    # 1. 낙상 버튼 스타일 결정
    if pt['score'] >= 70:
        btn_class = "fall-button-high"
        icon = "🏃‍♂️💥" 
        label = "낙상 고위험"
    elif pt['score'] >= 40:
        btn_class = "fall-button-mod"
        icon = "⚠️"
        label = "낙상 주의"
    else:
        btn_class = "fall-button-low"
        icon = "🛡️"
        label = "낙상 안전"
        
    # 2. HTML로 버튼 그리드 그리기 (주석을 제거하여 오류 방지)
    st.markdown(f"""
    <div class="dashboard-grid">
        <div class="emr-button">
            <div style="font-size:20px;">🩸</div>
            <div class="label-text">혈액형</div>
            <div style="font-size:14px;">A+</div>
        </div>
        <div class="emr-button">
            <div style="font-size:20px;">💊</div>
            <div class="label-text">투약</div>
            <div style="font-size:14px;">완료</div>
        </div>
        <div class="emr-button">
            <div style="font-size:20px;">🦠</div>
            <div class="label-text">감염</div>
            <div style="font-size:14px;">-</div>
        </div>
        <div class="emr-button {btn_class}">
            <div style="font-size:24px;">{icon}</div>
            <div class="label-text">{label}</div>
            <div class="score-text">{pt['score']}점</div>
        </div>
        <div class="emr-button">
            <div class="label-text">욕창</div>
            <div style="color:green;">저위험</div>
        </div>
        <div class="emr-button">
            <div class="label-text">통증</div>
            <div>3점</div>
        </div>
        <div class="emr-button">
            <div class="label-text">식이</div>
            <div>LD</div>
        </div>
        <div class="emr-button">
            <div class="label-text">배설</div>
            <div>정상</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("👆 위 대시보드에서 '낙상' 버튼의 색상과 점수가 실시간으로 변합니다.")

with col_right:
    # (오른쪽 패널 코드는 기존과 동일하므로 그대로 두시면 됩니다)
    st.markdown(f"#### ✅ {selected_pt_key.split()[1]} 환자 간호 중재")
    
    with st.container(border=True):
        st.write("**감지된 위험 요인:**")
        for f in pt['factors']:
            st.markdown(f"- 🔴 {f}")
        
        st.markdown("---")
        st.markdown("**[필수 간호 활동]**")
        
        if pt['score'] >= 40:
            st.checkbox("침상 난간(Side Rail) 올림 확인", value=True)
            st.checkbox("낙상 고위험 표지판 부착")
        if "수면제" in str(pt['factors']):
            st.checkbox("수면제 투여 후 30분 관찰")
        if pt['albumin'] < 3.0:
            st.checkbox("영양팀 협진 의뢰 (알부민 저하)")
            
        st.button("간호 수행 완료 및 저장 (Save)", use_container_width=True)
