# -*- coding: utf-8 -*-
"""
Script simplificado para rodar o servidor em desenvolvimento
Usa Flask diretamente ao invés de Waitress para melhor debug
"""
import sys
import os

# Força UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Importa módulos necessários antes de executar o app
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask

# Agora executa o app.py modificando para usar Flask ao invés de Waitress
if __name__ == '__main__':
    # Lê o conteúdo do app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitui serve() por app.run()
    content = content.replace(
        "serve(app, host='0.0.0.0', port=5000, threads=8, channel_timeout=60)",
        "app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)"
    )
    
    # Executa
    exec(compile(content, 'app.py', 'exec'))
