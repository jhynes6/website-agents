-- Create RLS policies for all client buckets (allows full CRUD with anon key)

-- Helper function to create policies for a bucket
CREATE OR REPLACE FUNCTION create_bucket_policies(bucket_name text) RETURNS void AS $$
BEGIN
    -- Drop existing policies if they exist
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'Allow anon uploads to ' || bucket_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'Allow anon reads from ' || bucket_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'Allow anon updates to ' || bucket_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'Allow anon deletes from ' || bucket_name);
    
    -- Create comprehensive policies
    EXECUTE format('
        CREATE POLICY %I
        ON storage.objects FOR INSERT
        TO anon
        WITH CHECK (bucket_id = %L)
    ', 'Allow anon uploads to ' || bucket_name, bucket_name);
    
    EXECUTE format('
        CREATE POLICY %I
        ON storage.objects FOR SELECT
        TO anon
        USING (bucket_id = %L)
    ', 'Allow anon reads from ' || bucket_name, bucket_name);
    
    EXECUTE format('
        CREATE POLICY %I
        ON storage.objects FOR UPDATE
        TO anon
        USING (bucket_id = %L)
    ', 'Allow anon updates to ' || bucket_name, bucket_name);
    
    EXECUTE format('
        CREATE POLICY %I
        ON storage.objects FOR DELETE
        TO anon
        USING (bucket_id = %L)
    ', 'Allow anon deletes from ' || bucket_name, bucket_name);
END;
$$ LANGUAGE plpgsql;

-- Apply policies to all client buckets
SELECT create_bucket_policies('archway-learning-solutions');
SELECT create_bucket_policies('abundantly');
SELECT create_bucket_policies('american-ethanol');
SELECT create_bucket_policies('atrenet');
SELECT create_bucket_policies('beistle');
SELECT create_bucket_policies('bucklandco');
SELECT create_bucket_policies('cas-severn');
SELECT create_bucket_policies('conneqt');
SELECT create_bucket_policies('clarke-consulting');
SELECT create_bucket_policies('clearfield-group');
SELECT create_bucket_policies('cogent-consulting');
SELECT create_bucket_policies('d2-creative');
SELECT create_bucket_policies('dodeka-digital');
SELECT create_bucket_policies('evenbound');
SELECT create_bucket_policies('f1-cloud-solutions');
SELECT create_bucket_policies('forge-apollo');
SELECT create_bucket_policies('galactic-fed');
SELECT create_bucket_policies('iconic-supply-co.');
SELECT create_bucket_policies('incyte-media');
SELECT create_bucket_policies('integrity-professionals');
SELECT create_bucket_policies('kilter.la');
SELECT create_bucket_policies('klickrr');
SELECT create_bucket_policies('lib-consulting-group');
SELECT create_bucket_policies('lithyem');
SELECT create_bucket_policies('makers-garments');
SELECT create_bucket_policies('manufacturing-geeks');
SELECT create_bucket_policies('mintleads');
SELECT create_bucket_policies('nga-healthcare');
SELECT create_bucket_policies('nextlevel-thinking');
SELECT create_bucket_policies('nutramarketers');
SELECT create_bucket_policies('on-the-marc-media');
SELECT create_bucket_policies('peachtree-va');
SELECT create_bucket_policies('pipefy');
SELECT create_bucket_policies('push-analytics');
SELECT create_bucket_policies('quintessa-marketing');
SELECT create_bucket_policies('reach-marketing');
SELECT create_bucket_policies('revdrive');
SELECT create_bucket_policies('revolttek');
SELECT create_bucket_policies('simple-machines');
SELECT create_bucket_policies('skayle-360');
SELECT create_bucket_policies('slice-communications');
SELECT create_bucket_policies('slingshot');
SELECT create_bucket_policies('sock-fancy');
SELECT create_bucket_policies('terra-collective');
SELECT create_bucket_policies('ubiq-education');
SELECT create_bucket_policies('vew-media');
SELECT create_bucket_policies('wendt-partners');
SELECT create_bucket_policies('white-label-digital');
SELECT create_bucket_policies('woven-legal');
SELECT create_bucket_policies('x-agency');
SELECT create_bucket_policies('zoomgrants');
SELECT create_bucket_policies('pi-lit');

-- Clean up helper function
DROP FUNCTION IF EXISTS create_bucket_policies(text);

