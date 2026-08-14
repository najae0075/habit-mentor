# 운영 지표 관리자 설정

1. 신규 설치는 Supabase SQL Editor에서 최신 `supabase_schema.sql` 전체를 실행합니다.
   기존 운영 앱에서 “이전 집계 함수” 안내가 나타나면
   `supabase_migrations/20260815_upgrade_admin_analytics.sql` 전체만 실행해도 됩니다.
2. Supabase Authentication > Users에서 관리자 계정의 UUID를 확인합니다.
3. SQL Editor에서 아래 쿼리를 실행합니다.

```sql
insert into public.admin_users(user_id)
values ('관리자-사용자-UUID')
on conflict do nothing;
```

4. Streamlit Community Cloud의 App settings > Secrets에 같은 UUID를 등록합니다.

```toml
ADMIN_USER_IDS = "관리자-사용자-UUID"
```

여러 관리자는 UUID를 쉼표로 구분합니다.

```toml
ADMIN_USER_IDS = "첫번째-UUID,두번째-UUID"
```

화면 노출 여부는 Streamlit Secret으로 결정하지만, 집계 함수 실행 권한은 Supabase의 `admin_users` 테이블로 다시 검증합니다. 일반 사용자는 원시 이벤트와 전체 집계를 조회할 수 없습니다.

마이그레이션은 기존 이벤트와 관리자 목록을 삭제하지 않습니다. 이전 RPC 정의만 기간 인자 버전으로 교체하고 PostgREST 스키마 캐시를 갱신합니다.
