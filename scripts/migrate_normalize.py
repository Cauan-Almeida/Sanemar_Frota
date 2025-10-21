"""Script de migração para normalizar coleções Firestore:
- Placas: uppercase
- Motoristas: Title Case

Funcionalidades:
- --dry-run : mostra o que seria feito
- --apply : aplica as mudanças (mescla documentos duplicados)

AVISO: Execute com cuidado e faça backup do Firestore antes de usar --apply.
"""
import argparse
from google.cloud import firestore
from collections import defaultdict


def title_case(s):
    return ' '.join([w.capitalize() for w in s.split()]) if s else s


def normalize_plate(p):
    if not p:
        return p
    # remove espaços, traços e caracteres não alfanuméricos, manter letras e números
    import re
    cleaned = re.sub(r'[^0-9A-Za-z]', '', p)
    return cleaned.upper()


def migrate_veiculos(db, dry_run=True):
    veiculos_ref = db.collection('veiculos')
    docs = list(veiculos_ref.stream())
    groups = defaultdict(list)
    for doc in docs:
        data = doc.to_dict()
        placa = normalize_plate(data.get('placa') or '')
        if not placa:
            continue
        groups[placa].append((doc.id, data))

    actions = []
    for placa, items in groups.items():
        if len(items) > 1:
            # escolher dataCadastro mais antiga como a que preservamos
            items_sorted = sorted(items, key=lambda x: x[1].get('dataCadastro') or 0)
            keeper_id, keeper_data = items_sorted[0]
            merged = keeper_data.copy()
            merged['placa'] = placa
            # buscamos campos adicionais em outros docs
            for docid, data in items_sorted[1:]:
                # copiar campos não existentes
                for k, v in data.items():
                    if k not in merged or not merged.get(k):
                        merged[k] = v
            actions.append((placa, keeper_id, [d[0] for d in items_sorted[1:]], merged))

    if dry_run:
        print('VEICULOS - Dry run report')
        for placa, keeper, to_delete, merged in actions:
            print(f'Placa {placa}: manter {keeper}, deletar {to_delete}')
    else:
        print('Applying veiculos migration...')
        for placa, keeper, to_delete, merged in actions:
            print(f'Updating {keeper} -> placa {placa}')
            veiculos_ref.document(keeper).set(merged, merge=True)
            for delid in to_delete:
                if delid != keeper:
                    print(f'Deleting duplicate {delid}')
                    veiculos_ref.document(delid).delete()


def migrate_motoristas(db, dry_run=True):
    motoristas_ref = db.collection('motoristas')
    docs = list(motoristas_ref.stream())
    groups = defaultdict(list)
    for doc in docs:
        data = doc.to_dict()
        nome = title_case((data.get('nome') or '').strip())
        if not nome:
            continue
        groups[nome].append((doc.id, data))

    actions = []
    for nome, items in groups.items():
        if len(items) > 1:
            items_sorted = sorted(items, key=lambda x: x[1].get('dataCadastro') or 0)
            keeper_id, keeper_data = items_sorted[0]
            merged = keeper_data.copy()
            merged['nome'] = nome
            for docid, data in items_sorted[1:]:
                for k, v in data.items():
                    if k not in merged or not merged.get(k):
                        merged[k] = v
            actions.append((nome, keeper_id, [d[0] for d in items_sorted[1:]], merged))

    if dry_run:
        print('MOTORISTAS - Dry run report')
        for nome, keeper, to_delete, merged in actions:
            print(f'Nome {nome}: manter {keeper}, deletar {to_delete}')
    else:
        print('Applying motoristas migration...')
        for nome, keeper, to_delete, merged in actions:
            print(f'Updating {keeper} -> nome {nome}')
            motoristas_ref.document(keeper).set(merged, merge=True)
            for delid in to_delete:
                if delid != keeper:
                    print(f'Deleting duplicate {delid}')
                    motoristas_ref.document(delid).delete()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Aplica as mudanças')
    args = parser.parse_args()

    db = firestore.Client()

    dry_run = not args.apply
    migrate_veiculos(db, dry_run=dry_run)
    migrate_motoristas(db, dry_run=dry_run)

    if dry_run:
        print('\nDry run terminado. Revise antes de executar com --apply')
    else:
        print('\nMigração aplicada com sucesso.')

if __name__ == '__main__':
    main()
