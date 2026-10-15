begin;

alter table public.financial_documents
  alter column source_url drop not null,
  add column storage_path text unique,
  add column file_name varchar(255),
  add column file_size_bytes bigint check (file_size_bytes is null or file_size_bytes > 0),
  add column mime_type varchar(100),
  add column processing_status varchar(12),
  add column error_message text,
  add column page_count integer check (page_count is null or page_count >= 0),
  add column chunk_count integer check (chunk_count is null or chunk_count >= 0);

update public.financial_documents
set processing_status = 'completed';

alter table public.financial_documents
  alter column processing_status set default 'pending',
  alter column processing_status set not null,
  add constraint financial_documents_processing_status_check
    check (processing_status in ('pending', 'processing', 'completed', 'failed'));

create index ix_financial_documents_company_status
  on public.financial_documents(company_id, processing_status);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'financial-filings',
  'financial-filings',
  false,
  26214400,
  array['application/pdf']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

commit;
