# 데일리 페이스 Streamlit

컨디션과 일정에 맞춰 오늘 가능한 습관 목표를 추천하는 반응형 MVP입니다.

## 로컬 실행

Python 3.11~3.13 환경에서 다음 명령을 실행합니다.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud 배포

1. 이 폴더를 GitHub 저장소에 푸시합니다.
2. Streamlit Community Cloud에서 `Create app`을 선택합니다.
3. 저장소와 브랜치를 선택하고 Main file path를 `app.py`로 지정합니다.
4. Python 버전은 3.12를 권장합니다.
5. 배포 후 생성된 URL에서 모바일과 PC 흐름을 확인합니다.

현재 MVP 데이터는 방문자의 Streamlit 세션 동안 유지됩니다. 실제 계정·다기기 동기화·장기 기록 운영에는 외부 데이터베이스와 인증 연동이 필요합니다. 비밀키는 `.streamlit/secrets.toml`에 두고 Git에 커밋하지 않습니다.

## 운영 점검

- Streamlit Cloud 로그에서 앱 재시작과 예외를 확인합니다.
- `requirements.txt` 버전은 검증 후에만 변경합니다.
- 주기적으로 모바일 체크인, 추천 4단계, 목표 수락과 완료 기록을 회귀 점검합니다.
- 민감한 컨디션·수면 기록을 로그에 출력하지 않습니다.
