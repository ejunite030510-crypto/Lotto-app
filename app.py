import streamlit as st
import pandas as pd
import random
import requests

# ---------------------------------------------------------
# 1. 데이터 수집 및 전처리 (엑셀 로직 대체)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)  # 1시간마다 데이터 갱신
def get_lotto_data():
    # 동행복권 공식 홈페이지의 '번호별 통계' 페이지 크롤링
    url = "https://dhlottery.co.kr/gameResult.do?method=statByNumber"
    
    try:
        # html 내의 테이블을 pandas로 한 번에 읽어옵니다.
        dfs = pd.read_html(url)
        df = dfs[0] # 첫 번째 테이블이 통계 데이터
        
        # 데이터 정제 (불필요한 헤더 제거 및 숫자형 변환)
        # 보통 컬럼이 [번호, 그래프, 당첨횟수] 등으로 구성됨
        # 정확한 컬럼 처리를 위해 필요한 데이터만 추출
        
        # 동행복권 테이블 구조에 맞춰 데이터 정리
        # 번호와 당첨횟수만 필요함
        # 웹사이트 구조에 따라 컬럼명이 다를 수 있으므로 인덱스로 처리하는 것이 안전할 수 있으나,
        # 여기서는 일반적인 구조를 가정하고 처리합니다.
        
        # 데이터프레임 구조 확인 후 필요한 컬럼만 남김 (번호, 당첨횟수)
        # 2024년 기준 웹사이트 구조 반영 로직
        df_clean = df.iloc[:, [0, 2]].copy() # 0번열: 번호, 2번열: 횟수
        df_clean.columns = ['number', 'count']
        
        # 데이터 타입 변환 (문자열 -> 정수)
        df_clean['number'] = df_clean['number'].astype(int)
        df_clean['count'] = df_clean['count'].astype(int)
        
        return df_clean.sort_values('number')
        
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. 가중치 계산 및 번호 추첨 로직
# ---------------------------------------------------------
def generate_lotto_numbers(df):
    results = []
    
    # 가중치 설정: 사용자의 요청대로 '빈도'를 가중치로 사용
    # 예: 1번이 200번 나왔으면 가중치 200, 45번이 100번 나왔으면 가중치 100
    # 이렇게 하면 많이 나온 번호가 뽑힐 확률이 수학적으로 비례하여 높아짐 (요청하신 1.01%, 0.99% 로직과 일치)
    weights = df['count'].tolist()
    numbers = df['number'].tolist()
    
    for _ in range(5): # 5세트 생성
        # 가중치를 적용하여 비복원 추출 (한 세트 내 중복 불가)
        # random.choices는 복원 추출이므로, 한 번 뽑고 리스트에서 제거하는 방식 사용
        
        current_numbers = list(numbers)
        current_weights = list(weights)
        
        one_set = []
        
        # 7개 뽑기 (6개 번호 + 1개 보너스)
        for _ in range(7):
            picked_list = random.choices(current_numbers, weights=current_weights, k=1)
            picked = picked_list[0]
            
            one_set.append(picked)
            
            # 뽑힌 번호의 인덱스 찾기
            idx = current_numbers.index(picked)
            
            # 뽑힌 번호와 해당 가중치를 리스트에서 제거 (중복 방지)
            del current_numbers[idx]
            del current_weights[idx]
        
        # 정렬: 앞의 6개는 오름차순 정렬, 마지막 1개(보너스)는 그대로 둠
        main_nums = sorted(one_set[:6])
        bonus_num = one_set[6]
        
        results.append((main_nums, bonus_num))
        
    return results

# ---------------------------------------------------------
# 3. 앱 화면 구성 (UI)
# ---------------------------------------------------------
st.set_page_config(page_title="AI 로또 추첨기", page_icon="🎱")

st.title("🎱 스마트 로또 생성기")
st.caption("과거 모든 데이터를 분석하여 가중치를 적용합니다.")

# 데이터 로드
with st.spinner('동행복권 서버에서 최신 데이터를 가져오는 중...'):
    df_stats = get_lotto_data()

if not df_stats.empty:
    # 간단한 통계 보여주기 (옵션)
    with st.expander("📊 현재 번호별 가중치 보기"):
        st.dataframe(df_stats.set_index('number').T)
        top_num = df_stats.sort_values('count', ascending=False).iloc[0]
        st.info(f"현재 역대 최다 당첨 번호: {top_num['number']}번 ({top_num['count']}회)")

    st.divider()

    # 추첨 버튼
    if st.button("🎲 5게임 무료 추천 받기", type="primary", use_container_width=True):
        games = generate_lotto_numbers(df_stats)
        
        st.success("생성 완료! 행운을 빕니다. 🍀")
        
        for i, (main, bonus) in enumerate(games, 1):
            st.markdown(f"### GAME {i}")
            
            # 번호 시각화 (동그라미 스타일)
            cols = st.columns(8) # 6개 + 화살표 + 1개
            
            # 메인 번호 6개 출력
            for idx, num in enumerate(main):
                # 색상 결정 로직 (로또 공 색상)
                color = "#fbc400" # 노랑 (1-10)
                if 11 <= num <= 20: color = "#69c8f2" # 파랑
                elif 21 <= num <= 30: color = "#ff7272" # 빨강
                elif 31 <= num <= 40: color = "#aaaaaa" # 회색
                elif 41 <= num: color = "#b0d840" # 초록
                
                cols[idx].markdown(
                    f"""<div style='background-color:{color}; 
                        color:white; border-radius:50%; 
                        width:35px; height:35px; 
                        text-align:center; line-height:35px; 
                        font-weight:bold; margin:0 auto;'>{num}</div>""", 
                    unsafe_allow_html=True
                )
            
            # + 기호
            cols[6].markdown("<div style='text-align:center; line-height:35px; font-weight:bold;'>+</div>", unsafe_allow_html=True)
            
            # 보너스 번호 출력
            b_color = "#fbc400"
            if 11 <= bonus <= 20: b_color = "#69c8f2"
            elif 21 <= bonus <= 30: b_color = "#ff7272"
            elif 31 <= bonus <= 40: b_color = "#aaaaaa"
            elif 41 <= bonus: b_color = "#b0d840"
            
            cols[7].markdown(
                 f"""<div style='background-color:{b_color}; 
                    color:white; border-radius:50%; 
                    width:35px; height:35px; 
                    text-align:center; line-height:35px; 
                    font-weight:bold; margin:0 auto;'>{bonus}</div>""", 
                unsafe_allow_html=True
            )
            st.write("") # 간격
            
else:
    st.error("데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")