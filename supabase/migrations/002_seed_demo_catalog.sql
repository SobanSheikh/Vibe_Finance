begin;

insert into public.companies (id, symbol, name, sector, exchange) values
  ('ebce53d4-8628-4df2-8aa9-b5f1ddbd94f8', 'RELIANCE', 'Reliance Industries', 'Energy', 'NSE'),
  ('2adf8b37-913a-4677-a412-20e617637f41', 'TCS', 'Tata Consultancy Services', 'Information Technology', 'NSE'),
  ('14968b6f-456f-4b6a-a455-73b17fe246ff', 'INFY', 'Infosys', 'Information Technology', 'NSE'),
  ('43ba499f-23cc-4692-b214-1f10d233b84c', 'HDFCBANK', 'HDFC Bank', 'Financial Services', 'NSE')
on conflict (symbol) do update set
  name = excluded.name,
  sector = excluded.sector,
  exchange = excluded.exchange;

insert into public.investor_profiles (
  id, name, risk_tolerance, investment_horizon_years,
  max_position_percent, max_sector_percent, is_demo
) values
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c', 'Ananya', 'low', 5, 10, 35, true),
  ('9c3bfb92-8815-43f7-8316-851c7f8d8ae9', 'Mira', 'medium', 8, 15, 40, true),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d', 'Aarav', 'high', 10, 25, 50, true)
on conflict (id) do update set
  name = excluded.name,
  risk_tolerance = excluded.risk_tolerance,
  investment_horizon_years = excluded.investment_horizon_years,
  max_position_percent = excluded.max_position_percent,
  max_sector_percent = excluded.max_sector_percent,
  is_demo = true;

insert into public.holdings (profile_id, company_id, quantity, average_cost) values
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c', 'ebce53d4-8628-4df2-8aa9-b5f1ddbd94f8', 18, 1325.50),
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c', '43ba499f-23cc-4692-b214-1f10d233b84c', 30, 1460.00),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d', '2adf8b37-913a-4677-a412-20e617637f41', 12, 3510.00),
  ('16b24f78-e814-4e72-861e-81f4d241fc9d', '14968b6f-456f-4b6a-a455-73b17fe246ff', 20, 1480.00)
on conflict (profile_id, company_id) do update set
  quantity = excluded.quantity,
  average_cost = excluded.average_cost;

insert into public.watchlist_items (profile_id, company_id) values
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c', '2adf8b37-913a-4677-a412-20e617637f41'),
  ('a7e99bdf-9459-4806-ada5-a596cf4d453c', '14968b6f-456f-4b6a-a455-73b17fe246ff')
on conflict (profile_id, company_id) do nothing;

commit;
