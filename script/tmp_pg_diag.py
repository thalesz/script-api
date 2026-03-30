import os, traceback
print('--- PG env vars (repr) ---')
for k in ('PG_HOST','PG_PORT','PG_DATABASE','PG_USER','PG_PASSWORD'):
    v = os.getenv(k)
    print(k, repr(v))
    if v is not None:
        print(' bytes:', list(v.encode('utf-8', errors='backslashreplace')))
print('--- All env keys with PG prefix ---')
for k,v in os.environ.items():
    if k.upper().startswith('PG'):
        print(k, repr(v))
print('--- try minimal connect (will catch UnicodeDecodeError) ---')
import psycopg2
params = {
  'host': os.getenv('PG_HOST','localhost'),
  'port': int(os.getenv('PG_PORT','5432') or 5432),
  'dbname': os.getenv('PG_DATABASE','sncr'),
  'user': os.getenv('PG_USER','postgres'),
  'password': os.getenv('PG_PASSWORD','postgres'),
}
print('connect params repr:', {k:repr(v) for k,v in params.items()})
try:
    conn = psycopg2.connect(**params)
    conn.close()
    print('CONNECTED OK')
except Exception:
    traceback.print_exc()
