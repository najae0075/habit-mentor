create table if not exists public.user_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_state enable row level security;

drop policy if exists "Users can read their own state" on public.user_state;
create policy "Users can read their own state"
on public.user_state for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can insert their own state" on public.user_state;
create policy "Users can insert their own state"
on public.user_state for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own state" on public.user_state;
create policy "Users can update their own state"
on public.user_state for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create index if not exists idx_user_state_updated_at
on public.user_state(updated_at desc);

create table if not exists public.analytics_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  event_name text not null,
  event_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint analytics_events_metadata_object check (jsonb_typeof(metadata) = 'object'),
  constraint analytics_events_user_event_key unique (user_id, event_key)
);

alter table public.analytics_events enable row level security;

drop policy if exists "Users can insert their own analytics events" on public.analytics_events;
create policy "Users can insert their own analytics events"
on public.analytics_events for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can read their own analytics events" on public.analytics_events;
create policy "Users can read their own analytics events"
on public.analytics_events for select
to authenticated
using ((select auth.uid()) = user_id);

create index if not exists idx_analytics_events_name_created_at
on public.analytics_events(event_name, created_at desc);

create index if not exists idx_analytics_events_user_created_at
on public.analytics_events(user_id, created_at desc);

create table if not exists public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.admin_users enable row level security;

drop function if exists public.admin_analytics_dashboard();
drop function if exists public.admin_analytics_dashboard(integer);
create function public.admin_analytics_dashboard(p_days integer default 7)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  result jsonb;
begin
  if auth.uid() is null or not exists (
    select 1 from public.admin_users where user_id = auth.uid()
  ) then
    raise exception 'administrator access required' using errcode = '42501';
  end if;
  if p_days not in (1, 7, 30) then
    raise exception 'period must be 1, 7, or 30 days' using errcode = '22023';
  end if;

  with event_days as (
    select
      user_id,
      event_name,
      metadata,
      created_at,
      (created_at at time zone 'Asia/Seoul')::date as day
    from public.analytics_events
  ),
  today_counts as (
    select
      count(distinct user_id) filter (where event_name = 'daily_active') as active_users,
      count(distinct user_id) filter (where event_name = 'checkin_started') as checkin_started_users,
      count(distinct user_id) filter (where event_name = 'checkin_completed') as checkin_completed_users,
      count(distinct user_id) filter (where event_name = 'recommendation_accepted') as recommendation_users,
      count(*) filter (where event_name = 'recommendation_accepted') as recommendations_accepted,
      count(*) filter (
        where event_name = 'recommendation_accepted'
          and metadata->>'modified' = 'true'
      ) as recommendations_modified,
      count(*) filter (where event_name = 'habit_completed') as habits_completed,
      count(*) filter (where event_name = 'reminder_shown') as reminders_shown,
      count(*) filter (where event_name = 'reminder_acknowledged') as reminders_acknowledged
    from event_days
    where day between (now() at time zone 'Asia/Seoul')::date - (p_days - 1)
      and (now() at time zone 'Asia/Seoul')::date
  ),
  yesterday_counts as (
    select count(distinct user_id) filter (where event_name = 'checkin_completed') as checked_in_users
    from event_days
    where day = (now() at time zone 'Asia/Seoul')::date - 1
  ),
  next_day_counts as (
    select count(distinct user_id) as returned_users
    from event_days
    where day = (now() at time zone 'Asia/Seoul')::date
      and event_name = 'user_returned'
      and metadata->>'days_since_last_checkin' = '1'
  ),
  recommendation_conversion as (
    select count(distinct accepted.user_id) as completed_users
    from event_days accepted
    where accepted.event_name = 'recommendation_accepted'
      and accepted.day between (now() at time zone 'Asia/Seoul')::date - (p_days - 1)
        and (now() at time zone 'Asia/Seoul')::date
      and exists (
        select 1 from event_days completed
        where completed.user_id = accepted.user_id
          and completed.event_name = 'habit_completed'
          and completed.metadata->>'habit_key' = accepted.metadata->>'habit_key'
          and completed.created_at >= accepted.created_at
          and completed.day <= (now() at time zone 'Asia/Seoul')::date
      )
  ),
  retention as (
    select
      count(*) filter (
        where (u.created_at at time zone 'Asia/Seoul')::date
          <= (now() at time zone 'Asia/Seoul')::date - 7
      ) as eligible_7,
      count(*) filter (
        where (u.created_at at time zone 'Asia/Seoul')::date
          <= (now() at time zone 'Asia/Seoul')::date - 7
          and exists (
            select 1 from event_days e
            where e.user_id = u.id and e.event_name = 'daily_active'
              and e.day = (u.created_at at time zone 'Asia/Seoul')::date + 7
          )
      ) as retained_7,
      count(*) filter (
        where (u.created_at at time zone 'Asia/Seoul')::date
          <= (now() at time zone 'Asia/Seoul')::date - 30
      ) as eligible_30,
      count(*) filter (
        where (u.created_at at time zone 'Asia/Seoul')::date
          <= (now() at time zone 'Asia/Seoul')::date - 30
          and exists (
            select 1 from event_days e
            where e.user_id = u.id and e.event_name = 'daily_active'
              and e.day = (u.created_at at time zone 'Asia/Seoul')::date + 30
          )
      ) as retained_30
    from auth.users u
  )
  select jsonb_build_object(
    'registered_users', (select count(*) from auth.users),
    'active_users', t.active_users,
    'checkin_started_users', t.checkin_started_users,
    'checkin_completed_users', t.checkin_completed_users,
    'checkin_rate', round(100.0 * t.checkin_completed_users / nullif(t.active_users, 0), 1),
    'checkin_completion_rate', round(100.0 * t.checkin_completed_users / nullif(t.checkin_started_users, 0), 1),
    'recommendation_completion_rate', round(100.0 * c.completed_users / nullif(t.recommendation_users, 0), 1),
    'recommendations_accepted', t.recommendations_accepted,
    'recommendations_modified', t.recommendations_modified,
    'habits_completed', t.habits_completed,
    'reminders_shown', t.reminders_shown,
    'reminders_acknowledged', t.reminders_acknowledged,
    'next_day_returns', n.returned_users,
    'next_day_return_rate', round(100.0 * n.returned_users / nullif(y.checked_in_users, 0), 1),
    'retention_7', round(100.0 * r.retained_7 / nullif(r.eligible_7, 0), 1),
    'retention_30', round(100.0 * r.retained_30 / nullif(r.eligible_30, 0), 1),
    'daily', (
      select coalesce(jsonb_agg(row_data order by day), '[]'::jsonb)
      from (
        select
          day,
          jsonb_build_object(
            'day', day,
            'active_users', count(distinct user_id) filter (where event_name = 'daily_active'),
            'checked_in_users', count(distinct user_id) filter (where event_name = 'checkin_completed')
          ) as row_data
        from event_days
        where day >= (now() at time zone 'Asia/Seoul')::date - (p_days - 1)
        group by day
      ) recent
    )
  ) into result
  from today_counts t
  cross join yesterday_counts y
  cross join next_day_counts n
  cross join recommendation_conversion c
  cross join retention r;

  return result;
end;
$$;

revoke all on function public.admin_analytics_dashboard(integer) from public;
grant execute on function public.admin_analytics_dashboard(integer) to authenticated;

-- 관리자 등록 예시(사용자 UUID로 교체 후 SQL Editor에서 한 번 실행):
-- insert into public.admin_users(user_id) values ('YOUR_AUTH_USER_UUID') on conflict do nothing;

