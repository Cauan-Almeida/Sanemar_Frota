"""
Script para APAGAR TODOS OS DADOS do Firestore e Firebase Storage
⚠️ CUIDADO: Esta ação é IRREVERSÍVEL!
"""

from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, storage

# Inicializa Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('../firebase-credentials.json')
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'frota-sanemar.firebasestorage.app'
    })

db = firestore.Client()
bucket = storage.bucket()

def delete_collection(collection_name, batch_size=100):
    """Deleta todos os documentos de uma coleção"""
    coll_ref = db.collection(collection_name)
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted += 1
        print(f"  ✅ Deletado: {doc.id}")

    if deleted >= batch_size:
        # Recursivamente deleta mais se houver
        return delete_collection(collection_name, batch_size)
    else:
        return deleted

def delete_storage_folder(folder_path):
    """Deleta todos os arquivos de uma pasta no Storage"""
    blobs = bucket.list_blobs(prefix=folder_path)
    deleted = 0
    
    for blob in blobs:
        blob.delete()
        deleted += 1
        print(f"  🗑️ Arquivo deletado: {blob.name}")
    
    return deleted

def main():
    print("=" * 60)
    print("⚠️  ATENÇÃO: LIMPEZA TOTAL DO BANCO DE DADOS ⚠️")
    print("=" * 60)
    print("\nEste script vai APAGAR PERMANENTEMENTE:")
    print("  • Todas as saídas/viagens")
    print("  • Todos os motoristas")
    print("  • Todos os veículos")
    print("  • Todos os abastecimentos")
    print("  • Todas as revisões")
    print("  • Todos os arquivos no Storage (CNHs, documentos, etc)")
    print("\n⚠️  ESTA AÇÃO NÃO PODE SER DESFEITA! ⚠️\n")
    
    confirmacao1 = input("Digite 'CONFIRMO' para continuar: ").strip()
    if confirmacao1 != "CONFIRMO":
        print("❌ Operação cancelada.")
        return
    
    confirmacao2 = input("Digite 'APAGAR TUDO' para confirmar novamente: ").strip()
    if confirmacao2 != "APAGAR TUDO":
        print("❌ Operação cancelada.")
        return
    
    print("\n🔥 Iniciando limpeza...\n")
    
    # 1. Apaga Firestore Collections
    collections = [
        'saidas',
        'motoristas', 
        'veiculos',
        'refuels',
        'revisoes',
        'km_mensal',
        'multas'
    ]
    
    for coll_name in collections:
        print(f"\n📂 Limpando coleção '{coll_name}'...")
        try:
            total = delete_collection(coll_name)
            print(f"✅ Total deletado em '{coll_name}': {total} documentos")
        except Exception as e:
            print(f"❌ Erro ao limpar '{coll_name}': {e}")
    
    # 2. Apaga Firebase Storage
    storage_folders = [
        'cnh/',          # CNHs dos motoristas
        'documentos/',   # Documentos dos veículos
        'multas/',       # Fotos de multas
        'revisoes/'      # Comprovantes de revisões
    ]
    
    print("\n\n📦 Limpando Firebase Storage...")
    for folder in storage_folders:
        print(f"\n📁 Limpando pasta '{folder}'...")
        try:
            total = delete_storage_folder(folder)
            print(f"✅ Total deletado em '{folder}': {total} arquivos")
        except Exception as e:
            print(f"❌ Erro ao limpar '{folder}': {e}")
    
    print("\n" + "=" * 60)
    print("✅ LIMPEZA CONCLUÍDA!")
    print("=" * 60)
    print("\n💡 O banco de dados está limpo e pronto para produção.")

if __name__ == "__main__":
    main()
