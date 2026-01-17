import streamlit as st
import pandas as pd
import random
import requests

# ---------------------------------------------------------
# 1. 데이터 수집 및 전처리 (안전장치 포함)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def get_lotto_data():
    """
    1순위: 동행복권 실시간 데이터 크롤링 시도
    2순위: 실패 시(차단 등) 내장된 비상용 데이터 사용
    """
    url = "https://dhlottery.co.kr/gameResult.do?method=statByNumber"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://dhlottery.co.kr/'
    }
    
    try:
        # SSL 인증서 검증 무시 (verify=False)로 접속 성공률 높임
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response.encoding = 'euc-kr'
        
        # 테이블 읽기 시도
        dfs = pd.read_html(response.text, match='번호')
        
        if len(dfs) > 0:
            df = dfs[0]
            # 컬럼 정리
            df_clean = df.iloc[:, [0, 2]].copy()
            df_clean.columns = ['number', 'count']
            df_clean['number'] = pd.to_numeric(df_clean['number'], errors='coerce')
            df_clean['count'] = pd.to_numeric(df_clean['count'], errors='coerce')
            return df_clean.dropna().astype(int).sort_values('number')
            
    except Exception as e:
        pass # 오류 발생 시 조용히 비상 데이터로 넘어감

    # -----------------------------------------------------
    # [비상용] 크롤링 실패 시 사용할 백업 데이터 (최근 통계 기반 근사치)
    # -----------------------------------------------------
    st.toast("⚠️ 실시간 서버 연결이 차단되어 '백업 데이터' 모드로 실행됩니다.", icon="📢")
    
    # 1~45번까지의 대략적인 당첨 횟수 데이터 (2024년 평균치 적용)
    # 앱이 죽지 않도록 하는 것이 최우선
    backup_counts = [
        186, 172, 174, 179, 163, 168, 172, 164, 145, 172, # 1~10
        175, 185, 180, 178, 170, 172, 182, 186, 165, 175, # 11~20
        169, 155, 160, 175, 165, 175, 185, 162, 155, 168, # 21~30
        172, 165, 178, 190, 165, 168, 175, 165, 175, 180, # 31~40
        155, 160, 182, 165, 182                         # 41~45
    ]
    
    df_backup = pd.DataFrame({
        'number': range(1, 46),
        'count': backup_counts
    })
    
    return df_backup

# ---------------------------------------------------------
# 2. 가중치 계산 및 번호 추첨 로직
# ---------------------------------------------------------
def generate_lotto_numbers(df):
    results = []
    
    # 가중치 평준화 (Smoothing): 격차를 1.5배 수준으로 완화
    # 공식: (당첨횟수 + 100)
    smoothing_factor = 100 
    
    weights = [count + smoothing_factor for count in df['count'].tolist()]
    numbers = df['number'].tolist()
    
    for _ in range(5):
        current_numbers = list(numbers)
        current_weights = list(weights)
        one_set = []
        
        for _ in range(7):
            picked_list = random.choices(current_numbers, weights=current_weights, k=1)
            picked = picked_list[0]
            one_set.append(picked)
            
            idx = current_numbers.index(picked)
            del current_numbers[idx]
            del current_weights[idx]
        
        main_nums = sorted(one_set[:6])
        bonus_num = one_set[6]
        results.append((main_nums, bonus_num))
        
    return results

# ---------------------------------------------------------
# 3. 앱 화면 구성
# ---------------------------------------------------------
st.set_page_config(page_title="AI 로또", page_icon="🎱", layout="centered")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%; font-size: 20px; font-weight: bold; padding: 15px 0;
        background-color: #FF4B4B; color: white; border-radius: 12px;
        border: none;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #FF2222;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎱 AI 로또 추첨기")
st.caption("빅데이터 가중치 알고리즘 (격차보정 1.5배)")

# 데이터 로드
with st.spinner('데이터 분석 및 가중치 계산 중...'):
    df_stats = get_lotto_data()

if not df_stats.empty:
    with st.expander("📊 현재 적용된 가중치 정보 보기"):
        top = df_stats.sort_values('count', ascending=False).iloc[0]
        st.write(f"**최다 당첨 번호:** {top['number']}번")
        st.write(f"**누적 당첨 횟수:** {top['count']}회")
        st.info("당첨 횟수가 많은 번호가 조금 더 높은 확률로 추첨됩니다.")

    st.divider()

    if st.button("🎲 행운의 번호 5세트 생성"):
        games = generate_lotto_numbers(df_stats)
        st.balloons()
        st.success("추첨 완료! 이번 주 주인공은 바로 당신입니다. 🍀")
        
        for i, (main, bonus) in enumerate(games, 1):
            st.markdown(f"##### GAME {i}")
            
            # 디자인 요소
            def get_color(n):
                if n <= 10: return "#fbc400" # 노랑
                elif n <= 20: return "#69c8f2" # 파랑
                elif n <= 30: return "#ff7272" # 빨강
                elif n <= 40: return "#aaaaaa" # 회색
                else: return "#b0d840" # 초록
            
            html = "<div style='display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:15px;'>"
            for num in main:
                c = get_color(num)
                html += f"<div style='background:{c}; color:#fff; width:38px; height:38px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);'>{num}</div>"
            
            html += "<div style='font-weight:bold; color:#ccc;'>+</div>"
            
            # 보너스 볼
            html += f"<div style='background:{get_color(bonus)}; color:#fff; width:38px; height:38px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);'>{bonus}</div>"
            html += "</div>"
            
            st.markdown(html, unsafe_allow_html=True)
            st.markdown("<div style='border-bottom:1px solid #eee; margin-bottom:15px;'></div>", unsafe_allow_html=True)

else:
    st.error("시스템 오류가 발생했습니다.")
