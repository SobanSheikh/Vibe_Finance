begin;

alter table public.companies
  add column if not exists is_active boolean not null default true;

alter table public.companies
  alter column exchange set default 'NASDAQ';

update public.companies
set is_active = false
where symbol in ('RELIANCE', 'TCS', 'INFY', 'HDFCBANK');

insert into public.companies (id, symbol, name, sector, exchange, is_active) values
  ('7dcf2aa1-a22c-48e1-8435-91fc07472df1', 'GOOGL', 'Alphabet Inc.', 'Communication Services', 'NASDAQ', true),
  ('803dc31f-6d0c-42b9-b6aa-eb4e2c50d25e', 'MSFT', 'Microsoft Corporation', 'Information Technology', 'NASDAQ', true),
  ('b0b27ca1-75b0-4a40-b8f3-7d52958cff3d', 'NVDA', 'NVIDIA Corporation', 'Information Technology', 'NASDAQ', true)
on conflict (symbol) do update set
  name = excluded.name,
  sector = excluded.sector,
  exchange = excluded.exchange,
  is_active = true;

delete from public.holdings
where profile_id in (
  'a7e99bdf-9459-4806-ada5-a596cf4d453c',
  '9c3bfb92-8815-43f7-8316-851c7f8d8ae9',
  '16b24f78-e814-4e72-861e-81f4d241fc9d'
);

insert into public.holdings (profile_id, company_id, quantity, average_cost)
select values_to_insert.profile_id, companies.id, values_to_insert.quantity, values_to_insert.average_cost
from (values
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c'::uuid, 'MSFT', 8::numeric, 410.00::numeric),
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c'::uuid, 'NVDA', 5::numeric, 150.00::numeric),
  ('9c3bfb92-8815-43f7-8316-851c7f8d8ae9'::uuid, 'GOOGL', 4::numeric, 175.00::numeric),
  ('9c3bfb92-8815-43f7-8316-851c7f8d8ae9'::uuid, 'MSFT', 10::numeric, 410.00::numeric),
  ('9c3bfb92-8815-43f7-8316-851c7f8d8ae9'::uuid, 'NVDA', 3::numeric, 150.00::numeric),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d'::uuid, 'GOOGL', 15::numeric, 175.00::numeric),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d'::uuid, 'MSFT', 5::numeric, 410.00::numeric),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d'::uuid, 'NVDA', 4::numeric, 150.00::numeric)
) as values_to_insert(profile_id, symbol, quantity, average_cost)
join public.companies on companies.symbol = values_to_insert.symbol
on conflict (profile_id, company_id) do update set
  quantity = excluded.quantity,
  average_cost = excluded.average_cost;

delete from public.watchlist_items
where profile_id in (
  'a7e99bdf-9459-4806-ada5-a596cf4d453c',
  '9c3bfb92-8815-43f7-8316-851c7f8d8ae9',
  '16b24f78-e814-4e72-861e-81f4d241fc9d'
);

insert into public.watchlist_items (profile_id, company_id)
select values_to_insert.profile_id, companies.id
from (values
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c'::uuid, 'GOOGL'),
  ('9c3bfb92-8815-43f7-8316-851c7f8d8ae9'::uuid, 'NVDA'),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d'::uuid, 'MSFT')
) as values_to_insert(profile_id, symbol)
join public.companies on companies.symbol = values_to_insert.symbol
on conflict (profile_id, company_id) do nothing;

commit;
