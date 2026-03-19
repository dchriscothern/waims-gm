create extension if not exists pgcrypto;

create table if not exists public.gm_profiles (
  gm_id uuid primary key,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.gm_evaluations (
  id uuid primary key default gen_random_uuid(),
  gm_id uuid not null,
  team_id text,
  overall_score double precision not null,
  recommended_action text not null,
  created_at timestamptz not null default now(),
  player jsonb not null,
  ctx jsonb not null,
  components jsonb not null default '{}'::jsonb,
  assumptions jsonb not null default '{}'::jsonb,
  tension_points jsonb not null default '[]'::jsonb,
  summary_note text,
  strengths text,
  concerns text,
  mode text
);

create index if not exists gm_evaluations_gm_id_idx
  on public.gm_evaluations (gm_id);

create index if not exists gm_evaluations_created_at_idx
  on public.gm_evaluations (created_at desc);

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.gm_profiles to authenticated;
grant select, insert, update, delete on public.gm_evaluations to authenticated;

alter table public.gm_profiles enable row level security;
alter table public.gm_evaluations enable row level security;

drop policy if exists "gm_profiles_select_own" on public.gm_profiles;
drop policy if exists "gm_profiles_insert_own" on public.gm_profiles;
drop policy if exists "gm_profiles_update_own" on public.gm_profiles;

create policy "gm_profiles_select_own"
on public.gm_profiles
for select
to authenticated
using (auth.uid() = gm_id);

create policy "gm_profiles_insert_own"
on public.gm_profiles
for insert
to authenticated
with check (auth.uid() = gm_id);

create policy "gm_profiles_update_own"
on public.gm_profiles
for update
to authenticated
using (auth.uid() = gm_id)
with check (auth.uid() = gm_id);

drop policy if exists "gm_evaluations_select_own" on public.gm_evaluations;
drop policy if exists "gm_evaluations_insert_own" on public.gm_evaluations;
drop policy if exists "gm_evaluations_delete_own" on public.gm_evaluations;

create policy "gm_evaluations_select_own"
on public.gm_evaluations
for select
to authenticated
using (auth.uid() = gm_id);

create policy "gm_evaluations_insert_own"
on public.gm_evaluations
for insert
to authenticated
with check (auth.uid() = gm_id);

create policy "gm_evaluations_delete_own"
on public.gm_evaluations
for delete
to authenticated
using (auth.uid() = gm_id);
