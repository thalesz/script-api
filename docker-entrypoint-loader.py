#!/usr/bin/env python3
"""
Entrypoint do Loader: Carrega CSVs para PostgreSQL após scraper completar
"""

import sys
import os
import subprocess
from pathlib import Path

# Mudar para o diretório da aplicação
os.chdir('/app')

# Adicionar script/src ao PYTHONPATH para imports
sys.path.insert(0, '/app/script/src')

# ====== Aguardar Scraper Completar ======
print("\n" + "="*50)
print("⏳ AGUARDANDO SCRAPER COMPLETAR")
print("="*50)

sentinel_file = Path('/app/script/data/checkpoints/scraper_done')

# Aguarda o arquivo sentinel (máximo 2 horas)
import time
max_wait = 7200  # 2 horas
elapsed = 0
while not sentinel_file.exists() and elapsed < max_wait:
    print(f"   Aguardando sentinel... ({elapsed}s)", end='\r')
    time.sleep(5)
    elapsed += 5

if not sentinel_file.exists():
    print(f"\n❌ Timeout: Scraper não completou em {max_wait}s")
    sys.exit(1)

print(f"✅ Scraper completou! Sentinela encontrada.")

# ====== Inicializar Banco de Dados (se necessário) ======
print("\n" + "="*50)
print("🔧 GARANTINDO BANCO DE DADOS")
print("="*50)

try:
    from database_initializer import DatabaseInitializer
    import os as os_module
    
    conn_params = {
        'host': os_module.getenv('PG_HOST', 'postgres'),
        'port': int(os_module.getenv('PG_PORT', '5432')),
        'dbname': os_module.getenv('PG_DATABASE', 'sncr'),
        'user': os_module.getenv('PG_USER', 'postgres'),
        'password': os_module.getenv('PG_PASSWORD', 'postgres'),
    }
    
    initializer = DatabaseInitializer(conn_params=conn_params)
    success = initializer.initialize()
    
    if success:
        print("✅ Banco de dados pronto!")
    else:
        print("❌ Erro ao preparar banco de dados")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====== Executar Loader ======
print("\n" + "="*50)
print("📥 INICIANDO LOADER")
print("="*50 + "\n")

try:
    result = subprocess.run(
        [sys.executable, '/app/script/src/auto_loader.py'],
        cwd='/app'
    )
    sys.exit(result.returncode)
    
except KeyboardInterrupt:
    print("\n\n📍 Loader interrompido pelo usuário")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Erro ao executar loader: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
