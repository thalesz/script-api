#!/usr/bin/env python3
"""
Entrypoint do Docker do scraper: executa apenas a aplicação de download.
"""

import sys
import os
import subprocess
from pathlib import Path

# Mudar para o diretório da aplicação
os.chdir('/app')

# Adicionar script/src ao PYTHONPATH para imports
sys.path.insert(0, '/app/script/src')

# ====== PASSO: Executar Aplicação Principal ======
print("\n" + "="*50)
print("🚀 INICIANDO APLICAÇÃO")
print("="*50 + "\n")

try:
    # Executa main.py passando argumentos da linha de comando
    result = subprocess.run(
        [sys.executable, '/app/script/src/main.py'] + sys.argv[1:],
        cwd='/app'
    )
    sys.exit(result.returncode)
    
except KeyboardInterrupt:
    print("\n\n📍 Aplicação interrompida pelo usuário")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Erro ao executar aplicação: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
