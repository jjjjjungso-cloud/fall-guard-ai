# streamlit_emr_updated_v2.py
# - Confirm 버튼 리셋 문제 해결(링크/쿼리파라미터 제거)
# - Confirm 버튼을 알람박스 "아래"에 고정 배치(가려짐 방지)
# - Confirm 누른 간호사 / 시간 로그 저장 (session_state + 다운로드)

import streamlit as st
from datetime import datetime

st.set_page_config(page_title="EMR Fall Risk Monitor", layout="wide")

# -----------------------
# 0) Session State 초기화
# -----------------------
if "alarm_confirmed" not in st.session_state:
    st.session_state.alarm_confirmed = False

if "confirm_logs" not in st.session_state:
    # 각 원소: {"time": "...", "nurse": "...", "score": 85, "factors": ["...","..."]}
    st.session_state.confirm_logs = []

# (선택) 마지막 계산 스냅샷
if "last_fall_score" not in st.session_state:
    st.session_state.last_fall_score = None
if "last_detected_factors" not in st.session_state:
    st.session_state.last_detected_factors = []

# -----------------------
# 1) 스타일 (알람 박스 + Confirm 버튼)
# -----------------------
st.markdown("""
<style>
/* 알람 박스 */
.custom-alert-box{
    background: rgba(128, 0, 0, 0.22);
    border: 1px solid rgba(255, 80, 80, 0.55);
    border-left: 6px solid rgba(255, 80, 80, 0.9);
    border-radius: 12px;
    padding: 18px 18px 16px 18px;
    margin-top: 10px;
    margin-bottom: 6px;
}
.alert-title{
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 8px;
}
.alert-content{
    font-size: 16px;
    line-height: 1.6;
    margin-bottom: 14px;
}
.alert-factors{
    background: rgba(0,0,0,0.22);
    border: 1px solid rgba(255, 80, 80, 0.35);
    border-radius: 10px;
    padding: 12px 12px;
}

/* ✅ Confirm 버튼 스타일 (페이지의 모든 st.button에 적용됨)
   - 만약 다른 버튼까지 빨개지는 게 싫으면, 아래 "Confirm만 적용" 버전으로 바꿔드릴게요.
*/
div.stButton > button {
    background-color: #c0392b !important;
    color: #ffffff !important;
    font-size: 18px !important;
    font-weight: 800 !important;
    border-radius: 10px !important;
    padding: 0.75em 1em !important;
    border: none !important;
}
div.stButton > button:hover {
    filter: brightness(0.95);
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# 2) 사이드바: 간호사 정보 + 시뮬레이션 입력(예시)
# -----------------------
with st.sidebar:
    st.header("사용자")
    nurse_name = st.text_input("Confirm 누를 간호사", value=st.session_state.get("nurse_name", ""))
    st.session_state["nurse_name"] = nurse_name

    st.divider()
    st.header("시뮬레이션 입력(예시)")

    # 아래 값들은 '예시'입니다. 실제 앱에서는 사용자 입력/EMR 데이터로 대체하세요.
    sim_age = st.number_input("나이", min_value=0, max_value=120, value=st.session_state.get("sim_age", 78), step=1)
    sim_sbp = st.number_input("수축기혈압(SBP)", min_value=30, max_value=250, value=st.session_state.get("sim_sbp", 88), step=1)
    sim_alb = st.number_input("알부민(g/dL)", min_value=0.0, max_value=6.0, value=st.session_state.get("sim_alb", 2.8), step=0.1)

    high_risk_drug = st.checkbox("고위험 약물", value=st.session_state.get("high_risk_drug", True))
    st.session_state.update({
        "sim_age": sim_age,
        "sim_sbp": sim_sbp,
        "sim_alb": sim_alb,
        "high_risk_drug": high_risk_drug
    })

# -----------------------
# 3) 낙상 점수/위험요인 산출(예시 로직)
# -----------------------
def compute_fall_risk(age: int, sbp: int, alb: float, high_risk_drug: bool):
    score = 0
    factors = []

    # 고령
    if age >= 75:
        score += 25
        factors.append("고령")

    # 저혈압
    if sbp <= 90:
        score += 25
        factors.append("저혈압")

    # 알부민 저하
    if alb < 3.0:
        score += 20
        factors.append("알부민 저하")

    # 고위험 약물
    if high_risk_drug:
        score += 15
        factors.append("고위험 약물")

    # (가산/보정) 예시
    if age >= 85:
        score += 5

    return score, factors

fall_score, detected_factors = compute_fall_risk(
    st.session_state["sim_age"],
    st.session_state["sim_sbp"],
    st.session_state["sim_alb"],
    st.session_state["high_risk_drug"],
)

# 스냅샷 저장(확인 로그에도 사용)
st.session_state.last_fall_score = fall_score
st.session_state.last_detected_factors = detected_factors

# -----------------------
# 4) Confirm 처리 함수 + 로그 저장
# -----------------------
def confirm_alarm():
    # 확인 상태 저장
    st.session_state.alarm_confirmed = True

    # 간호사명 없으면 "미입력"으로 저장 (원하면 Confirm 전에 입력 강제도 가능)
    nurse = (st.session_state.get("nurse_name") or "").strip()
    if not nurse:
        nurse = "미입력"

    log_item = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nurse": nurse,
        "score": int(st.session_state.get("last_fall_score") or 0),
        "factors": list(st.session_state.get("last_detected_factors") or []),
    }
    st.session_state.confirm_logs.append(log_item)

# -----------------------
# 5) 메인 UI
# -----------------------
st.title("낙상 위험 모니터 (데모)")

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("감지된 위험 요인")
    for f in (detected_factors or []):
        st.markdown(f"- **{f}**")

    st.write("")
    st.metric("낙상 위험 점수", fall_score)

with right:
    # ✅ 알람 표시 조건: score >= 60 이고 아직 확인 전
    if fall_score >= 60 and not st.session_state.alarm_confirmed:
        factors_str = "<br>• ".join(detected_factors) if detected_factors else "복합적 요인"

        st.markdown(f"""
        <div class="custom-alert-box">
            <div class="alert-title">🚨 낙상 고위험 감지! ({fall_score}점)</div>
            <div class="alert-content">
                환자의 상태 변화로 인해 낙상 위험도가 급격히 상승했습니다. 즉시 확인이 필요합니다.
            </div>
            <div class="alert-factors">
                <b>[감지된 주요 위험 요인]</b><br>
                • {factors_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ✅ (방법 2) 알람 박스 "아래"에 Confirm 버튼 배치 + 여백 보정
        st.markdown("<div style='margin-top: -2px;'></div>", unsafe_allow_html=True)

        if st.button("확인 (Confirm)", key="confirm_alarm_btn", use_container_width=True):
            confirm_alarm()
            st.rerun()

    elif fall_score >= 60 and st.session_state.alarm_confirmed:
        st.success("✅ 알람 확인 완료")
        st.caption("확인 로그가 저장되었습니다.")

    else:
        # 점수가 낮아지면 재알림 허용(원치 않으면 이 블록을 제거하세요)
        st.session_state.alarm_confirmed = False
        st.info("현재는 고위험 알람 조건이 아닙니다.")

# -----------------------
# 6) Confirm 로그 표시/다운로드
# -----------------------
st.divider()
st.subheader("Confirm 로그")

if st.session_state.confirm_logs:
    # 표로 보기
    rows = []
    for item in st.session_state.confirm_logs:
        rows.append({
            "시간": item["time"],
            "간호사": item["nurse"],
            "점수": item["score"],
            "위험요인": ", ".join(item["factors"]) if item["factors"] else "",
        })
    st.dataframe(rows, use_container_width=True)

    # CSV 다운로드
    import pandas as pd
    df = pd.DataFrame(rows)
    st.download_button(
        label="로그 CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="confirm_logs.csv",
        mime="text/csv",
        use_container_width=False
    )

    # 로그 초기화(원하면)
    if st.button("로그 초기화", key="clear_logs_btn"):
        st.session_state.confirm_logs = []
        st.rerun()
else:
    st.caption("아직 Confirm 로그가 없습니다.")
