# 운영 지표 관리자 설정

1. Supabase SQL Editor에서 최신 `supabase_schema.sql` 전체를 실행합니다.
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
