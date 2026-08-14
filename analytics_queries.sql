-- Supabase SQL Editor에서 운영자가 실행하는 핵심 지표 쿼리입니다.
-- 모든 날짜는 한국 시간(Asia/Seoul)을 기준으로 집계합니다.

-- 최근 30일: 일일 활성 사용자와 체크인율
with daily as (
  select
    (created_at at time zone 'Asia/Seoul')::date as day,
    count(distinct user_id) filter (where event_name = 'daily_active') as active_users,
    count(distinct user_id) filter (where event_name = 'checkin_completed') as checked_in_users
  from public.analytics_events
  where created_at >= now() - interval '30 days'
  group by 1
)
select
  day,
  active_users,
  checked_in_users,
  round(100.0 * checked_in_users / nullif(active_users, 0), 1) as checkin_rate_percent
from daily
order by day desc;

-- 최근 30일: 핵심 행동 퍼널
select
  event_name,
  count(*) as event_count,
  count(distinct user_id) as unique_users
from public.analytics_events
where created_at >= now() - interval '30 days'
  and event_name in (
    'checkin_started',
    'checkin_completed',
    'recommendation_accepted',
    'habit_completed',
    'goal_reduced',
    'rest_selected',
    'user_returned'
  )
group by event_name
order by event_count desc;

-- 최근 30일: 추천 수정 비율
select
  count(*) as accepted_count,
  count(*) filter (where (metadata->>'modified')::boolean) as modified_count,
  round(
    100.0 * count(*) filter (where (metadata->>'modified')::boolean) / nullif(count(*), 0),
    1
  ) as modified_rate_percent
from public.analytics_events
where event_name = 'recommendation_accepted'
  and created_at >= now() - interval '30 days';
