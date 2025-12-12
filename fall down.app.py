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
