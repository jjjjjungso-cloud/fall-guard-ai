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
# 5. [메인 화면] UI 구성
# --------------------------------------------------------------------------------
col_left, col_right = st.columns([1.2, 2.5])

with col_left:
    st.markdown("##### 🔍 환자 선택")
    
    # [데이터 수정] 욕창 점수(braden)가 없는 경우를 대비해 기본값 설정
    for p in patient_db:
        if 'braden' not in patient_db[p]:
            patient_db[p]['braden'] = 18 # 기본값 (정상)

    selected_pt_key = st.selectbox("label", list(patient_db.keys()), label_visibility="collapsed")
    pt = patient_db[selected_pt_key]

    st.markdown("##### 📋 환자 상태 모니터링")
    
    # 1. 낙상 점수 색상 (높을수록 위험)
    if pt['score'] >= 70:
        fall_color = "#ff4444" # 빨강 (고위험)
    elif pt['score'] >= 40:
        fall_color = "#ffbb33" # 노랑 (중위험)
    else:
        fall_color = "#00e5ff" # 청록색 (안전 - 모니터 느낌)
        
    # 2. 욕창 점수 색상 (낮을수록 위험)
    # 예: 12점 이하 고위험, 14점 이하 중위험
    braden_score = pt.get('braden', 18) 
    if braden_score <= 12:
        ulcer_color = "#ff4444"
    elif braden_score <= 14:
        ulcer_color = "#ffbb33"
    else:
        ulcer_color = "#00e5ff" # 청록색

    # 3. [핵심] 디지털 계기판 스타일 (00 | 00)
    # 들여쓰기 문제를 해결하기 위해 HTML을 한 줄로 붙이거나, textwrap.dedent를 쓰지 않고 직접 작성합니다.
    st.markdown(f"""
    <style>
        .digital-monitor {{
            background-color: #000000; 
            border: 2px solid #333;
            border-radius: 6px;
            padding: 15px;
            display: flex;
            justify-content: space-around;
            align-items: center;
            margin-bottom: 20px;
            box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
        }}
        .score-box {{ text-align: center; width: 45%; }}
        .monitor-label {{
            color: #aaaaaa; font-size: 16px; font-weight: bold;
            margin-bottom: 5px; font-family: 'Malgun Gothic', sans-serif;
        }}
        .digital-number {{
            font-family: 'Consolas', monospace;
            font-size: 50px; font-weight: 900; line-height: 1.0;
            text-shadow: 0 0 10px rgba(255,255,255,0.3);
        }}
        .divider {{ width: 1px; height: 50px; background-color: #333; }}
        
        /* 하단 작은 버튼들 스타일 */
        .small-grid {{
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
        }}
        .small-btn {{
            background: #2b3648; padding: 10px; border-radius: 4px;
            text-align: center; font-size: 12px; color: #ccc;
        }}
        .btn-val {{ font-weight: bold; color: white; margin-bottom: 2px; }}
    </style>

    <div class="digital-monitor">
        <div class="score-box">
            <div class="monitor-label">낙상 위험도</div>
            <div class="digital-number" style="color: {fall_color};">{pt['score']}</div>
        </div>
        <div class="divider"></div>
        <div class="score-box">
            <div class="monitor-label">욕창 위험도</div>
            <div class="digital-number" style="color: {ulcer_color};">{braden_score}</div>
        </div>
    </div>
    
    <div class="small-grid">
        <div class="small-btn"><div class="btn-val">혈액형</div>A+</div>
        <div class="small-btn"><div class="btn-val">감염</div>-</div>
        <div class="small-btn"><div class="btn-val">식이</div>LD</div>
        <div class="small-btn"><div class="btn-val">격리</div>-</div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    # 오른쪽 패널 (기존 유지)
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
