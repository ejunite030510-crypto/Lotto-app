import streamlit as st
import pandas as pd
import random
import requests

# ---------------------------------------------------------
# 1. 데이터 수집 및 전처리
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def get_lotto_data():
    """
    동행복권 공식 홈페이지에서 통계 데이터를 가져옵니다.
    """
    url = "https://dhlottery.co.kr/gameResult.do?method=statByNumber"
    
    # [핵심 수정] 봇 탐지를 피하기 위해 브라우저인 척 위장하는 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # requests를 사용하여 헤더와 함께 요청
        response = requests.get(url, headers=headers, timeout=10)
        
        # 한글 깨짐 방지 (동행복권 사이트는 euc-kr 인코딩을 사용함)
        response.encoding = 'euc-kr'
        
        # 받아온 HTML 문자열에서 테이블 추출
        dfs = pd.read_html(response.text)
        
        # 통계 표 찾기 (보통 첫 번째나 두 번째 테이블)
        # 테이블 구조가 맞는지 확인하며 찾기
        df = None
        for table in dfs:
            # '당첨횟수'라는 단어가 포함된 테이블을 찾음
            if '당첨횟수' in table.columns or '당첨횟수' in table.iloc[0].values.astype(str):
                df = table
                break
        
        if df is None:
            df = dfs[0] # 못 찾으면 첫 번째 거라도 가져옴

        # 데이터 정제 (번호, 당첨횟수 컬럼만 추출)
        # 사이트 구조: [번호, 그래프, 당첨횟수] 형태
        # iloc을 사용하여 안전하게 인덱스로 접근
        df_clean = df.iloc[:, [0, 2]].copy()
        df_clean.columns = ['number', 'count']
        
        # 데이터 타입 변환 (오류 방지)
        df_clean['number'] = pd.to_numeric(df_clean['number'], errors='coerce')
        df_clean['count'] = pd.to_numeric(df_clean['count'], errors='coerce')
        
        # 결측치 제거 (헤더 등이 포함됐을 경우 대비)
        df_clean = df_clean.dropna().astype(int)
        
        return df_clean.sort_values('number')
        
    except Exception as e:
        st.error(f"데이터 접속 오류: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. 가중치 계산 및 번호 추첨 로직
# ---------------------------------------------------------
def generate_lotto_numbers(df):
    results = []
    
    # 가중치 평준화 (Smoothing): 격차를 1.5배 수준으로 완화
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
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎱 AI 로또 추첨기")
st.caption("실시간 데이터 분석 + 가중치 알고리즘 적용")

with st.spinner('동행복권 서버에서 데이터를 가져오는 중...'):
    df_stats = get_lotto_data()

if not df_stats.empty:
    with st.expander("📊 데이터 분석 결과 확인"):
        top = df_stats.sort_values('count', ascending=False).iloc[0]
        st.write(f"현재까지 총 {len(df_stats)}개의 번호 데이터 분석 완료")
        st.write(f"최다 당첨 번호: **{top['number']}번** (총 {top['count']}회 출현)")

    st.divider()

    if st.button("🎲 번호 생성하기"):
        games = generate_lotto_numbers(df_stats)
        st.success("생성 완료! 행운을 빕니다. 🍀")
        
        for i, (main, bonus) in enumerate(games, 1):
            st.markdown(f"**GAME {i}**")
            
            # 공 그리기 로직
            def get_color(n):
                if n <= 10: return "#fbc400" # 노랑
                elif n <= 20: return "#69c8f2" # 파랑
                elif n <= 30: return "#ff7272" # 빨강
                elif n <= 40: return "#aaaaaa" # 회색
                else: return "#b0d840" # 초록
            
            html = "<div style='display:flex; align-items:center; gap:5px; flex-wrap:wrap;'>"
            for num in main:
                c = get_color(num)
                html += f"<div style='background:{c}; color:#fff; width:35px; height:35px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; text-shadow:1px 1px 2px rgba(0,0,0,0.3);'>{num}</div>"
            html += "<div style='font-weight:bold; margin:0 5px;'>+</div>"
            html += f"<div style='background:{get_color(bonus)}; color:#fff; width:35px; height:35px; border-radius:50%; display:flex; justify-content:center; align-items:center; font-weight:bold; text-shadow:1px 1px 2px rgba(0,0,0,0.3);'>{bonus}</div>"
            html += "</div>"
            
            st.markdown(html, unsafe_allow_html=True)
            st.markdown("---")
else:
    st.error("데이터 서버 접속이 차단되었습니다. 잠시 후 다시 시도해주세요.")
