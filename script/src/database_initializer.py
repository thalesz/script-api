#!/usr/bin/env python3
"""
Database Initializer: Classe para inicializar o banco de dados SNCR
Cria tabelas/índices a partir de schema.sql e popula dados base
"""

import os
import psycopg2
from psycopg2 import sql
from pathlib import Path
from logger import get_logger
from config import cfg
from states import LOCAL_STATES


class DatabaseInitializer:
    """Inicializa o banco de dados SNCR com tabelas, índices e dados"""

    # Reutiliza a fonte única de estados para evitar duplicação entre módulos
    STATES_DATA = [tuple(item.split(' - ', 1)) for item in LOCAL_STATES]
    SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'sql' / 'schema.sql'

    def __init__(self, conn_params=None):
        """
        Inicializa o DatabaseInitializer
        
        Args:
            conn_params (dict): Parâmetros de conexão PostgreSQL.
                               Se None, constrói a partir de variáveis de ambiente.
        """
        self.logger = get_logger('db_initializer', Path(cfg.LOGS_DIR) / 'init_db.log')
        self.conn_params = conn_params or self._build_conn_params_from_env()
        self.logger.info('DatabaseInitializer inicializado com params: %s:%s db=%s',
                        self.conn_params['host'], 
                        self.conn_params['port'], 
                        self.conn_params['dbname'])

    def _build_conn_params_from_env(self):
        """Constrói parâmetros de conexão a partir de variáveis de ambiente"""
        params = {
            'host': os.getenv('PG_HOST', 'localhost').strip(),
            'port': int(os.getenv('PG_PORT', '5432')),
            'dbname': os.getenv('PG_DATABASE', 'sncr').strip(),
            'user': os.getenv('PG_USER', 'postgres').strip(),
            'password': os.getenv('PG_PASSWORD', 'postgres').strip(),
        }
        return params

    def _connect(self):
        """Conecta ao PostgreSQL com fallback para pg8000 se necessário"""
        try:
            return psycopg2.connect(**self.conn_params)
        except UnicodeDecodeError:
            self.logger.warning('psycopg2 com UnicodeDecodeError; tentando fallback pg8000')
            try:
                import pg8000
                return pg8000.connect(
                    host=self.conn_params['host'],
                    port=self.conn_params['port'],
                    database=self.conn_params['dbname'],
                    user=self.conn_params['user'],
                    password=self.conn_params['password']
                )
            except Exception as e:
                if self._is_missing_database_error(e):
                    self.logger.info('Banco alvo ainda não existe; tentativa de criação será realizada')
                else:
                    self.logger.exception('Fallback pg8000 falhou')
                raise

    def _is_missing_database_error(self, error):
        """Detecta erro de banco inexistente em psycopg2 e pg8000."""
        message = str(error).lower()
        if 'does not exist' in message:
            return True
        if 'não existe o banco de dados' in message or 'nao existe o banco de dados' in message:
            return True
        if '3d000' in message:
            return True

        args = getattr(error, 'args', ())
        if args:
            first = args[0]
            if isinstance(first, dict):
                sqlstate = str(first.get('C', '')).upper()
                if sqlstate == '3D000':
                    return True
        return False

    def _ensure_database_exists(self):
        """Garante que o banco de dados 'sncr' existe"""
        dbname = self.conn_params['dbname']
        try:
            # Tenta conectar ao banco de dados
            conn = self._connect()
            conn.close()
            self.logger.info(f'Banco de dados "{dbname}" já existe')
            return
        except Exception as e:
            if self._is_missing_database_error(e):
                self.logger.info(f'Banco de dados "{dbname}" não existe. Criando...')
                self._create_database(dbname)
                return
            raise

    def _create_database(self, dbname):
        """Cria o banco de dados"""
        try:
            # Conecta ao banco padrão 'postgres' para criar novo banco
            params = self.conn_params.copy()
            params['dbname'] = 'postgres'
            try:
                conn = psycopg2.connect(**params)
            except UnicodeDecodeError:
                self.logger.warning('psycopg2 com UnicodeDecodeError ao criar DB; tentando pg8000')
                import pg8000
                conn = pg8000.connect(
                    host=params['host'],
                    port=params['port'],
                    database=params['dbname'],
                    user=params['user'],
                    password=params['password']
                )
            conn.autocommit = True
            
            with conn.cursor() as cur:
                # Usa sql.Identifier para escape seguro do nome do banco
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
                self.logger.info(f'Banco de dados "{dbname}" criado com sucesso')
            
            conn.close()
        except psycopg2.errors.DuplicateDatabase:
            self.logger.info(f'Banco de dados "{dbname}" já existe')
        except Exception as e:
            self.logger.error(f'Erro ao criar banco de dados: {e}')
            raise

    def _apply_schema(self, cur):
        """Executa o schema SQL versionado para criar tabelas e índices."""
        if not self.SCHEMA_PATH.exists():
            raise FileNotFoundError(f'Schema SQL não encontrado: {self.SCHEMA_PATH}')

        schema_sql = self.SCHEMA_PATH.read_text(encoding='utf-8')
        cur.execute(schema_sql)
        self.logger.info('Schema aplicado a partir de %s', self.SCHEMA_PATH)

    def _populate_states(self, cur, conn):
        """Popula a tabela 'states' com os 27 estados brasileiros"""
        # Verifica se já tem dados
        cur.execute("SELECT COUNT(*) FROM states")
        count = cur.fetchone()[0]
        
        if count == 0:
            cur.executemany(
                "INSERT INTO states (uf, name) VALUES (%s, %s) ON CONFLICT (uf) DO NOTHING",
                self.STATES_DATA
            )
            conn.commit()
            self.logger.info('Tabela "states" populada com 27 estados')
        else:
            self.logger.info(f'Tabela "states" já contém {count} registros')

    def initialize(self):
        """
        Executa a inicialização completa do banco de dados
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            self.logger.info('=== Iniciando inicialização do banco de dados ===')
            
            # Garante que o banco existe
            self._ensure_database_exists()
            
            # Conecta ao banco e aplica schema
            with self._connect() as conn:
                with conn.cursor() as cur:
                    self._apply_schema(cur)
                    conn.commit()
                    
                    # Popular dados dos estados
                    self._populate_states(cur, conn)
            
            self.logger.info('✅ Banco de dados inicializado com sucesso')
            return True
            
        except Exception as e:
            self.logger.error(f'❌ Erro ao inicializar banco: {e}', exc_info=True)
            return False
