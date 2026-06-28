#!/bin/bash

if [ ! -d "venv" ]; then
    echo "A criar ambiente virtual..."
    python3 -m venv venv
else
    echo "Ambiente virtual já existe, a reutilizar..."
fi

echo "A instalar dependências..."
venv/bin/pip install -r requirements.txt

echo "A gerar ficheiros proto..."
venv/bin/python3 -m grpc_tools.protoc \
    -I./src/proto \
    --python_out=./src/proto \
    --grpc_python_out=./src/proto \
    ./src/proto/game.proto

echo "A corrigir imports do proto..."
sed -i 's/^import game_pb2/from proto import game_pb2/' src/proto/game_pb2_grpc.py

echo ""
echo "Setup completo!"
echo "Agora corre:"
echo "  source venv/bin/activate"
echo "  python3 src/main.py"