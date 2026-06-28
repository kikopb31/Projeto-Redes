import hashlib

def xor_distance(id1: str, id2: str) -> int:     
    h1 = int(hashlib.sha1(id1.encode()).hexdigest(), 16)
    h2 = int(hashlib.sha1(id2.encode()).hexdigest(), 16)
    return h1 ^ h2

# 1. Definir os IDs dos Jogadores
alvo = "TargetPlayer"
no_perto = "Player1"
no_longe = "Player99"

# 2. Calcular as distâncias
dist_perto = xor_distance(no_perto, alvo)
dist_longe = xor_distance(no_longe, alvo)

# 3. Mostrar os resultados em formato legível
print(f"--- TESTE DE DISTÂNCIA XOR ---")
print(f"Alvo da busca: '{alvo}'\n")

print(f"Nó A: '{no_perto}'")
print(f"  > Distância numérica: {dist_perto}")
print(f"  > Em binário (bites iniciais): {bin(dist_perto)[:30]}...")

print(f"\nNó B: '{no_longe}'")
print(f"  > Distância numérica: {dist_longe}")
print(f"  > Em binário (bites iniciais): {bin(dist_longe)[:30]}...")

print("\n--- CONCLUSÃO ---")
if dist_perto < dist_longe:
    print(f"O '{no_perto}' está MAIS PERTO de '{alvo}' do que o '{no_longe}'.")
else:
    print(f"O '{no_longe}' está MAIS PERTO de '{alvo}' do que o '{no_perto}'.")