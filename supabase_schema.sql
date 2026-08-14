create table if not exists public.user_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_state enable row level security;

create policy "Users can read their own state"
on public.user_state for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "Users can insert their own state"
on public.user_state for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "Users can update their own state"
on public.user_state for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create index if not exists idx_user_state_updated_at
on public.user_state(updated_at desc);

