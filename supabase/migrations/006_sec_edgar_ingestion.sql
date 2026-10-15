begin;

alter table public.companies
  add column if not exists sec_cik varchar(10);

create unique index if not exists uq_companies_sec_cik
  on public.companies(sec_cik)
  where sec_cik is not null;

update public.companies set sec_cik = '0001652044' where symbol = 'GOOGL';
update public.companies set sec_cik = '0000789019' where symbol = 'MSFT';
update public.companies set sec_cik = '0001045810' where symbol = 'NVDA';

alter table public.financial_documents
  add column if not exists source_provider varchar(40),
  add column if not exists external_id varchar(80);

create index if not exists ix_financial_documents_source_provider
  on public.financial_documents(source_provider);

create index if not exists ix_financial_documents_external_id
  on public.financial_documents(external_id);

create unique index if not exists uq_financial_documents_provider_external_id
  on public.financial_documents(source_provider, external_id)
  where source_provider is not null and external_id is not null;

update storage.buckets
set allowed_mime_types = array['application/pdf', 'text/html', 'application/xhtml+xml']
where id = 'financial-filings';

commit;
