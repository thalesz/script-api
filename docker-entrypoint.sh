#!/bin/bash
# Entrypoint script: inicializa o banco e executa main.py

set -e  # Exit on error

echo "=== Docker Entrypoint ==="
echo "Inicializando banco de dados..."

# Executa inicialização do banco de dados
python script/src/init_db.py

if [ $? -eq 0 ]; then
    echo "Banco de dados inicializado com sucesso!"
    echo "Iniciando aplicação..."
    # Executa o script principal com os args passados
    exec python script/src/main.py "$@"
else
    echo "Falha na inicialização do banco de dados"
    exit 1
fi
