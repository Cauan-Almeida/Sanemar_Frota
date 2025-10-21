"""Diagnóstico: encontrar registros em 'saidas' onde motorista/solicitante parecem trocados

Critério (heurístico):
- motorista tem apenas 1 palavra (possível primeiro nome) E solicitante tem 1 palavra (possível sobrenome)
- ou solicitante parece ser um nome curto (<= 2 palavras) que também pode ser parte do motorista

Este script só lista registros suspeitos (dry-run). Não aplica mudanças.

Uso:
    python scripts\find_mismatched_saidas.py --limit 200

Requer credenciais do Google Cloud configuradas no ambiente.
"""
from google.cloud import firestore
from pprint import pprint
import argparse


def suspect(motorista, solicitante):
    if not motorista or not solicitante:
        return False
    m_parts = motorista.strip().split()
    s_parts = solicitante.strip().split()
    # heurística simples: motorista com 1 palavra e solicitante com 1 palavra
    if len(m_parts) == 1 and len(s_parts) == 1:
        # se ambos curtos, marcar como suspeito
        return True
    # outro caso: solicitante muito curto (1-2 palavras) e motorista tem 2+ palavras but solicitante matches last word
    if len(s_parts) <= 2 and len(m_parts) >= 2:
        # se o último sobrenome do motorista estiver sozinho no solicitante, suspeito
        if s_parts[-1].lower() == m_parts[-1].lower():
            return True
    return False


def main(limit=200):
    db = firestore.Client()
    saidas_ref = db.collection('saidas').order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(limit)
    docs = list(saidas_ref.stream())
    print(f"Analisando {len(docs)} registros (mais recentes)...\n")
    suspects = []
    for doc in docs:
        d = doc.to_dict()
        motorista = d.get('motorista', '')
        solicitante = d.get('solicitante', '')
        if suspect(motorista, solicitante):
            suspects.append((doc.id, d))

    print(f"Encontrados {len(suspects)} registros suspeitos:\n")
    for docid, d in suspects:
        print(f"ID: {docid}")
        pprint(d)
        print("---\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=200)
    args = parser.parse_args()
    main(limit=args.limit)
