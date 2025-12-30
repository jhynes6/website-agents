-- Create all client buckets for Supabase Storage
-- Run this via MCP or Supabase SQL editor

-- Generate INSERT statements for all client buckets
INSERT INTO storage.buckets (id, name, public, file_size_limit)
SELECT 
    client_slug,
    client_slug,
    false,
    52428800  -- 50MB
FROM (VALUES
    ('a-perfect-promotion'),
    ('abundantly'),
    ('american-ethanol'),
    ('archway-learning-solutions'),
    ('atrenet'),
    ('beistle'),
    ('bucklandco'),
    ('cas-severn'),
    ('clarke-consulting'),
    ('clearfield-group'),
    ('conneqt'),
    ('eckerd-connects'),
    ('elderwood'),
    ('enercare'),
    ('evenbound'),
    ('family-services-of-westchester'),
    ('finance-of-america-commercial'),
    ('gatehouse-media'),
    ('global-aerospace'),
    ('haylor'),
    ('heniff-transportation'),
    ('highpoint'),
    ('hub-international'),
    ('jani-king'),
    ('kettle-cuisine'),
    ('lightyear-capital'),
    ('martinryan'),
    ('mcenearney-associates'),
    ('medical-guardian'),
    ('megaphone-marketing'),
    ('metlife'),
    ('mutual-of-america'),
    ('nfp'),
    ('now-optics'),
    ('oswald-companies'),
    ('pacer-group'),
    ('paycom'),
    ('pension-benefit-information'),
    ('pink-halo-projects'),
    ('pocono-medical-center'),
    ('romp-n-roll'),
    ('ryan'),
    ('sirva'),
    ('starwood-capital'),
    ('suffolk-federal'),
    ('thermo-king'),
    ('totalbenefits'),
    ('transplace'),
    ('umicore'),
    ('versant-health'),
    ('vitech'),
    ('wardlaw-hartridge'),
    ('whittier-streetschool')
) AS clients(client_slug)
ON CONFLICT (id) DO NOTHING;

-- Verify all buckets were created
SELECT COUNT(*) as bucket_count FROM storage.buckets;

