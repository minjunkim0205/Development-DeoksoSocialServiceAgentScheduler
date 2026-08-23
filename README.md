# 덕소 사회복무요원 근무표 생성기

Streamlit과 OR-Tools로 사회복무요원 월간 근무표를 생성하고 수정하는 앱입니다.

## 설치

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```cmd
streamlit run app.py
```

## 주요 규칙

- 금/토/일 야간은 반드시 2명 배치
- 평일 야간은 2명 우선, 불가하면 1명 허용
- 주간은 기본 2명, 금/토/일은 최대 3명 허용
- 야간 다음날 비번 강제, 비번 다음날 휴무 우선
- 숙련 순번 기준 선임끼리 야간 동시 배치 금지
- 훈련소 미수료 또는 요원교육 미수료자끼리 야간 동시 배치 금지

세부 값은 앱의 `설정` 화면에서 조정할 수 있습니다.
