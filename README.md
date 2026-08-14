# 데일리 페이스 Streamlit

컨디션과 일정에 맞춰 오늘 가능한 습관 목표를 추천하는 반응형 MVP입니다.

## 운영 앱

[데일리 페이스 열기](https://habit-mentor-najae0075.streamlit.app/)

- 운영 브랜치: `main`
- 앱 진입점: `app.py`
- 배포 방식: Streamlit Community Cloud 자동 배포

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
- 배포 상태는 `python tests/check_deployment.py`로 확인할 수 있습니다.

## Supabase 연결

1. Supabase SQL Editor에서 `supabase_schema.sql`을 실행합니다.
2. Streamlit Cloud의 App settings → Secrets에 아래 값을 등록합니다.

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_YOUR_KEY"
```

배포 환경에 두 값이 있으면 이메일 로그인과 사용자별 기록 동기화가 활성화됩니다. 값이 없는 로컬 환경에서는 게스트 모드로 실행됩니다. Secret 또는 service role 키는 사용하지 않습니다.
