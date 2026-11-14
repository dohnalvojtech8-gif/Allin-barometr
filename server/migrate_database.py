"""One-time verified migration. Secrets are read from environment, never logged."""
import hashlib
import json
import logging
import threading
import time
from urllib.parse import urlparse, parse_qs

TABLES = ('users', 'stock_documents', 'stock_change_log', 'shop_bundles', 'bottle_calibrations', 'scan_photos',
          'sessions', 'invitations', 'invitation_uses', 'events', 'unlocks', 'rate_buckets')

def migrate(source_url, target_url, schema, statements, source_schema='public'):
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    if not target_url or source_url == target_url:
        return
    target_host = urlparse(target_url).hostname or ''
    if not target_host.endswith(('.supabase.co', '.supabase.com')):
        raise RuntimeError('SUPABASE_DATABASE_URL must point to Supabase')
    sslmode = parse_qs(urlparse(target_url).query).get('sslmode', [''])[0]
    if sslmode not in ('require', 'verify-ca', 'verify-full'):
        raise RuntimeError('Supabase connection requires sslmode=require or stricter')
    source = None
    try:
        with psycopg.connect(target_url, connect_timeout=15, row_factory=dict_row) as target:
            target.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
            target.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(schema)))
            target.execute('CREATE TABLE IF NOT EXISTS migration_status (name TEXT PRIMARY KEY, completed_at DOUBLE PRECISION NOT NULL, summary_json TEXT NOT NULL)')
            target.execute('ALTER TABLE migration_status ENABLE ROW LEVEL SECURITY')
            target.execute("SELECT pg_advisory_xact_lock(82735490)")
            if target.execute("SELECT 1 FROM migration_status WHERE name='render_to_supabase_v1'").fetchone():
                logging.warning('BAROMETR database: Supabase; verified migration already completed')
                return
            if not source_url:
                raise RuntimeError('Original DATABASE_URL is needed for the first migration')
            source = psycopg.connect(source_url, connect_timeout=15, row_factory=dict_row)
            source.execute('SET lock_timeout TO \'60s\'')
            existing = {r['table_name'] for r in source.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=%s',(source_schema,)).fetchall()}
            tables = [t for t in TABLES if t in existing]
            if not (set(TABLES)-{'stock_documents','stock_change_log'} <= existing):
                raise RuntimeError('Original account tables are incomplete; migration stopped')
            source.execute(sql.SQL('LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE').format(sql.SQL(',').join(sql.Identifier(source_schema, t) for t in tables)))
            for statement in statements:
                target.execute(statement)
            target.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions_json TEXT NOT NULL DEFAULT '{}'")
            target.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS stock_owner_id TEXT REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED')
            if target.execute('SELECT count(*) AS n FROM users').fetchone()['n']:
                raise RuntimeError('Target already contains accounts; refusing to overwrite profiles')
            summary = {}
            for table in tables:
                rows = source.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(source_schema, table))).fetchall()
                if rows:
                    columns = list(rows[0])
                    insert = sql.SQL('INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING').format(sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, columns)), sql.SQL(',').join(sql.Placeholder() for _ in columns))
                    with target.cursor() as cursor:
                        cursor.executemany(insert, [[r[c] for c in columns] for r in rows])
                copied = target.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall()
                def fingerprint(values):
                    canonical = sorted(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, separators=(',', ':')) for r in values)
                    return hashlib.sha256('\n'.join(canonical).encode()).hexdigest()
                if len(copied) != len(rows) or fingerprint([{k:r[k] for k in rows[0]} for r in copied] if rows else copied) != fingerprint(rows):
                    raise RuntimeError('Migration verification failed for '+table)
                target.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(sql.Identifier(table)))
                summary[table] = len(rows)
            target.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC, anon, authenticated').format(sql.Identifier(schema)))
            target.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM PUBLIC, anon, authenticated').format(sql.Identifier(schema)))
            target.execute('INSERT INTO migration_status VALUES (%s,%s,%s)', ('render_to_supabase_v1', time.time(), json.dumps(summary)))
        # Keep old instances from accepting writes during Render's traffic switch.
        held_source = source
        source = None
        def release_old_database():
            time.sleep(120)
            held_source.rollback()
            held_source.close()
        threading.Thread(target=release_old_database, daemon=True).start()
        logging.warning('BAROMETR Supabase migration verified: %s', json.dumps(summary, sort_keys=True))
    finally:
        if source:
            source.rollback()
            source.close()
