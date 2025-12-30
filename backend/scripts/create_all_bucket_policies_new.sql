-- Create RLS policies for all 53 client buckets
-- Run this after creating buckets

DO $$
DECLARE
    client_name text;
    client_names text[] := ARRAY[
        'a-perfect-promotion',
        'abundantly',
        'american-ethanol',
        'archway-learning-solutions',
        'atrenet',
        'beistle',
        'bucklandco',
        'cas-severn',
        'clarke-consulting',
        'clearfield-group',
        'conneqt',
        'eckerd-connects',
        'elderwood',
        'enercare',
        'evenbound',
        'family-services-of-westchester',
        'finance-of-america-commercial',
        'gatehouse-media',
        'global-aerospace',
        'haylor',
        'heniff-transportation',
        'highpoint',
        'hub-international',
        'jani-king',
        'kettle-cuisine',
        'lightyear-capital',
        'martinryan',
        'mcenearney-associates',
        'medical-guardian',
        'megaphone-marketing',
        'metlife',
        'mutual-of-america',
        'nfp',
        'now-optics',
        'oswald-companies',
        'pacer-group',
        'paycom',
        'pension-benefit-information',
        'pink-halo-projects',
        'pocono-medical-center',
        'romp-n-roll',
        'ryan',
        'sirva',
        'starwood-capital',
        'suffolk-federal',
        'thermo-king',
        'totalbenefits',
        'transplace',
        'umicore',
        'versant-health',
        'vitech',
        'wardlaw-hartridge',
        'whittier-streetschool'
    ];
BEGIN
    FOREACH client_name IN ARRAY client_names
    LOOP
        -- SELECT policy
        EXECUTE format('
            CREATE POLICY %I ON storage.objects 
            FOR SELECT 
            TO anon 
            USING (bucket_id = %L)',
            'Allow anon reads from ' || client_name,
            client_name
        );

        -- INSERT policy
        EXECUTE format('
            CREATE POLICY %I ON storage.objects 
            FOR INSERT 
            TO anon 
            WITH CHECK (bucket_id = %L)',
            'Allow anon uploads to ' || client_name,
            client_name
        );

        -- UPDATE policy
        EXECUTE format('
            CREATE POLICY %I ON storage.objects 
            FOR UPDATE 
            TO anon 
            USING (bucket_id = %L)',
            'Allow anon updates to ' || client_name,
            client_name
        );

        -- DELETE policy
        EXECUTE format('
            CREATE POLICY %I ON storage.objects 
            FOR DELETE 
            TO anon 
            USING (bucket_id = %L)',
            'Allow anon deletes from ' || client_name,
            client_name
        );

        RAISE NOTICE 'Created policies for: %', client_name;
    END LOOP;
END $$;

-- Verify policies were created
SELECT COUNT(*) as policy_count 
FROM pg_policies 
WHERE schemaname = 'storage' 
AND tablename = 'objects'
AND roles @> '{anon}';

