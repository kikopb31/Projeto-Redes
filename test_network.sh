#!/bin/bash

# Terminar todos os nós se o script for interrompido (Ctrl+C)
trap "echo 'A fechar todos os nós...'; kill 0" EXIT

echo "=== A INICIAR SIMULAÇÃO DE REDE P2P LOCA === "

# 1. Iniciar o Nó A (Bootstrap Node) na porta 50051
echo "A lançar o Nó A (Bootstrap)..."
python3 src/main.py A 127.0.0.1 50051 n &
sleep 2 # Espera 2 segundos para o servidor gRPC arrancar

# 2. Iniciar o Nó B e conectar ao Nó A
echo "A lançar o Nó B (Liga-se ao Nó A)..."
python3 src/main.py B 127.0.0.1 50052 y 127.0.0.1 50051 &
sleep 1

# 3. Iniciar o Nó C e conectar ao Nó A (ou B)
echo "A lançar o Nó C (Liga-se ao Nó A)..."
python3 src/main.py C 127.0.0.1 50053 y 127.0.0.1 50051 &
sleep 1

echo "=== REDE EM EXECUÇÃO ==="
echo "Podes ver os logs acima. Prime [Ctrl+C] para terminar todos os nós simultaneamente."

# Manter o script ativo para os processos secundários continuarem a correr
wait