#!/usr/bin/env python3
"""
Script para gerar hash de senha para o sistema de usuários.
Use para criar o primeiro usuário admin no Firestore.
"""

import sys

def generate_hash(password):
    """Gera hash bcrypt de uma senha"""
    try:
        import bcrypt
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except ImportError:
        print("⚠️  bcrypt não instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "bcrypt"])
        import bcrypt
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

if __name__ == '__main__':
    print("=" * 60)
    print("🔐 GERADOR DE HASH DE SENHA - Sistema Frota Sanemar")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        # Senha passada como argumento
        password = sys.argv[1]
    else:
        # Solicita senha ao usuário
        import getpass
        password = getpass.getpass("Digite a senha para gerar hash: ")
    
    if not password:
        print("❌ Senha vazia!")
        sys.exit(1)
    
    print()
    print("⏳ Gerando hash...")
    hashed = generate_hash(password)
    
    print()
    print("✅ Hash gerado com sucesso!")
    print()
    print("=" * 60)
    print("COPIE O HASH ABAIXO:")
    print("=" * 60)
    print(hashed)
    print("=" * 60)
    print()
    print("📋 Instruções:")
    print()
    print("1. Acesse Firebase Console → Firestore Database")
    print("2. Crie a coleção 'usuarios'")
    print("3. Adicione um documento com:")
    print()
    print("   {")
    print(f'     "username": "admin",')
    print(f'     "password_hash": "{hashed}",')
    print(f'     "nome_completo": "Administrador",')
    print(f'     "tipo": "admin",')
    print(f'     "ativo": true,')
    print(f'     "data_criacao": (timestamp atual)')
    print("   }")
    print()
    print("4. Faça login com username='admin' e a senha que você digitou")
    print()
    print("=" * 60)
