begin;

create unique index if not exists uq_financial_documents_company_type_period
  on public.financial_documents (
    company_id,
    lower(trim(document_type)),
    lower(trim(coalesce(reporting_period, '')))
  );

commit;
