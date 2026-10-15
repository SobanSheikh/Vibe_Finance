begin;

alter table public.analysis_sessions
  add column if not exists result_snapshot jsonb;

comment on column public.analysis_sessions.result_snapshot is
  'Validated user-facing analysis response for restart-safe job retrieval.';

commit;
