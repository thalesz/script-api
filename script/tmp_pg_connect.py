import traceback, psycopg2
try:
    conn = psycopg2.connect(host='localhost', port=5432, dbname='sncr', user='postgres', password='postgres')
    conn.close()
    print('DIRECT CONNECT OK')
except Exception:
    traceback.print_exc()
