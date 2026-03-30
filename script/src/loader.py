import os
import glob
import csv
from pathlib import Path
import psycopg2
from psycopg2 import sql
from config import cfg
from logger import get_logger
from states import LOCAL_STATES


class Loader:
    """Carrega CSVs no PostgreSQL em modo insert-only: apenas `codigo_incra` novos são inseridos."""

    CREATE_STATES_SQL = """
    CREATE TABLE IF NOT EXISTS states (
        uf VARCHAR(2) PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    );
    """

    CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS sncr_records (
        codigo_incra TEXT PRIMARY KEY,
        matricula VARCHAR(20),
        municipio TEXT,
        denominacao TEXT,
        proprietario TEXT,
        pct_obtencao NUMERIC(12,4),
        uf VARCHAR(2) REFERENCES states(uf) ON DELETE RESTRICT,
        loaded_at TIMESTAMP DEFAULT now()
    );
    """

    # Reutiliza a fonte única de estados para evitar duplicação entre módulos
    STATES_DATA = [tuple(item.split(' - ', 1)) for item in LOCAL_STATES]

    @staticmethod
    def _normalize_conn_params(params: dict) -> dict:
        """Normalize connection params to psycopg2 style keys."""
        if not isinstance(params, dict):
            return params
        normalized = dict(params)
        if 'dbname' not in normalized and 'database' in normalized:
            normalized['dbname'] = normalized.pop('database')
        return normalized

    def __init__(self, dsn=None):
        self.logger = get_logger('loader', Path(cfg.LOGS_DIR) / 'loader.log')
        # connection params dict (prefer explicit args to avoid DSN parsing/encoding issues)
        if dsn and isinstance(dsn, dict):
            self.conn_params = self._normalize_conn_params(dsn)
        else:
            self.conn_params = self._build_conn_params_from_env()

    def _build_conn_params_from_env(self):
        host = os.getenv('PG_HOST', 'localhost')
        port = os.getenv('PG_PORT', '5432')
        db = os.getenv('PG_DATABASE', 'sncr')
        user = os.getenv('PG_USER', 'postgres')
        pwd = os.getenv('PG_PASSWORD', 'postgres')
        # ensure strings and strip accidental BOM/whitespace
        params = {
            'host': str(host).strip(),
            'port': int(str(port).strip()),
            'dbname': str(db).strip(),
            'user': str(user).strip(),
            'password': str(pwd).strip(),
        }
        # log connection target without password
        self.logger.info('Postgres target: %s:%s db=%s user=%s', params['host'], params['port'], params['dbname'], params['user'])
        return params

    def _connect(self):
        dbname = self.conn_params.get('dbname') or self.conn_params.get('database')
        try:
            return psycopg2.connect(**self.conn_params)
        except UnicodeDecodeError:
            # Some Windows environments may provoke a UnicodeDecodeError inside the
            # binary psycopg2 driver. Fall back to a pure-Python driver (pg8000)
            # to avoid platform-specific decoding bugs.
            self.logger.warning('psycopg2 raised UnicodeDecodeError; attempting pg8000 fallback')
            try:
                import pg8000
                # pg8000 uses 'database' instead of 'dbname'
                return pg8000.connect(host=self.conn_params['host'], port=self.conn_params['port'], database=dbname, user=self.conn_params['user'], password=self.conn_params['password'])
            except Exception:
                self.logger.exception('pg8000 fallback failed')
                raise
        except Exception:
            # re-raise other exceptions
            raise

    def prepare_table(self):
        # Ensure the target database exists; if not, attempt to create it
        self.ensure_database_exists()

        with self._connect() as conn:
            with conn.cursor() as cur:
                # Create states table first (no dependencies)
                cur.execute(self.CREATE_STATES_SQL)
                # Populate states table if empty
                cur.execute("SELECT COUNT(*) FROM states")
                if cur.fetchone()[0] == 0:
                    cur.executemany(
                        "INSERT INTO states (uf, name) VALUES (%s, %s)",
                        self.STATES_DATA
                    )
                    conn.commit()
                    self.logger.info('Tabela states populada com 27 estados')
                # Create sncr_records table (references states)
                cur.execute(self.CREATE_SQL)
                conn.commit()
        self.logger.info('Tabelas states e sncr_records verificadas/criadas')

    def ensure_database_exists(self):
        dbname = self.conn_params.get('dbname') or self.conn_params.get('database')
        try:
            # try connecting to target database using _connect() for proper error handling
            conn = self._connect()
            conn.close()
            return
        except Exception as e:
            msg = str(e).lower()
            # check for "database does not exist" error (handle both psycopg2 and pg8000 formats)
            db_not_exist = ('does not exist' in msg or 
                           '3d000' in msg or  # PostgreSQL error code for "database does not exist"
                           'n' in msg and 'existe' in msg and 'banco' in msg)  # Portuguese message
            if db_not_exist:
                self.logger.info('Database %s not found; attempting to create it', dbname)
                # connect to maintenance DB (default 'postgres') to create the target DB
                maint_db = os.getenv('PG_MAINTENANCE_DB', 'postgres')
                mparams = self.conn_params.copy()
                mparams['dbname'] = maint_db
                try:
                    # use psycopg2 for create database with autocommit
                    mconn = psycopg2.connect(**mparams)
                    mconn.autocommit = True
                    with mconn.cursor() as mcur:
                        mcur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(dbname)))
                    mconn.close()
                    self.logger.info('Database %s created', dbname)
                    return
                except UnicodeDecodeError:
                    # fallback to pg8000 to perform CREATE DATABASE
                    self.logger.warning('psycopg2 UnicodeDecodeError during DB create; attempting pg8000')
                    try:
                        import pg8000
                        mconn = pg8000.connect(host=mparams['host'], port=mparams['port'], database=mparams['dbname'], user=mparams['user'], password=mparams['password'])
                        mconn.autocommit = True
                        cur = mconn.cursor()
                        cur.execute('CREATE DATABASE "%s"' % dbname)
                        cur.close()
                        mconn.close()
                        self.logger.info('Database %s created via pg8000', dbname)
                        return
                    except Exception:
                        self.logger.exception('pg8000 fallback failed to create database')
                        raise
                except Exception:
                    self.logger.exception('Failed to create database %s', dbname)
                    raise
            else:
                # re-raise unexpected exceptions
                raise

    def _process_file(self, path: Path):
        uf = path.stem.split('_')[0] if '_' in path.stem else None
        src = str(path)
        self.logger.info(f'Carregando arquivo {src}')
        csv_rows = 0
        csv_distinct_codigos = 0
        existing_in_db = 0
        inserted_new = 0
        inserted_rows = 0
        with self._connect() as conn:
            with conn.cursor() as cur:
                # create temp table
                cur.execute("DROP TABLE IF EXISTS tmp_sncr;")
                cur.execute("CREATE TEMP TABLE tmp_sncr (LIKE sncr_records INCLUDING DEFAULTS) ON COMMIT DROP;")
                # copy from CSV (semicolon separated)
                with path.open('r', encoding='utf-8') as f:
                    # read header to map columns
                    reader = csv.DictReader(f, delimiter=';')
                    rows = list(reader)
                    if not rows:
                        self.logger.info(f'Arquivo {src} vazio, pulando')
                        return
                    csv_rows = len(rows)
                    # insert into temp table
                    cols = list(rows[0].keys())
                    # ensure columns exist in target mapping
                    insert_cols = cols + ['uf']
                    placeholders = ','.join(['%s'] * len(insert_cols))
                    insert_query = sql.SQL('INSERT INTO tmp_sncr ({}) VALUES ({})').format(
                        sql.SQL(',').join(map(sql.Identifier, insert_cols)),
                        sql.SQL(placeholders)
                    )
                    for r in rows:
                        vals = [r.get(c) for c in cols]
                        vals.append(uf)
                        # normalize numeric - validate pct_obtencao
                        if 'pct_obtencao' in cols:
                            idx = cols.index('pct_obtencao')
                            val = str(vals[idx]).strip() if vals[idx] else ''
                            if val and val.lower() not in ('none', 'null'):
                                try:
                                    # validate by converting to float (comma to dot)
                                    float(val.replace(',', '.'))
                                    vals[idx] = val.replace(',', '.')
                                except (ValueError, AttributeError):
                                    # invalid numeric, set to None
                                    vals[idx] = None
                            else:
                                vals[idx] = None
                        cur.execute(insert_query, vals)

                # Metrics before insert: unique codes in file and how many already exist in DB.
                cur.execute("SELECT COUNT(DISTINCT codigo_incra) FROM tmp_sncr WHERE codigo_incra IS NOT NULL")
                csv_distinct_codigos = cur.fetchone()[0] or 0

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT DISTINCT t.codigo_incra
                        FROM tmp_sncr t
                        JOIN sncr_records s ON s.codigo_incra = t.codigo_incra
                        WHERE t.codigo_incra IS NOT NULL
                    ) q;
                    """
                )
                existing_in_db = cur.fetchone()[0] or 0

                # Insert only records that do not exist yet in sncr_records.
                insert_new = r"""
                INSERT INTO sncr_records (codigo_incra, matricula, municipio, denominacao, proprietario, pct_obtencao, uf)
                SELECT t.codigo_incra,
                       t.matricula,
                       t.municipio,
                       t.denominacao,
                       t.proprietario,
                       CASE WHEN t.pct_obtencao IS NULL OR t.pct_obtencao::text ~ '^\s*$' THEN NULL
                            WHEN t.pct_obtencao::text ~ '^\d+([.,]\d+)?$' THEN t.pct_obtencao::numeric
                            ELSE NULL
                       END,
                       t.uf
                FROM (
                    SELECT DISTINCT ON (codigo_incra)
                        codigo_incra, matricula, municipio, denominacao, proprietario, pct_obtencao, uf
                    FROM tmp_sncr
                    WHERE codigo_incra IS NOT NULL
                    ORDER BY codigo_incra
                ) t
                LEFT JOIN sncr_records s ON s.codigo_incra = t.codigo_incra
                WHERE s.codigo_incra IS NULL;
                """
                cur.execute(insert_new)
                inserted_rows = cur.rowcount if cur.rowcount is not None else 0
                inserted_new = inserted_rows
                conn.commit()
        self.logger.info(
            'Resumo carga %s | linhas_csv=%s | codigos_unicos=%s | novos=%s | ja_existiam=%s | linhas_inseridas=%s',
            src,
            csv_rows,
            csv_distinct_codigos,
            inserted_new,
            existing_in_db,
            inserted_rows,
        )
        print(
            f"Resumo carga {path.name}: linhas_csv={csv_rows}, codigos_unicos={csv_distinct_codigos}, "
            f"novos={inserted_new}, ja_existiam={existing_in_db}, linhas_inseridas={inserted_rows}"
        )

    def run(self, input_dir=None):
        input_dir = Path(input_dir or cfg.DOWNLOAD_DIR)
        files = sorted(glob.glob(str(input_dir / '*.csv')))
        if not files:
            self.logger.info('Nenhum CSV encontrado em %s', input_dir)
            return
        self.prepare_table()
        for f in files:
            try:
                self._process_file(Path(f))
            except Exception as e:
                self.logger.exception('Falha ao processar %s: %s', f, e)


def run_loader():
    l = Loader()
    l.run()


if __name__ == '__main__':
    run_loader()
