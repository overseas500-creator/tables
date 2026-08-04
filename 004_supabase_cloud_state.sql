-- Secure cloud persistence for the static school timetable application.
-- Run this migration in the Supabase SQL Editor for the target project.

begin;

create table if not exists public.user_app_state (
    user_id uuid
        primary key
        references auth.users(id)
        on delete cascade,

    state jsonb not null,

    state_version integer not null default 7
        check (state_version between 1 and 100000),

    revision bigint not null default 1
        check (revision > 0),

    last_client_id uuid not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint user_app_state_must_be_object
        check (jsonb_typeof(state) = 'object'),

    constraint user_app_state_must_have_version
        check (
            state ? 'version'
            and jsonb_typeof(state -> 'version') = 'number'
        ),

    constraint user_app_state_size_limit
        check (octet_length(state::text) <= 10485760)
);

comment on table public.user_app_state is
    'One complete timetable application state document per authenticated user.';

alter table public.user_app_state
    enable row level security;

alter table public.user_app_state
    force row level security;

revoke all
on table public.user_app_state
from public, anon, authenticated;

grant usage on schema public to authenticated;

grant select
on table public.user_app_state
to authenticated;

drop policy if exists app_state_select_own
    on public.user_app_state;

create policy app_state_select_own
on public.user_app_state
for select
to authenticated
using ((select auth.uid()) = user_id);

create or replace function public.save_user_app_state(
    p_state jsonb,
    p_state_version integer,
    p_expected_revision bigint,
    p_client_id uuid
)
returns table (
    new_revision bigint,
    saved_at timestamptz
)
language plpgsql
security definer
set search_path = pg_catalog, public
as $function$
declare
    v_user_id uuid := auth.uid();
    v_saved_at timestamptz := clock_timestamp();
begin
    if v_user_id is null then
        raise exception 'authentication_required'
            using errcode = '42501';
    end if;

    if p_expected_revision = 0 then
        return query
        insert into public.user_app_state (
            user_id,
            state,
            state_version,
            revision,
            last_client_id,
            created_at,
            updated_at
        )
        values (
            v_user_id,
            p_state,
            p_state_version,
            1,
            p_client_id,
            v_saved_at,
            v_saved_at
        )
        on conflict (user_id) do nothing
        returning
            user_app_state.revision,
            user_app_state.updated_at;

        if found then
            return;
        end if;
    elsif p_expected_revision > 0 then
        return query
        update public.user_app_state
        set
            state = p_state,
            state_version = p_state_version,
            revision = user_app_state.revision + 1,
            last_client_id = p_client_id,
            updated_at = v_saved_at
        where
            user_app_state.user_id = v_user_id
            and user_app_state.revision = p_expected_revision
        returning
            user_app_state.revision,
            user_app_state.updated_at;

        if found then
            return;
        end if;
    end if;

    raise exception 'state_conflict'
        using errcode = '40001';
end;
$function$;

revoke all
on function public.save_user_app_state(jsonb, integer, bigint, uuid)
from public, anon;

grant execute
on function public.save_user_app_state(jsonb, integer, bigint, uuid)
to authenticated;

commit;

notify pgrst, 'reload schema';
