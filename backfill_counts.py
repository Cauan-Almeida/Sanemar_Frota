# backfill_counts.py
import os
from google.cloud import firestore
from collections import Counter
from dotenv import load_dotenv
from tqdm import tqdm # Biblioteca para barra de progresso

# Carrega suas credenciais
load_dotenv()
db = firestore.Client()
print("Conectado ao Firestore.")

# 1. Contar todas as viagens da coleção 'saidas'
print("Lendo toda a coleção 'saidas'. Isso vai custar cota e pode demorar...")
saidas_docs = list(db.collection('saidas').stream())

motorista_counts = Counter()
veiculo_counts = Counter()

for doc in tqdm(saidas_docs, desc="Contando viagens"):
    data = doc.to_dict()
    if data.get('motorista'):
        motorista_counts[data['motorista']] += 1
    if data.get('veiculo'):
        veiculo_counts[data['veiculo']] += 1

print(f"Contagem concluída. {len(motorista_counts)} motoristas e {len(veiculo_counts)} veiculos encontrados.")

# 2. Atualizar a coleção 'motoristas'
print("\nAtualizando contadores de motoristas...")
motoristas_ref = db.collection('motoristas')
batch = db.batch()
motoristas_processados = 0

for nome, total in tqdm(motorista_counts.items(), desc="Motoristas"):
    q = motoristas_ref.where('nome', '==', nome).limit(1).stream()
    doc_list = list(q)
    
    if doc_list:
        doc_ref = doc_list[0].reference
        batch.update(doc_ref, {'viagens_totais': total})
    else:
        # Se o motorista não existir (caso raro), cria
        novo_doc_ref = motoristas_ref.document()
        batch.set(novo_doc_ref, {'nome': nome, 'viagens_totais': total, 'status': 'nao_credenciado'})
    
    motoristas_processados += 1
    if motoristas_processados % 400 == 0: # Envia o batch a cada 400 operações
        batch.commit()
        batch = db.batch()

batch.commit() # Envia o que sobrou

# 3. Atualizar a coleção 'veiculos'
print("\nAtualizando contadores de veiculos...")
veiculos_ref = db.collection('veiculos')
batch = db.batch()
veiculos_processados = 0

for placa, total in tqdm(veiculo_counts.items(), desc="Veículos"):
    q = veiculos_ref.where('placa', '==', placa).limit(1).stream()
    doc_list = list(q)
    
    if doc_list:
        doc_ref = doc_list[0].reference
        batch.update(doc_ref, {'viagens_totais': total})
    else:
        # Se o veículo não existir, cria
        novo_doc_ref = veiculos_ref.document()
        batch.set(novo_doc_ref, {'placa': placa, 'viagens_totais': total})

    veiculos_processados += 1
    if veiculos_processados % 400 == 0:
        batch.commit()
        batch = db.batch()

batch.commit() # Envia o que sobrou

print("\n--- Backfill concluído com sucesso! ---")
print("Seus totais gerais agora estão corretos e seu dashboard está otimizado.")
