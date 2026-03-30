#!/usr/bin/env python3
"""
Init DB: Inicializa o banco de dados com tabelas e dados
Deve ser executado antes de rodar downloader ou auto_loader
"""

import sys
import os
from pathlib import Path
from database_initializer import DatabaseInitializer
from logger import get_logger
from config import cfg

def init_database():
    """Inicializa banco de dados com tabelas e dados"""
    logger = get_logger('init_db', Path(cfg.LOGS_DIR) / 'init_db.log')
    
    # Build connection params from environment
    conn_params = {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': int(os.getenv('PG_PORT', '5432')),
        'dbname': os.getenv('PG_DATABASE', 'sncr'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'postgres'),
    }
    
    try:
        initializer = DatabaseInitializer(conn_params=conn_params)
        success = initializer.initialize()
        
        if success:
            print('✅ Banco de dados inicializado com sucesso!')
            print('   - Banco: sncr')
            print('   - Tabelas: states (27 estados), sncr_records')
            print('   - Índices: uf, municipio, proprietario')
            return 0
        else:
            print('❌ Erro ao inicializar banco de dados')
            return 1
    except Exception as e:
        logger.error(f'❌ Erro ao inicializar banco: {e}', exc_info=True)
        print(f'❌ Erro ao inicializar banco: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(init_database())
