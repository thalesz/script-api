#!/usr/bin/env python3
"""
Auto Loader: carrega automaticamente os CSVs locais em script/output/.

O filtro de duplicidade é feito no banco durante a carga (insert-only para novos
codigo_incra), então é seguro processar os arquivos em toda execução.
"""

import os
import psycopg2
from pathlib import Path
from logger import get_logger
from config import cfg
from loader import Loader

class AutoLoader:
    def __init__(self):
        self.logger = get_logger('auto_loader', Path(cfg.LOGS_DIR) / 'auto_loader.log')
        self.conn_params = self._build_conn_params()
        self.output_dir = Path(cfg.DOWNLOAD_DIR)
        
    def _build_conn_params(self):
        return {
            'host': os.getenv('PG_HOST', 'localhost'),
            'port': int(os.getenv('PG_PORT', '5432')),
            'database': os.getenv('PG_DATABASE', 'sncr'),
            'user': os.getenv('PG_USER', 'postgres'),
            'password': os.getenv('PG_PASSWORD', 'postgres'),
        }
    
    def _list_csv_files(self):
        """Lista todos os arquivos CSV disponíveis para carga."""
        return sorted(self.output_dir.glob('*.csv'))
    
    def run(self):
        """Executa carregamento automático"""
        self.logger.info('=== Iniciando Auto Loader ===')

        # Garantir que o banco de dados e as tabelas existem no início.
        try:
            loader = Loader(dsn=self.conn_params)
            loader.prepare_table()
            self.logger.info("✅ Banco de dados e tabelas preparados")
        except Exception as e:
            self.logger.error(f"❌ Erro ao preparar banco de dados: {e}")
            raise
        
        csv_files = self._list_csv_files()
        if not csv_files:
            self.logger.info('Nenhum arquivo CSV encontrado em %s', self.output_dir)
            print(f'❌ Nenhum CSV encontrado em {self.output_dir}')
            return

        self.logger.info('CSVs encontrados para carga: %s', len(csv_files))
        print(f'\n📍 Arquivos CSV para processar: {len(csv_files)}\n')

        # Usar o loader já criado no início
        loaded_count = 0
        failed_files = []
        
        for csv_file in csv_files:
            try:
                self.logger.info(f'Iniciando processamento de {csv_file}')
                loader._process_file(csv_file)
                loaded_count += 1
                print(f'✅ {csv_file.name}: Carregado com sucesso')
                self.logger.info(f'✅ {csv_file.name} carregado com sucesso')
            except Exception as e:
                self.logger.error(f'❌ Erro ao carregar {csv_file}: {e}')
                failed_files.append(csv_file.name)
                print(f'❌ {csv_file.name}: Erro - {str(e)[:100]}')
        
        print(f'\n📊 Resumo:')
        print(f'   ✅ Carregados: {loaded_count}')
        print(f'   ❌ Falhas: {len(failed_files)}')
        
        if failed_files:
            print(f'\n   Arquivos com falha: {", ".join(failed_files)}')
            self.logger.info(f'Arquivos com falha: {failed_files}')
        
        self.logger.info(f'Auto Loader finalizado: {loaded_count} carregados, {len(failed_files)} falhas')


if __name__ == '__main__':
    auto_loader = AutoLoader()
    auto_loader.run()
