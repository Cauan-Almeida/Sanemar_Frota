"""Script interativo para corrigir registros suspeitos na coleção 'saidas'.

Para cada documento marcado como suspeito, o script mostra os campos e oferece opções:
  [s] swap motorista <-> solicitante
  [t] swap horarioSaida <-> horarioChegada
  [m] mover campo (escolher origem/destino)
  [e] editar manualmente (digitar novos valores)
  [k] manter/skip
  [q] quit

Uso:
  python scripts\fix_mismatched_saidas.py --limit 200

ATENÇÃO: este script altera documentos no Firestore. Faça backup antes de usar --apply.
Por padrão ele pede confirmação para cada alteração.
"""
import argparse
from google.cloud import firestore
from pprint import pprint
from datetime import datetime


def suspect(motorista, solicitante):
    if not motorista or not solicitante:
        return False
    m_parts = motorista.strip().split()
    s_parts = solicitante.strip().split()
    if len(m_parts) == 1 and len(s_parts) == 1:
        return True
    if len(s_parts) <= 2 and len(m_parts) >= 2:
        if s_parts[-1].lower() == m_parts[-1].lower():
            return True
    return False


def is_iso_datetime(s):
    if not s or not isinstance(s, str):
        return False
    try:
        # tentativa simples de parse ISO ou dd/mm/YYYY
        datetime.fromisoformat(s)
        return True
    except Exception:
        try:
            datetime.strptime(s, '%d/%m/%Y %H:%M')
            return True
        except Exception:
            return False


def prompt_choice():
    print('[s] swap motorista <-> solicitante')
    print('[t] swap horarioSaida <-> horarioChegada')
    print('[m] mover campo (origem -> destino)')
    print('[e] editar manualmente')
    print('[k] pular/keep')
    print('[q] sair')
    c = input('Escolha ação: ').strip().lower()
    return c


def interactive_fix(doc_ref, data):
    print('\nDocumento ID:', doc_ref.id)
    pprint(data)
    while True:
        c = prompt_choice()
        if c == 's':
            new = data.copy()
            new['motorista'], new['solicitante'] = data.get('solicitante', ''), data.get('motorista', '')
            print('Proposta: swap motorista <-> solicitante ->')
            pprint(new)
            if input('Aplicar? (y/n) ').lower().startswith('y'):
                doc_ref.update({'motorista': new['motorista'], 'solicitante': new['solicitante']})
                print('Atualizado.')
            break
        elif c == 't':
            new = data.copy()
            new['horarioSaida'], new['horarioChegada'] = data.get('horarioChegada', ''), data.get('horarioSaida', '')
            new['timestampSaida'], new['timestampChegada'] = data.get('timestampChegada'), data.get('timestampSaida')
            print('Proposta: swap horarioSaida <-> horarioChegada ->')
            pprint(new)
            if input('Aplicar? (y/n) ').lower().startswith('y'):
                updates = {
                    'horarioSaida': new['horarioSaida'],
                    'horarioChegada': new['horarioChegada'],
                    'timestampSaida': new['timestampSaida'],
                    'timestampChegada': new['timestampChegada'],
                }
                doc_ref.update(updates)
                print('Atualizado.')
            break
        elif c == 'm':
            print('Campos disponíveis:', ', '.join(list(data.keys())))
            origem = input('Campo origem: ').strip()
            destino = input('Campo destino: ').strip()
            if origem not in data or destino not in data:
                print('Campo inválido.')
                continue
            new = data.copy()
            new[destino] = new.get(origem)
            new[origem] = ''
            print(f'Proposta: mover {origem} -> {destino}')
            pprint(new)
            if input('Aplicar? (y/n) ').lower().startswith('y'):
                doc_ref.update({destino: new[destino], origem: new[origem]})
                print('Atualizado.')
            break
        elif c == 'e':
            edits = {}
            for k in data.keys():
                val = input(f'{k} (enter para manter "{data.get(k)}"): ').strip()
                if val:
                    edits[k] = val
            if edits:
                print('Proposta de edição:')
                pprint(edits)
                if input('Aplicar? (y/n) ').lower().startswith('y'):
                    doc_ref.update(edits)
                    print('Atualizado.')
            break
        elif c == 'k':
            print('Pulando...')
            break
        elif c == 'q':
            print('Saindo.')
            return 'quit'
        else:
            print('Opção inválida.')
    return None


def main(limit=200):
    db = firestore.Client()
    saidas_ref = db.collection('saidas').order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(limit)
    docs = list(saidas_ref.stream())
    print(f'Analisando {len(docs)} registros (mais recentes)...\n')
    suspects = []
    for doc in docs:
        d = doc.to_dict()
        motorista = d.get('motorista', '')
        solicitante = d.get('solicitante', '')
        # heurística base: nomes curtos ou campos que parecem trocados
        if suspect(motorista, solicitante):
            suspects.append((doc, d))
            continue
        # heurística adicional: se horarioSaida não é datetime e parece nome, marcar
        hs = d.get('horarioSaida')
        ts = d.get('timestampSaida')
        if hs and not is_iso_datetime(hs) and isinstance(hs, str) and len(hs) < 40:
            # parece ter texto não datetime (ex: 'Max')
            suspects.append((doc, d))

    print(f'Encontrados {len(suspects)} registros suspeitos:\n')
    for doc_ref, data in suspects:
        res = interactive_fix(doc_ref.reference, data)
        if res == 'quit':
            print('Interrompendo por solicitação do usuário.')
            break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=200)
    args = parser.parse_args()
    main(limit=args.limit)
