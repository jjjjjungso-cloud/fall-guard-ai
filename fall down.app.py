import streamlit as st
import pandas as pd
import time

# --------------------------------------------------------------------------------
# [설정] 페이지 및 다크모드 스타일
# --------------------------------------------------------------------------------
st.set_page_config(page_title="Fall-Guard AI", layout="wide")

st.markdown("""
<style>
    /* 전체 배경: EMR 다크모드 색상 */
    .stApp { background-color: #1e2b3e; color: white; }
    
    /* 왼쪽 패널 디자인 */
    .risk-panel {
        background-color: #263859; padding: 20px; border-radius: 10px;
        text-align: center; margin-bottom: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.5); /* 그림자 효과 */
    }
    
    /* 점수 폰트 (네온 효과) */
    .big-score { 
        font-size: 80px !important; font-weight: 900; line-height: 1.0; margin: 15px 0; 
        text-shadow: 0 0 15px rgba(255,255,255,0.2); 
    }
    
    /* 텍스트 색상 강제 지정 (다크모드용) */
    h1, h2, h3, h4, p, div, span, label { color: #e0e0e0 !important; }
    .stCheckbox label { font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# [데이터] 시뮬레이션용 환자 케이스
# --------------------------------------------------------------------------------
patient_db = {
    'CASE 1: 김수면 (약물 고위험)': {
        'score': 92, 'level': 'High', 'factors': ['수면제 복용', '고령(78세)', '야간 빈뇨'], 
        'mental': 'Alert', 'mobility': 'Independent'
    },
    'CASE 2: 이보행 (신체 고위험)': {
        'score': 72, 'level': 'High', 'factors': ['편마비', '낙상 과거력', '보행 장애'], 
        'mental': 'Alert', 'mobility': 'Needs Assist'
    },
    'CASE 3: 박섬망 (인지 고위험)': {
        'score': 88, 'level': 'High', 'factors': ['섬망 증세', '수액 라인 유지'], 
        'mental': 'Confusion', 'mobility': 'Restless'
    },
    'CASE 4: 최안전 (저위험)': {
        'score': 15, 'level': 'Low', 'factors': [], 
        'mental': 'Alert', 'mobility': 'Independent'
    }
}

# --------------------------------------------------------------------------------
# [로직] 처방적 분석 (규칙 기반 간호 중재 생성)
# --------------------------------------------------------------------------------
def get_interventions(data):
    tasks = []
    # 1. 공통 규칙
    if data['score'] >= 60:
        tasks.append("📌 [공통] 낙상 고위험 표지판 침상 부착")
        tasks.append("📌 [공통] 침상 난간(Side Rail) 2개 이상 올림")
    
    # 2. 약물 규칙
    if any("수면제" in f for f in data['factors']):
        tasks.append("💊 [약물] 투약 직후 30분간 침상 안정(ABR) 및 관찰")
    
    # 3. 인지/신체 규칙
    if data['mental'] == 'Confusion' or "섬망" in str(data['factors']):
        tasks.append("🌙 [안전] 침상 주변 야간 조명(Night Light) 점등")
        tasks.append("👀 [감시] 간호스테이션 인접 병실 배정 (가상)")
        
    if "보행 장애" in str(data['factors']) or data['mobility'] == 'Needs Assist':
        tasks.append("🤝 [이동] 화장실 이동 시 보조인력 동반 필수")
        
    return tasks

# --------------------------------------------------------------------------------
# [화면] UI 구성 (왼쪽: AI 패널 / 오른쪽: 상세 내용)
# --------------------------------------------------------------------------------
col_ai, col_context = st.columns([1, 2.8])

# 1. 왼쪽 AI 패널
with col_ai:
    st.markdown("#### 🛡️ Fall-Guard AI")
    selected_pt = st.selectbox("환자 선택 (시뮬레이션)", list(patient_db.keys()))
    pt_data = patient_db[selected_pt]
    
    # 위험도에 따른 색상 설정
    if pt_data['score'] >= 70:
        color = "#ff4444" # Red
        status = "🚨 고위험"
        border = f"3px solid {color}"
    elif pt_data['score'] >= 40:
        color = "#ffbb33" # Orange
        status = "⚠️ 중위험"
        border = f"3px solid {color}"
    else:
        color = "#00C851" # Green
        status = "🟢 안전"
        border = "1px solid gray"

    # 점수 표시 카드
    st.markdown(f"""
    <div class="risk-panel" style="border: {border};">
        <div style="color:{color}; font-size:24px; font-weight:bold;">{status}</div>
        <div class="big-score" style="color:{color};">{pt_data['score']}</div>
        <div style="font-size:14px; color:#aaa;">24시간 내 낙상 예측 확률(%)</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 위험 요인 태그
    st.markdown("**🚩 주요 위험 요인**")
    if pt_data['factors']:
        for f in pt_data['factors']:
            st.markdown(f"<div style='background:rgba(255,255,255,0.1); padding:5px; margin-bottom:5px; border-radius:5px; color:{color};'>• {f}</div>", unsafe_allow_html=True)
    else:
        st.info("특이 소견 없음")

# 2. 오른쪽 컨텍스트 패널 (처방적 분석 결과)
with col_context:
    st.markdown(f"### 📋 {selected_pt.split(':')[1]} 환자 맞춤형 중재")
    st.info("💡 AI가 위험 요인을 분석하여 **즉시 수행해야 할 간호 활동**을 생성했습니다.")
    
    # 로직에 따른 할 일 목록 가져오기
    todos = get_interventions(pt_data)
    
    if todos:
        with st.container(border=True):
            st.markdown("#### ✅ 필수 간호 중재 (To-Do)")
            
            # 진행률 바 (재미 요소)
            progress_text = "중재 이행률"
            my_bar = st.progress(0, text=progress_text)
            
            checked_count = 0
            for i, task in enumerate(todos):
                if st.checkbox(task, key=f"task_{i}"):
                    checked_count += 1
            
            # 체크할 때마다 진행률 업데이트
            if len(todos) > 0:
                my_bar.progress(checked_count / len(todos), text=f"이행률: {int(checked_count / len(todos) * 100)}%")

            st.markdown("---")
            if st.button("간호기록 저장 (EMR 전송)", type="primary", use_container_width=True):
                with st.spinner("서버 전송 중..."):
                    time.sleep(1.5)
                st.success("✅ 간호기록이 성공적으로 저장되었습니다!")
                st.balloons() # 성공 축하 효과
    else:
        st.success("현재 특별한 추가 중재가 필요하지 않습니다. 정규 라운딩을 지속하세요.")
        
    # (데모용) EMR 느낌 내기 위한 이미지 영역
    st.markdown("---")
    st.caption("👇 [참고] 기존 EMR 간호정보조사지 연동 화면")
    st.image("https://via.placeholder.com/800x200/15202b/ffffff?text=Electronic+Medical+Record+(Vital+Signs,+History)", use_column_width=True)