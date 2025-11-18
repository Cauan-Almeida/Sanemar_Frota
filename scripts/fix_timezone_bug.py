"""
Script para corrigir registros com horários bugados por problema de timezone.

O bug causava conversão UTC dupla ao editar registros:
- Input datetime-local era interpretado como UTC
- toISOString() convertia novamente
- Resultado: horários 3 horas adiantados

Este script identifica e corrige esses registros.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import initialize_firebase

# Timezone do Brasil
BRAZIL_TZ = timezone(timedelta(hours=-3))

def corrigir_timezone_bugado():
    """Corrige registros com horários bugados"""
    result = initialize_firebase()
    
    # initialize_firebase retorna tuple (db, storage_bucket) ou apenas db
    if isinstance(result, tuple):
        db, _ = result
    else:
        db = result
    
    if not db:
        print("❌ Erro: não foi possível conectar ao Firebase")
        return
    
    print("🔍 Buscando registros potencialmente bugados...\n")
    
    # Busca todos os registros dos últimos 30 dias
    hoje = datetime.now(timezone.utc)
    mes_atras = hoje - timedelta(days=30)
    
    saidas_ref = db.collection('saidas').where('timestampSaida', '>=', mes_atras).stream()
    
    registros_analisados = 0
    registros_suspeitos = []
    
    for doc in saidas_ref:
        data = doc.to_dict()
        registros_analisados += 1
        
        # Verifica se tem timestampSaida
        if not data.get('timestampSaida'):
            continue
        
        ts_saida = data['timestampSaida']
        ts_chegada = data.get('timestampChegada')
        
        # Converte para datetime
        if hasattr(ts_saida, 'seconds'):
            dt_saida = datetime.fromtimestamp(ts_saida.seconds, tz=timezone.utc)
        else:
            dt_saida = ts_saida
        
        # Converte para horário local para análise
        dt_saida_local = dt_saida.astimezone(BRAZIL_TZ)
        hora_saida = dt_saida_local.hour
        
        # Horários suspeitos: madrugada (0-5h) ou muito tarde (22-23h)
        # Esses são incomuns para veículos de trabalho
        if hora_saida <= 5 or hora_saida >= 22:
            registros_suspeitos.append({
                'id': doc.id,
                'veiculo': data.get('veiculo'),
                'motorista': data.get('motorista'),
                'trajeto': data.get('trajeto'),
                'saida_utc': dt_saida,
                'saida_local': dt_saida_local,
                'hora': hora_saida,
                'data': data
            })
    
    print(f"📊 Registros analisados: {registros_analisados}")
    print(f"⚠️  Registros suspeitos (horários incomuns): {len(registros_suspeitos)}\n")
    
    if not registros_suspeitos:
        print("✅ Nenhum registro suspeito encontrado!")
        return
    
    print("=" * 80)
    print("REGISTROS COM HORÁRIOS SUSPEITOS:")
    print("=" * 80)
    
    for i, reg in enumerate(registros_suspeitos, 1):
        print(f"\n{i}. ID: {reg['id']}")
        print(f"   Veículo: {reg['veiculo']}")
        print(f"   Motorista: {reg['motorista']}")
        print(f"   Trajeto: {reg['trajeto']}")
        print(f"   Horário UTC: {reg['saida_utc'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Horário Local (atual): {reg['saida_local'].strftime('%Y-%m-%d %H:%M:%S')} ({reg['hora']}h)")
        
        # Calcula horário corrigido (subtrai 3 horas do UTC)
        dt_corrigido_utc = reg['saida_utc'] - timedelta(hours=3)
        dt_corrigido_local = dt_corrigido_utc.astimezone(BRAZIL_TZ)
        print(f"   Horário Corrigido (sugerido): {dt_corrigido_local.strftime('%Y-%m-%d %H:%M:%S')} ({dt_corrigido_local.hour}h)")
    
    print("\n" + "=" * 80)
    resposta = input("\n🔧 Deseja corrigir TODOS esses registros? (sim/não): ").strip().lower()
    
    if resposta != 'sim':
        print("❌ Operação cancelada.")
        return
    
    print("\n🔄 Corrigindo registros...\n")
    
    corrigidos = 0
    for reg in registros_suspeitos:
        try:
            # Calcula horário corrigido (subtrai 3 horas)
            dt_corrigido_utc = reg['saida_utc'] - timedelta(hours=3)
            
            # Atualiza no Firestore
            doc_ref = db.collection('saidas').document(reg['id'])
            doc_ref.update({
                'timestampSaida': dt_corrigido_utc
            })
            
            corrigidos += 1
            print(f"✅ {reg['veiculo']} - {reg['motorista']}: "
                  f"{reg['saida_local'].strftime('%H:%M')} → "
                  f"{dt_corrigido_utc.astimezone(BRAZIL_TZ).strftime('%H:%M')}")
            
        except Exception as e:
            print(f"❌ Erro ao corrigir {reg['id']}: {e}")
    
    print(f"\n✅ Correção concluída! {corrigidos}/{len(registros_suspeitos)} registros corrigidos.")
    print("\n💡 IMPORTANTE: Esses registros foram identificados por terem horários incomuns.")
    print("   Verifique manualmente se as correções estão corretas no sistema.")


if __name__ == '__main__':
    print("=" * 80)
    print("CORREÇÃO DE BUG DE TIMEZONE - Registros de Saída")
    print("=" * 80)
    print("\nEste script corrige registros que foram editados com o bug de timezone.")
    print("Bug: conversão UTC dupla causava horários 3 horas adiantados.\n")
    
    corrigir_timezone_bugado()
