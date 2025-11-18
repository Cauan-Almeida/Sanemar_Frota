"""
Script para listar todos os registros de hoje e verificar horários
"""

import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import initialize_firebase

BRAZIL_TZ = timezone(timedelta(hours=-3))

def listar_registros_hoje():
    result = initialize_firebase()
    
    if isinstance(result, tuple):
        db, _ = result
    else:
        db = result
    
    if not db:
        print("❌ Erro: não foi possível conectar ao Firebase")
        return
    
    # Busca registros de hoje
    hoje_local = datetime.now(BRAZIL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    hoje_utc = hoje_local.astimezone(timezone.utc)
    amanha_utc = hoje_utc + timedelta(days=1)
    
    print(f"🔍 Buscando registros de hoje ({hoje_local.strftime('%d/%m/%Y')})")
    print(f"   Período UTC: {hoje_utc} até {amanha_utc}\n")
    
    saidas_ref = db.collection('saidas').where('timestampSaida', '>=', hoje_utc).where('timestampSaida', '<', amanha_utc).stream()
    
    registros = []
    for doc in saidas_ref:
        data = doc.to_dict()
        registros.append({
            'id': doc.id,
            'veiculo': data.get('veiculo'),
            'motorista': data.get('motorista'),
            'solicitante': data.get('solicitante'),
            'trajeto': data.get('trajeto'),
            'status': data.get('status'),
            'timestampSaida': data.get('timestampSaida'),
            'timestampChegada': data.get('timestampChegada')
        })
    
    if not registros:
        print("❌ Nenhum registro encontrado para hoje")
        return
    
    print(f"✅ Encontrados {len(registros)} registros\n")
    print("=" * 100)
    
    for i, reg in enumerate(registros, 1):
        ts_saida = reg['timestampSaida']
        ts_chegada = reg['timestampChegada']
        
        # Converte timestamps
        if hasattr(ts_saida, 'seconds'):
            dt_saida_utc = datetime.fromtimestamp(ts_saida.seconds, tz=timezone.utc)
        else:
            dt_saida_utc = ts_saida
        
        dt_saida_local = dt_saida_utc.astimezone(BRAZIL_TZ)
        
        if ts_chegada:
            if hasattr(ts_chegada, 'seconds'):
                dt_chegada_utc = datetime.fromtimestamp(ts_chegada.seconds, tz=timezone.utc)
            else:
                dt_chegada_utc = ts_chegada
            dt_chegada_local = dt_chegada_utc.astimezone(BRAZIL_TZ)
            chegada_str = dt_chegada_local.strftime('%d/%m/%Y %H:%M')
        else:
            chegada_str = '-'
        
        print(f"\n{i}. {reg['veiculo']} - {reg['motorista']}")
        print(f"   Status: {reg['status']}")
        print(f"   Solicitante: {reg['solicitante']}")
        print(f"   Trajeto: {reg['trajeto']}")
        print(f"   Saída UTC: {dt_saida_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Saída Local: {dt_saida_local.strftime('%d/%m/%Y %H:%M')}")
        print(f"   Chegada Local: {chegada_str}")
        print(f"   ID: {reg['id']}")
    
    print("\n" + "=" * 100)

if __name__ == '__main__':
    listar_registros_hoje()
