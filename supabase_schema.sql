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

