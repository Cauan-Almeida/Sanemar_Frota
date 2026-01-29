import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, session, send_file
from functools import wraps
from google.cloud import firestore, storage
from google.cloud.firestore_v1.base_query import And
import firebase_admin
from firebase_admin import credentials, storage as firebase_storage
from dotenv import load_dotenv
from collections import Counter
import io
import bcrypt
from io import BytesIO

# --- Funções Auxiliares ---
def serialize_doc(doc):
    """Converte datetimes em um documento para strings ISO 8601."""
    if not doc:
        return None
    serialized = doc.copy()
    for key, value in serialized.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
    return serialized


def normalize_plate(plate: str) -> str:
    """Remove espaços, traços e caracteres não alfanuméricos e converte para maiúsculas."""
    if not plate:
        return plate
    cleaned = re.sub(r'[^0-9A-Za-z]', '', plate)
    return cleaned.upper()

# Define o fuso horário local
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")

# Função para invalidar cache do histórico (chamada em saídas/chegadas/cancelamentos)
def invalidate_historico_cache():
    """Limpa todo o cache do histórico quando há mudanças"""
    global historico_cache
    historico_cache.clear()
    print('[DELETE] Cache do histórico invalidado (saída/chegada/cancelamento)')

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o Flask App
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'frota-sanemar-secret-key-2025-super-segura')

# Credenciais de autenticação
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'sanemar2025')
HISTORICO_USERNAME = os.getenv('HISTORICO_USERNAME', 'historico')
HISTORICO_PASSWORD = os.getenv('HISTORICO_PASSWORD', 'historico123')

def requires_auth(f):
    """Decorator para exigir autenticação por sessão (ADMIN)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in') or session.get('user_type') != 'admin':
            # Se for rota API, retorna JSON 401 ao invés de redirecionar
            if request.path.startswith('/api/'):
                return jsonify({"error": "Autenticação necessária", "authenticated": False}), 401
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated

def requires_auth_historico(f):
    """Decorator para exigir autenticação por sessão (HISTÓRICO)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in') or session.get('user_type') not in ['admin', 'historico']:
            # Se for rota API, retorna JSON 401 ao invés de redirecionar
            if request.path.startswith('/api/'):
                return jsonify({"error": "Autenticação necessária", "authenticated": False}), 401
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated

# Inicializa Firebase com suporte para variável de ambiente (produção) ou arquivo local (dev)
import json
import tempfile

def initialize_firebase():
    """Inicializa Firebase Admin SDK e Firestore.
    - Produção (Render): Lê credenciais da variável GOOGLE_APPLICATION_CREDENTIALS_JSON
    - Desenvolvimento: Lê do arquivo firebase-credentials.json
    """
    try:
        # Tenta ler credenciais da variável de ambiente (PRODUÇÃO - Render)
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        
        if credentials_json:
            print("[CONFIG] Modo PRODUÇÃO: Lendo credenciais da variável de ambiente")
            # Parse das credenciais JSON
            credentials_dict = json.loads(credentials_json)
            
            # Cria objeto de credenciais do Google
            from google.oauth2 import service_account
            google_credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            
            # Inicializa Firebase Admin SDK
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'frota-sanemar.firebasestorage.app'
                })
            
            # Inicializa Firestore com as credenciais explícitas
            db = firestore.Client(credentials=google_credentials, project=credentials_dict['project_id'])
            bucket = firebase_storage.bucket()
            
            print("[OK] Firebase inicializado com sucesso (PRODUÇÃO)")
            return db, bucket
            
        else:
            print("[CONFIG] Modo DESENVOLVIMENTO: Lendo credenciais do arquivo local")
            # Modo desenvolvimento - lê do arquivo
            if not firebase_admin._apps:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'frota-sanemar.firebasestorage.app'
                })
            
            db = firestore.Client()
            bucket = firebase_storage.bucket()
            
            print("[OK] Firebase inicializado com sucesso (DESENVOLVIMENTO)")
            return db, bucket
            
    except Exception as e:
        print(f" Erro ao inicializar Firebase: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# Inicializa Firebase
db, bucket = initialize_firebase()

# ==========================================
# [CONFIG] SISTEMA DE MODO DE MANUTENÇÃO
# ==========================================

def is_maintenance_mode():
    """Verifica se o sistema está em modo de manutenção"""
    try:
        if os.path.exists('.maintenance'):
            with open('.maintenance', 'r', encoding='utf-8-sig') as f:  # utf-8-sig remove BOM automaticamente
                content = f.read().strip().lower()
                return content == 'on'
        return False
    except Exception as e:
        print(f"Erro ao verificar modo de manutenção: {e}")
        return False

@app.before_request
def check_maintenance():
    """Intercepta todas as requisições e redireciona para tela de manutenção se ativado"""
    # Permite acesso aos endpoints de controle de manutenção
    if request.path.startswith('/api/maintenance'):
        return None
    
    # Permite acesso à tela de manutenção
    if request.path == '/maintenance':
        return None
    
    # Permite acesso a assets estáticos
    if request.path.startswith('/static/'):
        return None
    
    # Se está em manutenção, redireciona para tela de manutenção
    if is_maintenance_mode():
        if request.path != '/maintenance':
            return redirect(url_for('maintenance_page'))
    
    return None

@app.route('/maintenance')
def maintenance_page():
    """Página de manutenção"""
    return render_template('maintenance.html')

# Endpoints para controlar o modo de manutenção via API
@app.route('/api/maintenance/on', methods=['POST'])
@requires_auth
def activate_maintenance():
    """Ativa o modo de manutenção"""
    try:
        with open('.maintenance', 'w') as f:
            f.write('on')
        return jsonify({"success": True, "message": "Modo de manutenção ATIVADO"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/maintenance/off', methods=['POST'])
def deactivate_maintenance():
    """Desativa o modo de manutenção (sem autenticação para poder reativar o sistema)"""
    try:
        # Remove o arquivo completamente para garantir desativação
        if os.path.exists('.maintenance'):
            os.remove('.maintenance')
        return jsonify({"success": True, "message": "Modo de manutenção DESATIVADO"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/maintenance/status', methods=['GET'])
def maintenance_status():
    """Verifica o status do modo de manutenção"""
    return jsonify({
        "maintenance_mode": is_maintenance_mode(),
        "message": "Sistema em manutenção" if is_maintenance_mode() else "Sistema operacional"
    }), 200

# Flag global para indicar que o Firestore está indisponível (por ex. quota excedida)
FIRESTORE_AVAILABLE = True

# ==========================================
# [SAVE] SISTEMA DE BACKUP DE ARQUIVOS
# ==========================================
# Move arquivos para pasta de backup ao invés de deletar

def backup_storage_file(blob_path, reason='delete'):
    """
    Move arquivo do Storage para pasta de backup ao invés de deletar.
    
    Args:
        blob_path (str): Caminho do arquivo no Storage (ex: motoristas/abc123/cnh_123.pdf)
        reason (str): Motivo do backup ('delete', 'replace', etc.)
    
    Returns:
        str: URL do arquivo no backup, ou None se falhar
    """
    if not bucket:
        print(f" Backup: Storage indisponível")
        return None
    
    try:
        # Blob original
        source_blob = bucket.blob(blob_path)
        
        # Verifica se arquivo existe
        if not source_blob.exists():
            print(f" Arquivo não existe: {blob_path}")
            return None
        
        # Cria nome do backup com timestamp
        timestamp = datetime.now(LOCAL_TZ).strftime('%Y%m%d_%H%M%S')
        backup_path = f"deleted_backups/{timestamp}_{reason}/{blob_path}"
        
        # Copia arquivo para backup
        backup_blob = bucket.blob(backup_path)
        backup_blob.rewrite(source_blob)
        
        # Torna backup público (opcional)
        backup_blob.make_public()
        backup_url = backup_blob.public_url
        
        print(f"[OK] Arquivo copiado para backup: {backup_path}")
        
        # Agora pode deletar o original com segurança
        source_blob.delete()
        print(f"[DELETE] Original deletado: {blob_path}")
        
        return backup_url
        
    except Exception as e:
        print(f" Erro ao fazer backup de {blob_path}: {e}")
        return None

# ==========================================
# [SEARCH] SISTEMA DE AUDITORIA
# ==========================================
# Registra TODAS as ações no banco de dados:
# - Quem fez (usuário)
# - O que fez (action: create, update, delete)
# - Quando (timestamp)
# - Onde (coleção e documento)
# - Dados antes e depois (para rollback)

def log_audit(action, collection_name, doc_id, old_data=None, new_data=None, user=None):
    """
    Registra uma ação de auditoria no Firestore.
    
    Args:
        action (str): 'create', 'update', 'delete'
        collection_name (str): Nome da coleção afetada
        doc_id (str): ID do documento afetado
        old_data (dict): Dados antes da modificação (para update/delete)
        new_data (dict): Dados depois da modificação (para create/update)
        user (str): Usuário que executou a ação (pega da sessão se None)
    """
    if not db:
        print(f" Auditoria: Firestore indisponível, log não registrado")
        return
    
    try:
        # Pega usuário da sessão se não fornecido
        if user is None:
            user = session.get('username', 'sistema')
        
        # Timestamp atual
        now = datetime.now(LOCAL_TZ)
        
        # Prepara o documento de auditoria
        audit_doc = {
            'action': action,  # create, update, delete
            'collection': collection_name,
            'document_id': doc_id,
            'user': user,
            'timestamp': now,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        # Adiciona dados antigos/novos se fornecidos
        if old_data:
            # Remove campos sensíveis se necessário
            audit_doc['old_data'] = serialize_doc(old_data)
        
        if new_data:
            audit_doc['new_data'] = serialize_doc(new_data)
        
        # Salva no Firestore
        db.collection('audit_log').add(audit_doc)
        
        print(f"[OK] Auditoria: {action.upper()} em {collection_name}/{doc_id} por {user}")
    
    except Exception as e:
        # Não deve interromper a operação principal
        print(f" Erro ao registrar auditoria: {e}")
        import traceback
        traceback.print_exc()

# ==========================================
#  SISTEMA DE GERENCIAMENTO DE USUÁRIOS
# ==========================================

def hash_password(password):
    """Gera hash bcrypt de uma senha"""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except:
        # Fallback caso bcrypt não esteja instalado
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verifica se senha corresponde ao hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        # Fallback para SHA256
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

def get_user_by_username(username):
    """Busca usuário no Firestore por username"""
    if not db:
        return None
    try:
        users_ref = db.collection('usuarios')
        query = users_ref.where(filter=firestore.FieldFilter('username', '==', username)).where(filter=firestore.FieldFilter('ativo', '==', True)).limit(1).get()
        if query:
            user_doc = query[0]
            user_data = user_doc.to_dict()
            user_data['id'] = user_doc.id
            return user_data
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None

# Flag global para indicar que o Firestore está indisponível (por ex. quota excedida)
FIRESTORE_AVAILABLE = True

def mark_firestore_unavailable_if_quota(e):
    """Marca FIRESTORE_AVAILABLE = False se detectarmos erro de quota/excesso de uso.
    Retorna True se marcou como indisponível."""
    global FIRESTORE_AVAILABLE
    try:
        msg = str(e).lower()
        if 'quota' in msg or 'quota exceeded' in msg or '429' in msg:
            FIRESTORE_AVAILABLE = False
            print('Firestore marcado como indisponível devido a erro de quota/excesso de uso.')
            return True
    except Exception:
        pass
    return False

@app.template_filter('formatar_data')
def formatar_data_filter(iso_string):
    """Formata uma string ISO 8601 para DD/MM/YYYY HH:mm no fuso horário local."""
    if not iso_string:
        return '-'
    try:
        # Garante que a string ISO seja compatível com fromisoformat
        if isinstance(iso_string, str) and iso_string.endswith('Z'):
            iso_string = iso_string.replace('Z', '+00:00')
        
        dt_utc = datetime.fromisoformat(iso_string)
        
        # Se o datetime não tiver fuso horário, assume UTC
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            
        dt_local = dt_utc.astimezone(LOCAL_TZ)
        return dt_local.strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError):
        return iso_string

# --- Rota Principal para servir a página do motorista ---
@app.route('/')
def index():
    # Se o Firestore estiver indisponível (quota excedida), exibimos página de manutenção
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503

    veiculos = []
    veiculos_completos = []  # Lista com objetos {placa, modelo}
    veiculos_agrupados = {
        'Base de Itaipuaçu': [],
        'Base ETE de Araçatiba': [],
        'Sede Sanemar': [],
        'Vans': [],
        'Comercial': [],
        'Outros': []
    }
    motoristas = []
    if db:
        try:
            veiculos_ref = db.collection('veiculos').stream()
            for doc in veiculos_ref:
                data = doc.to_dict()
                placa = data.get('placa')
                if not placa:
                    continue
                
                # Verifica se veículo está visível (padrão: True se campo não existir)
                visivel = data.get('visivel_para_motoristas', True)
                
                if visivel:
                    veiculos.append(placa)
                    veiculo_obj = {
                        'placa': placa,
                        'modelo': data.get('modelo', '')
                    }
                    veiculos_completos.append(veiculo_obj)
                    
                    # Agrupa por categoria
                    categoria = data.get('categoria', 'Outros')
                    if categoria in veiculos_agrupados:
                        veiculos_agrupados[categoria].append(veiculo_obj)
                    else:
                        veiculos_agrupados['Outros'].append(veiculo_obj)
            
            # Ordena cada grupo
            veiculos.sort()
            veiculos_completos.sort(key=lambda x: x['placa'])
            for categoria in veiculos_agrupados:
                veiculos_agrupados[categoria].sort(key=lambda x: x['placa'])

            # Agrupa motoristas por seção (somente visíveis)
            motoristas_agrupados = {
                'Base de Itaipuaçu': [],
                'Base ETE de Araçatiba': [],
                'Sede Sanemar': [],
                'Van': [],
                'Outros': []
            }
            motoristas_ref = db.collection('motoristas').stream()
            motoristas = []
            for doc in motoristas_ref:
                data = doc.to_dict()
                nome = data.get('nome')
                if nome:
                    # Verifica visibilidade (padrão: True)
                    visivel = data.get('visivel_para_motoristas', True)
                    if visivel:
                        motoristas.append(nome)
                        secao = data.get('secao', 'Outros')
                        if secao in motoristas_agrupados:
                            motoristas_agrupados[secao].append(nome)
                        else:
                            motoristas_agrupados['Outros'].append(nome)
            
            motoristas.sort()
            for secao in motoristas_agrupados:
                motoristas_agrupados[secao].sort()

        except Exception as e:
            mark_firestore_unavailable_if_quota(e)
            print(f"Erro ao buscar veículos ou motoristas: {e}")
            return render_template('maintenance.html'), 503

    return render_template('index.html', 
                         veiculos=veiculos, 
                         veiculos_completos=veiculos_completos, 
                         veiculos_agrupados=veiculos_agrupados,
                         motoristas=motoristas,
                         motoristas_agrupados=motoristas_agrupados)


# --- Rota para Service Worker ---
@app.route('/sw.js')
def service_worker():
    """Serve o service worker da raiz do projeto"""
    return send_file('sw.js', mimetype='application/javascript')


# --- Rotas de Autenticação ---
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Página de login bonita"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Tenta buscar usuário no Firestore primeiro
        user = get_user_by_username(username)
        
        if user and verify_password(password, user['password_hash']):
            # Usuário encontrado no Firestore
            session['logged_in'] = True
            session['user_type'] = user.get('tipo', 'operador')
            session['username'] = username
            session['nome_completo'] = user.get('nome_completo', username)
            session['user_id'] = user.get('id')
            
            # Registra login no audit_log
            log_audit('login', 'usuarios', user.get('id'), new_data={'username': username})
            
            # Redireciona conforme tipo de usuário
            if user.get('tipo') == 'admin':
                next_page = request.args.get('next') or url_for('dashboard')
            elif user.get('tipo') == 'historico':
                next_page = request.args.get('next') or url_for('historico_page')
            else:
                next_page = request.args.get('next') or url_for('index')
            
            return redirect(next_page)
        
        # Fallback: verifica credenciais antigas (variáveis de ambiente)
        # REMOVER após migrar todos os usuários para Firestore
        elif username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['user_type'] = 'admin'
            session['username'] = username
            next_page = request.args.get('next') or url_for('dashboard')
            return redirect(next_page)
        elif username == HISTORICO_USERNAME and password == HISTORICO_PASSWORD:
            session['logged_in'] = True
            session['user_type'] = 'historico'
            session['username'] = username
            next_page = request.args.get('next') or url_for('historico_page')
            return redirect(next_page)
        else:
            return render_template('login.html', error='Usuário ou senha incorretos')
    
    return render_template('login.html')


@app.route('/limpar-cache')
def limpar_cache():
    """Página para limpar cache do Service Worker"""
    return render_template('limpar-cache.html')


@app.route('/logout')
def logout():
    """Faz logout do usuário"""
    session.clear()
    return redirect(url_for('login_page'))


# --- Rota para o Dashboard de Análise ---
@app.route('/dashboard')
@requires_auth
def dashboard():
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    
    # Passa o tipo de usuário para o template
    user_type = session.get('user_type', 'operador')
    return render_template('dashboard.html', user_type=user_type)

@app.route('/motorista/<nome>')
@requires_auth
def motorista_detalhes(nome):
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    if not db:
        return "Erro: Conexão com o banco de dados não estabelecida.", 500
    try:
        # Busca os detalhes do motorista
        motoristas_ref = db.collection('motoristas')
        motorista_query = motoristas_ref.where(filter=firestore.FieldFilter('nome', '==', nome)).limit(1).stream()
        motorista = next(motorista_query, None)
        if not motorista:
            return "Motorista não encontrado.", 404

        motorista_data = serialize_doc(motorista.to_dict())

        # Busca o histórico de viagens do motorista
        saidas_ref = db.collection('saidas')
        viagens_query = saidas_ref.where(filter=firestore.FieldFilter('motorista', '==', nome)).order_by('timestampSaida', direction=firestore.Query.DESCENDING).stream()
        viagens = [serialize_doc(doc.to_dict()) for doc in viagens_query]

        # Calcula estatísticas
        total_viagens = len(viagens)
        total_horas = 0
        for viagem in viagens:
            if viagem.get('status') == 'finalizada' and viagem.get('timestampSaida') and viagem.get('timestampChegada'):
                saida = datetime.fromisoformat(viagem['timestampSaida'])
                chegada = datetime.fromisoformat(viagem['timestampChegada'])
                total_horas += (chegada - saida).total_seconds() / 3600

        stats = {
            'total_viagens': total_viagens,
            'total_horas': f"{total_horas:.2f}"
        }

        return render_template('motorista_detalhes.html', motorista=motorista_data, viagens=viagens, stats=stats)

    except Exception as e:
        print(f"Erro ao buscar detalhes do motorista: {e}")
        return "Ocorreu um erro ao buscar os detalhes do motorista.", 500


@app.route('/api/cancelar', methods=['POST'])
def api_cancelar():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    data = request.get_json() or {}
    veiculo = (data.get('veiculo') or '').strip()
    if not veiculo:
        return jsonify({"error": "Campo 'veiculo' é obrigatório."}), 400
    veiculo = normalize_plate(veiculo)
    try:
        saidas_ref = db.collection('saidas')
        # Firestore may require a composite index for filtering by vehicle+status+order_by.
        # To avoid forcing an index during dev, we fetch documents with status 'em_curso'
        # (single-field indexed) and filter/sort in Python. This is acceptable since
        # the number of in-progress trips is small in normal operation.
        query = saidas_ref.where(filter=firestore.FieldFilter('status', '==', 'em_curso'))
        viagens_cursor = list(query.stream())
        # Filter by normalized vehicle and find the one with the latest timestampSaida
        viagens_filtradas = []
        for doc in viagens_cursor:
            data_doc = doc.to_dict() or {}
            if normalize_plate(data_doc.get('veiculo', '') or '') == veiculo:
                viagens_filtradas.append((doc, data_doc))
        if not viagens_filtradas:
            return jsonify({"error": "Nenhum registro em curso encontrado para este veículo."}), 404
        # Sort by timestampSaida descending (newest first)
        viagens_filtradas.sort(key=lambda pair: pair[1].get('timestampSaida') or '', reverse=True)
        viagem_doc = viagens_filtradas[0][0]
        # Delete the document as requested by the user (cancel should remove the viagem)
        viagem_doc.reference.delete()
        
        # Invalida cache do histórico após cancelamento
        invalidate_historico_cache()
        
        return jsonify({"message": "Viagem cancelada."}), 200
    except Exception as e:
        print(f"Erro ao cancelar viagem: {e}")
        return jsonify({"error": "Ocorreu um erro ao cancelar a viagem."}), 500

@app.route('/veiculo/<placa>')
@app.route('/veiculos/<placa>')
@requires_auth
def veiculo_detalhes(placa):
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    if not db:
        return "Erro: Conexão com o banco de dados não estabelecida.", 500

    try:
        # Busca o histórico de viagens do veículo
        saidas_ref = db.collection('saidas')
        viagens_query = saidas_ref.where(filter=firestore.FieldFilter('veiculo', '==', placa)).order_by('timestampSaida', direction=firestore.Query.DESCENDING).stream()
        
        viagens_list = [serialize_doc(doc.to_dict()) for doc in viagens_query]

        # Preparar lista de saídas para o template
        saidas = []
        for v in viagens_list:
            saidas.append({
                'status': v.get('status'),
                'motorista': v.get('motorista'),
                'saida': v.get('timestampSaida'),
                'chegada': v.get('timestampChegada'),
                'trajeto': v.get('trajeto')
            })

        # Calcula estatísticas
        total_viagens = len(viagens_list)
        total_horas = 0
        for viagem in viagens_list:
            if viagem.get('status') == 'finalizada' and viagem.get('timestampSaida') and viagem.get('timestampChegada'):
                saida = datetime.fromisoformat(viagem['timestampSaida'])
                chegada = datetime.fromisoformat(viagem['timestampChegada'])
                total_horas += (chegada - saida).total_seconds() / 3600

        # Buscar timestamp do veículo
        veiculos_ref = db.collection('veiculos')
        veiculo_query = veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).stream()
        veiculo = next(veiculo_query, None)
        timestamp = None
        if veiculo:
            veiculo_data = veiculo.to_dict()
            timestamp = veiculo_data.get('timestamp')

        return render_template('veiculo_detalhes.html', 
                             placa=placa,
                             timestamp=timestamp,
                             total_viagens=total_viagens,
                             horas_viagens=f"{total_horas:.2f}",
                             saidas=saidas)

    except Exception as e:
        print(f"Erro ao buscar detalhes do veículo: {e}")
        return "Ocorreu um erro ao buscar os detalhes do veículo.", 500


# --- API Endpoints ---

@app.route('/api/saida', methods=['POST'])
def api_saida():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    # Limpeza dos dados de entrada para remover espaços em branco
    veiculo = (data.get('veiculo') or '').strip()
    motorista = (data.get('motorista') or '').strip()
    solicitante = (data.get('solicitante') or '').strip()
    trajeto = (data.get('trajeto') or '').strip()
    horario = data.get('horario') # Horário é opcional
    veiculo_categoria = data.get('veiculo_categoria', 'Outros')
    motorista_secao = data.get('motorista_secao', 'Outros')

    # Normaliza entradas: placa em maiúsculas; nomes e textos capitalizados
    def title_case(s):
        return ' '.join([w.capitalize() for w in s.split()]) if s else s

    veiculo = normalize_plate(veiculo) if veiculo else veiculo
    motorista = title_case(motorista)
    solicitante = title_case(solicitante)
    trajeto = title_case(trajeto)

    if not all([veiculo, motorista, solicitante, trajeto]):
        return jsonify({"error": "Todos os campos de saída são obrigatórios."}), 400

    response_message = handle_saida(veiculo, motorista, solicitante, trajeto, horario, veiculo_categoria, motorista_secao)

    # Lógica de resposta baseada na mensagem de retorno
    if "sucesso" in response_message:
        return jsonify({"message": response_message}), 200
    elif "já está em curso" in response_message:
        return jsonify({"error": response_message}), 409 # 409 Conflict
    else:
        return jsonify({"error": response_message}), 500


@app.route('/api/chegada', methods=['POST'])
def api_chegada():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    veiculo = (data.get('veiculo') or '').strip()
    horario = data.get('horario')  # Horário é opcional
    litros = data.get('litros')
    odometro = data.get('odometro')

    # Normaliza placa
    veiculo = normalize_plate(veiculo) if veiculo else veiculo

    if not veiculo:
        return jsonify({"error": "O campo veículo é obrigatório."}), 400

    response_message = handle_chegada(veiculo, horario, litros=litros, odometro=odometro)
    
    # Invalida cache do histórico se foi sucesso
    if "sucesso" in response_message:
        invalidate_historico_cache()

    if "sucesso" in response_message:
        return jsonify({"message": response_message}), 200
    else:
        if "Nenhum registro" in response_message:
            return jsonify({"error": response_message}), 404  # 404 Not Found
        return jsonify({"error": response_message}), 500

@app.route('/api/abastecimento', methods=['POST'])
def api_abastecimento():
    """Rota para registrar abastecimento rápido"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    placa = (data.get('placa') or '').strip()
    motorista = (data.get('motorista') or '').strip()
    litros = data.get('litros')
    odometro = data.get('odometro')
    veiculo_categoria = data.get('veiculo_categoria', 'Outros')

    # Normaliza placa e nome
    placa = normalize_plate(placa) if placa else placa
    def title_case(s):
        return ' '.join([w.capitalize() for w in s.split()]) if s else s
    motorista = title_case(motorista)

    if not all([placa, motorista, litros]):
        return jsonify({"error": "Placa, motorista e litros são obrigatórios."}), 400

    try:
        # Verifica/Cria veículo se não existir
        veiculos_ref = db.collection('veiculos')
        veiculo_query = veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).stream()
        veiculo_docs = list(veiculo_query)
        
        if not veiculo_docs:
            # Cria veículo automaticamente
            veiculos_ref.add({
                'placa': placa,
                'tipo': 'Não especificado',
                'modelo': 'Não especificado',
                'categoria': veiculo_categoria,
                'visivel_para_motoristas': True,
                'status_ativo': True,
                'dataCadastro': firestore.SERVER_TIMESTAMP,
                'viagens_totais': 0
            })
            print(f" Veículo {placa} criado automaticamente na categoria {veiculo_categoria}")
        
        # Registra no Firestore na coleção 'refuels' (mesma coleção dos gráficos)
        refuels_ref = db.collection('refuels')
        now_utc = datetime.now(timezone.utc)
        
        refuels_ref.add({
            'veiculo': placa,  # Campo 'veiculo', não 'placa'
            'motorista': motorista,
            'litros': float(litros),
            'odometro': int(odometro) if odometro else None,
            'timestamp': now_utc
        })
        
        print(f"[OK] Abastecimento registrado: {placa} - {litros}L")
        return jsonify({"message": f"Abastecimento de {litros}L registrado para {placa}"}), 200
    except Exception as e:
        print(f" Erro ao registrar abastecimento: {e}")
        return jsonify({"error": "Erro ao registrar abastecimento"}), 500

@app.route('/api/veiculos_em_curso', methods=['GET'])
def get_veiculos_em_curso():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        saidas_ref = db.collection('saidas')
        query = saidas_ref.where(filter=firestore.FieldFilter('status', '==', 'em_curso')).order_by('timestampSaida', direction=firestore.Query.ASCENDING)
        viagens_em_curso = query.stream()

        veiculos = []
        for doc in viagens_em_curso:
            data = doc.to_dict()
            placa = data.get("veiculo")
            
            # Buscar categoria do veículo
            categoria = "Outros"  # valor padrão
            if placa:
                veiculo_docs = db.collection('veiculos').where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).get()
                if veiculo_docs:
                    veiculo_data = veiculo_docs[0].to_dict()
                    categoria = veiculo_data.get('categoria', 'Outros')
            
            veiculos.append({
                "id": doc.id,  # [OK] Adicionado ID do documento
                "veiculo": placa,
                "motorista": data.get("motorista"),
                "solicitante": data.get("solicitante"),
                "trajeto": data.get("trajeto"),
                "horarioSaida": data.get("horarioSaida"),
                "categoria": categoria  # [OK] Categoria do veículo
            })
        
        return jsonify(veiculos), 200

    except Exception as e:
        print(f"Erro ao buscar veículos em curso: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar os veículos em curso."}), 500

# ==========================================
#  API DE GERENCIAMENTO DE USUÁRIOS
# ==========================================

@app.route('/api/usuarios', methods=['GET'])
@requires_auth
def get_usuarios():
    """Lista todos os usuários (somente admin)"""
    if session.get('user_type') != 'admin':
        return jsonify({"error": "Acesso negado"}), 403
    
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        usuarios = []
        users_ref = db.collection('usuarios').stream()
        for doc in users_ref:
            data = doc.to_dict()
            # Remove password_hash da resposta
            data.pop('password_hash', None)
            data['id'] = doc.id
            usuarios.append(data)
        
        # Ordena por nome
        usuarios.sort(key=lambda x: x.get('nome_completo', ''))
        return jsonify(usuarios), 200
        
    except Exception as e:
        print(f"Erro ao buscar usuários: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/usuarios', methods=['POST'])
@requires_auth
def create_usuario():
    """Cria novo usuário (somente admin)"""
    if session.get('user_type') != 'admin':
        return jsonify({"error": "Acesso negado"}), 403
    
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    nome_completo = (data.get('nome_completo') or '').strip()
    tipo = (data.get('tipo') or 'operador').strip()
    
    if not username or not password or not nome_completo:
        return jsonify({"error": "username, password e nome_completo são obrigatórios"}), 400
    
    if tipo not in ['admin', 'historico', 'operador']:
        return jsonify({"error": "tipo deve ser: admin, historico ou operador"}), 400
    
    try:
        # Verifica se username já existe
        existing = db.collection('usuarios').where(filter=firestore.FieldFilter('username', '==', username)).limit(1).get()
        if len(list(existing)) > 0:
            return jsonify({"error": "Username já existe"}), 400
        
        # Cria hash da senha
        password_hash = hash_password(password)
        
        # Cria documento do usuário
        user_data = {
            'username': username,
            'password_hash': password_hash,
            'nome_completo': nome_completo,
            'tipo': tipo,
            'ativo': True,
            'data_criacao': datetime.now(LOCAL_TZ)
        }
        
        doc_ref = db.collection('usuarios').add(user_data)
        
        # Auditoria
        log_audit('create', 'usuarios', doc_ref[1].id, new_data={'username': username, 'tipo': tipo})
        
        return jsonify({"message": "Usuário criado com sucesso", "id": doc_ref[1].id}), 201
        
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/usuarios/<user_id>', methods=['PUT'])
@requires_auth
def update_usuario(user_id):
    """Atualiza usuário (somente admin)"""
    if session.get('user_type') != 'admin':
        return jsonify({"error": "Acesso negado"}), 403
    
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    
    try:
        user_ref = db.collection('usuarios').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        old_data = user_doc.to_dict()
        update_data = {}
        
        # Campos permitidos para atualizar
        if 'nome_completo' in data:
            update_data['nome_completo'] = data['nome_completo'].strip()
        if 'tipo' in data:
            if data['tipo'] not in ['admin', 'historico', 'operador']:
                return jsonify({"error": "tipo inválido"}), 400
            update_data['tipo'] = data['tipo']
        if 'ativo' in data:
            update_data['ativo'] = bool(data['ativo'])
        
        # Atualizar senha se fornecida
        if 'password' in data and data['password']:
            update_data['password_hash'] = hash_password(data['password'])
        
        if not update_data:
            return jsonify({"error": "Nenhum campo para atualizar"}), 400
        
        user_ref.update(update_data)
        
        # Auditoria (sem incluir password_hash)
        audit_data = {k: v for k, v in update_data.items() if k != 'password_hash'}
        log_audit('update', 'usuarios', user_id, old_data={'username': old_data.get('username')}, new_data=audit_data)
        
        return jsonify({"message": "Usuário atualizado com sucesso"}), 200
        
    except Exception as e:
        print(f"Erro ao atualizar usuário: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/usuarios/<user_id>', methods=['DELETE'])
@requires_auth
def delete_usuario(user_id):
    """Desativa usuário (não deleta, apenas marca como inativo)"""
    if session.get('user_type') != 'admin':
        return jsonify({"error": "Acesso negado"}), 403
    
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        user_ref = db.collection('usuarios').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        user_data = user_doc.to_dict()
        
        # Não permite deletar a si mesmo
        if user_data.get('username') == session.get('username'):
            return jsonify({"error": "Você não pode desativar sua própria conta"}), 400
        
        # Marca como inativo ao invés de deletar
        user_ref.update({'ativo': False})
        
        # Auditoria
        log_audit('deactivate', 'usuarios', user_id, old_data={'username': user_data.get('username'), 'ativo': True})
        
        return jsonify({"message": "Usuário desativado com sucesso"}), 200
        
    except Exception as e:
        print(f"Erro ao desativar usuário: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# [LIST] API DE LOGS DE AUDITORIA
# ==========================================

@app.route('/api/audit-logs', methods=['GET'])
@requires_auth
def get_audit_logs():
    """Lista logs de auditoria (somente admin)"""
    if session.get('user_type') != 'admin':
        return jsonify({"error": "Acesso negado - somente administradores"}), 403
    
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        # Filtros opcionais
        user_filter = request.args.get('user', '').strip()
        action_filter = request.args.get('action', '').strip()
        collection_filter = request.args.get('collection', '').strip()
        limit_param = request.args.get('limit', '50')
        
        try:
            limit_value = int(limit_param)
            if limit_value > 50:  # Máximo de 50 para economizar quota
                limit_value = 50
        except:
            limit_value = 50
        
        # Query base
        query = db.collection('audit_log').order_by('timestamp', direction=firestore.Query.DESCENDING)
        
        # Aplica filtros
        if user_filter:
            query = query.where(filter=firestore.FieldFilter('user', '==', user_filter))
        if action_filter:
            query = query.where(filter=firestore.FieldFilter('action', '==', action_filter))
        if collection_filter:
            query = query.where(filter=firestore.FieldFilter('collection', '==', collection_filter))
        
        # Executa query
        logs_docs = query.limit(limit_value).stream()
        
        logs = []
        for doc in logs_docs:
            log_data = serialize_doc(doc.to_dict())
            log_data['id'] = doc.id
            logs.append(log_data)
        
        return jsonify(logs), 200
        
    except Exception as e:
        print(f"Erro ao buscar logs de auditoria: {e}")
        return jsonify({"error": str(e)}), 500

# Cache para histórico (5 minutos) - um cache para cada combinação de filtros
historico_cache = {}  # Dicionário de caches por chave (mes_ano_placa_motorista_page)

@app.route('/api/historico', methods=['GET'])
@requires_auth_historico
def get_historico():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        data_filtro = request.args.get('data')       # ex: 17/10/2025
        mes_filtro = request.args.get('mes_filtro') or request.args.get('mes')  # ex: 10 (outubro)
        ano_filtro = request.args.get('ano_filtro') or request.args.get('ano')  # ex: 2025
        placa_filtro = request.args.get('placa', '').strip()
        motorista_filtro = request.args.get('motorista', '').strip()
        
        # [OK] PAGINAÇÃO SERVER-SIDE para economizar quota
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 500))  # [OK] AUMENTADO DE 50 PARA 500

        # [OK] SE NÃO TEM FILTROS, BUSCA DO MÊS ATUAL
        if not data_filtro and not mes_filtro and not ano_filtro:
            now_local = datetime.now(LOCAL_TZ)
            mes_filtro = str(now_local.month)
            ano_filtro = str(now_local.year)
            print(f'[DATE] Sem filtro de data: buscando mês atual {mes_filtro}/{ano_filtro}')

        # [OK] CACHE de 5 minutos - invalidado automaticamente em saídas/chegadas/cancelamentos
        now = time.time()
        cache_key = f"{mes_filtro}_{ano_filtro}_{placa_filtro}_{motorista_filtro}_{page}"
        
        #  BYPASS DE CACHE para requisições real-time (com parâmetro _t recente)
        bypass_cache = False
        timestamp_param = request.args.get('_t')
        if timestamp_param:
            try:
                request_timestamp = int(timestamp_param) / 1000  # Converte de ms para segundos
                time_diff = now - request_timestamp
                if time_diff < 10:  # Se a requisição foi feita nos últimos 10 segundos
                    bypass_cache = True
                    print(f'[FAST] BYPASS CACHE - Requisição real-time detectada (há {time_diff:.1f}s)')
            except (ValueError, TypeError):
                pass
        
        # Verifica se tem cache válido (só usa se não for bypass)
        if not bypass_cache and cache_key in historico_cache and historico_cache[cache_key]['expires'] > now:
            cached = historico_cache[cache_key]['data']
            print(f'[FAST] Cache hit: {mes_filtro}/{ano_filtro} - economiza leituras Firestore')
            return jsonify(cached), 200
        
        print(f'[RELOAD] Cache miss: buscando {mes_filtro}/{ano_filtro} do Firestore')

        # Começa a query básica
        query = db.collection('saidas')
        
        # Flag para saber se aplicamos filtros complexos (que exigem filtro local)
        needs_local_filter = False
        
        # [OK] 1. SEMPRE aplica filtro de MÊS/ANO primeiro (base de todas as buscas)
        if mes_filtro and ano_filtro:
            try:
                mes = int(mes_filtro)
                ano = int(ano_filtro)
                
                # Primeiro dia do mês às 00:00:00
                start_local = datetime(ano, mes, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                
                # Último dia do mês às 23:59:59
                if mes == 12:
                    end_local = datetime(ano, 12, 31, 23, 59, 59, tzinfo=LOCAL_TZ)
                else:
                    # Último segundo antes do próximo mês
                    end_local = datetime(ano, mes + 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ) - timedelta(seconds=1)
                
                start_utc = start_local.astimezone(timezone.utc)
                end_utc = end_local.astimezone(timezone.utc)
                
                query = query.where(filter=firestore.FieldFilter('timestampSaida', '>=', start_utc))
                query = query.where(filter=firestore.FieldFilter('timestampSaida', '<=', end_utc))
                
                print(f'[DATE] Filtro de mês: {mes}/{ano} ({start_local} até {end_local})')
            except ValueError as e:
                print(f' Erro no filtro de mês/ano: {e}')
                pass
        
        # [OK] 2. Aplica filtro de DATA ESPECÍFICA (refina o mês para um dia específico)
        if data_filtro:
            try:
                # Converte a data local para UTC para a consulta
                data_obj = datetime.strptime(data_filtro, '%d/%m/%Y')
                
                # [OK] VALIDA: data deve estar dentro do mês selecionado
                if mes_filtro and ano_filtro:
                    mes = int(mes_filtro)
                    ano = int(ano_filtro)
                    if data_obj.month != mes or data_obj.year != ano:
                        print(f' Data {data_filtro} fora do mês {mes}/{ano} - ignorando filtro de data')
                        data_filtro = None  # Ignora data fora do mês
                
                if data_filtro:  # Se ainda é válida
                    start_local = data_obj.replace(hour=0, minute=0, second=0, tzinfo=LOCAL_TZ)
                    end_local = data_obj.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ)
                    
                    start_utc = start_local.astimezone(timezone.utc)
                    end_utc = end_local.astimezone(timezone.utc)
                    
                    # Substitui o filtro de mês pelo filtro de dia específico
                    query = db.collection('saidas')
                    query = query.where(filter=firestore.FieldFilter('timestampSaida', '>=', start_utc))
                    query = query.where(filter=firestore.FieldFilter('timestampSaida', '<=', end_utc))
                    print(f'[DATE] Filtro de data específica: {data_filtro} dentro de {mes}/{ano}')
            except ValueError:
                print(f' Data inválida: {data_filtro}')
                pass

        # [OK] 3. Aplica filtro de PLACA (se houver)
        # Como já temos filtro de timestamp, precisamos fazer filtro local para placa
        if placa_filtro:
            needs_local_filter = True

        # [OK] 4. Motorista sempre filtrado localmente (mais flexível - case insensitive, partial match)
        if motorista_filtro:
            needs_local_filter = True

        # [OK] 5. Ordena e Executa a query
        query = query.order_by('timestampSaida', direction=firestore.Query.DESCENDING)
        
        # [OK] REMOVE PAGINAÇÃO COM OFFSET (causa o bug de retornar poucos registros)
        # Retorna TODOS os registros do mês (até o limite de 500)
        historico_docs = query.limit(limit).stream() 

        historico = []
        veiculos_cache_map = {}  # Cache de categorias dos veículos
        
        for doc in historico_docs:
            data = serialize_doc(doc.to_dict())
            data['id'] = doc.id  # [OK] ADICIONA O ID DO DOCUMENTO
            
            # [OK] FILTROS LOCAIS (aplicados após buscar do Firestore)
            # Filtro de placa
            if placa_filtro:
                placa_doc = data.get('veiculo', '')
                placa_normalizada = normalize_plate(placa_filtro)
                if placa_doc.upper() != placa_normalizada.upper():
                    continue  # Pula este registro
            
            # Filtro de motorista (case insensitive, partial match)
            if motorista_filtro:
                motorista_doc = data.get('motorista', '').lower()
                motorista_busca = motorista_filtro.lower()
                if motorista_busca not in motorista_doc:
                    continue  # Pula este registro
            
            # Busca categoria do veículo (com cache para evitar queries repetidas)
            placa = data.get('veiculo')
            if placa and placa not in veiculos_cache_map:
                try:
                    veiculo_docs = db.collection('veiculos').where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).get()
                    if veiculo_docs:
                        veiculo_info = veiculo_docs[0].to_dict()
                        veiculos_cache_map[placa] = veiculo_info.get('categoria', 'Outros')
                    else:
                        veiculos_cache_map[placa] = 'Outros'
                except:
                    veiculos_cache_map[placa] = 'Outros'
            
            data['categoria'] = veiculos_cache_map.get(placa, 'Outros')
            historico.append(data)
        
        # [OK] Busca TOTAL de registros (para paginação) - usa COUNT do Firestore (1 leitura!)
        count_query = db.collection('saidas')
        
        # [OK] SEMPRE aplica filtro de mês no count (mesma lógica da query principal)
        if mes_filtro and ano_filtro:
            try:
                mes = int(mes_filtro)
                ano = int(ano_filtro)
                start_local = datetime(ano, mes, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                if mes == 12:
                    end_local = datetime(ano, 12, 31, 23, 59, 59, tzinfo=LOCAL_TZ)
                else:
                    end_local = datetime(ano, mes + 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ) - timedelta(seconds=1)
                start_utc = start_local.astimezone(timezone.utc)
                end_utc = end_local.astimezone(timezone.utc)
                count_query = count_query.where(filter=firestore.FieldFilter('timestampSaida', '>=', start_utc))
                count_query = count_query.where(filter=firestore.FieldFilter('timestampSaida', '<=', end_utc))
            except ValueError:
                pass
        
        # Se tem filtro de data específica, substitui o filtro de mês
        if data_filtro:
            try:
                data_obj = datetime.strptime(data_filtro, '%d/%m/%Y')
                start_local = data_obj.replace(hour=0, minute=0, second=0, tzinfo=LOCAL_TZ)
                end_local = data_obj.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ)
                start_utc = start_local.astimezone(timezone.utc)
                end_utc = end_local.astimezone(timezone.utc)
                count_query = db.collection('saidas')
                count_query = count_query.where(filter=firestore.FieldFilter('timestampSaida', '>=', start_utc))
                count_query = count_query.where(filter=firestore.FieldFilter('timestampSaida', '<=', end_utc))
            except ValueError:
                pass
        
        #  Filtros locais (placa e motorista) não podem ser aplicados no count
        # O count será aproximado se houver filtros locais
        # Para ter count exato com filtros locais, usamos len(historico)
        if needs_local_filter:
            total_count = len(historico)
            print(f"[STATS] COUNT com filtros locais: {total_count} registros")
        else:
            # Conta total de registros (busca apenas IDs, mais eficiente que documentos completos)
            try:
                # Tenta usar COUNT do Firestore (SDK mais recente)
                count_result = count_query.count().get()
                total_count = count_result[0][0].value
                print(f"[OK] COUNT otimizado: {total_count} registros totais (1 leitura)")
            except Exception as count_error:
                # Fallback: busca apenas 1 campo (timestampSaida) ao invés do doc completo
                print(f" COUNT falhou ({count_error}), usando contagem manual...")
                docs_count = list(count_query.select(['timestampSaida']).stream())
                total_count = len(docs_count)
                print(f"[STATS] Contagem manual: {total_count} registros totais")
        
        # DEBUG: Verifica contagem
        print(f"[Pagina] {page}: retornando {len(historico)} registros de {total_count} totais")
        if placa_filtro:
            print(f"[SEARCH] Filtro de placa aplicado: {placa_filtro}")
        if motorista_filtro:
            print(f"[SEARCH] Filtro de motorista aplicado: {motorista_filtro}")

        # Ordena localmente: primeiro por status (em_curso primeiro), depois por timestamp (mais recente primeiro)
        def sort_key(item):
            # Prioridade 1: em_curso = 0, finalizada = 1 (menor número vem primeiro)
            status_priority = 0 if item.get('status') == 'em_curso' else 1
            
            # Prioridade 2: timestamp mais recente (negativo para ordem decrescente)
            timestamp_str = item.get('timestampSaida', '')
            try:
                if timestamp_str:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamp_val = -ts.timestamp()  # Negativo para mais recente primeiro
                else:
                    timestamp_val = 0
            except:
                timestamp_val = 0
            
            return (status_priority, timestamp_val)
        
        historico_final = sorted(historico, key=sort_key)

        # [OK] Salva no cache (5 minutos) - APENAS se não tem filtros E é página 1
        response_data = {
            'historico': historico_final,
            'total': total_count,
            'page': page,
            'limit': limit
        }
        
        # Salva no cache somente quando é busca geral (sem filtros) da página 1
        if not data_filtro and not placa_filtro and not motorista_filtro and page == 1:
            historico_cache[cache_key] = {
                'data': response_data,
                'expires': time.time() + 300  # 5 minutos
            }
            print(f'[SAVE] Cache salvo: {mes_filtro}/{ano_filtro} por 5min ({len(historico_final)} registros)')
        else:
            print(f'[OK] Sem cache (tem filtros): {len(historico_final)} registros')

        return jsonify(response_data), 200

    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar o histórico."}), 500



@app.route('/api/motoristas', methods=['GET'])
def get_motoristas():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        motoristas_ref = db.collection('motoristas').stream()
        motoristas = []
        for doc in motoristas_ref:
            motorista_data = doc.to_dict()
            motorista_data['id'] = doc.id
            motoristas.append(serialize_doc(motorista_data))
        return jsonify(motoristas), 200

    except Exception as e:
        print(f"Erro ao buscar motoristas: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar os motoristas."}), 500


@app.route('/api/motoristas', methods=['POST'])
@requires_auth
def post_motorista():
    """Cria um motorista com campos opcionais: funcao, empresa."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    funcao = (data.get('funcao') or '').strip()
    empresa = (data.get('empresa') or '').strip()
    secao = (data.get('secao') or 'Outros').strip()
    if not secao:
        secao = 'Outros'
    visivel = data.get('visivel_para_motoristas', True)

    if not nome:
        return jsonify({"error": "O campo 'nome' é obrigatório."}), 400

    try:
        motoristas_ref = db.collection('motoristas')
        # Evita duplicados por nome
        existing = list(motoristas_ref.where(filter=firestore.FieldFilter('nome', '==', nome)).limit(1).stream())
        if existing:
            return jsonify({"error": "Motorista já cadastrado."}), 409

        motoristas_ref.add({
            'nome': nome,
            'funcao': funcao,
            'empresa': empresa,
            'secao': secao,
            'visivel_para_motoristas': visivel,
            'status': 'nao_credenciado',
            'status_ativo': True,  # [OK] Novo campo: Ativo por padrão
            'cnh_url': None,  # [OK] Novo campo: URL da CNH
            'dataCadastro': firestore.SERVER_TIMESTAMP
        })

        return jsonify({"message": "Motorista cadastrado com sucesso."}), 201
    except Exception as e:
        print(f"Erro ao cadastrar motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao cadastrar o motorista."}), 500


@app.route('/api/motoristas/<motorista_id>', methods=['PUT'])
@requires_auth
def update_motorista(motorista_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    funcao = (data.get('funcao') or '').strip()
    empresa = (data.get('empresa') or '').strip()
    secao = (data.get('secao') or 'Outros').strip()
    if not secao:
        secao = 'Outros'
    visivel = data.get('visivel_para_motoristas', True)

    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()

        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404
        
        # Salva dados antigos para auditoria
        motorista_data = motorista_doc.to_dict()

        update_data = {}
        if nome:
            update_data['nome'] = nome
        if funcao:
            update_data['funcao'] = funcao
        if empresa:
            update_data['empresa'] = empresa
        if 'secao' in data and secao:
            update_data['secao'] = secao
        if 'visivel_para_motoristas' in data:
            update_data['visivel_para_motoristas'] = visivel

        if not update_data:
            return jsonify({"error": "Nenhum campo para atualizar."}), 400

        # Auditoria: registra atualização do motorista
        log_audit('update', 'motoristas', motorista_id, old_data=motorista_data, new_data=update_data)
        
        motorista_ref.update(update_data)
        return jsonify({"message": "Motorista atualizado com sucesso."}), 200

    except Exception as e:
        print(f"Erro ao atualizar motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar o motorista."}), 500


@app.route('/api/motoristas/<motorista_id>', methods=['DELETE'])
@requires_auth
def delete_motorista(motorista_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()

        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404
        
        # Salva dados antigos para auditoria
        motorista_data = motorista_doc.to_dict()
        
        # [SAVE] BACKUP: Se tem CNH anexada, mover para pasta de backup
        backup_urls = []
        if motorista_data.get('cnh_url'):
            try:
                # Extrai caminho do arquivo da URL
                cnh_url = motorista_data['cnh_url']
                if 'firebasestorage.googleapis.com' in cnh_url:
                    import urllib.parse
                    path_start = cnh_url.find('/o/') + 3
                    path_end = cnh_url.find('?')
                    if path_start > 2 and path_end > path_start:
                        file_path = urllib.parse.unquote(cnh_url[path_start:path_end])
                        backup_url = backup_storage_file(file_path, reason='motorista_deleted')
                        if backup_url:
                            backup_urls.append({
                                'tipo': 'cnh',
                                'url_original': cnh_url,
                                'url_backup': backup_url
                            })
                            print(f"[OK] CNH do motorista {motorista_data.get('nome')} salva em backup")
            except Exception as e:
                print(f" Erro ao fazer backup da CNH: {e}")
        
        # Adiciona URLs de backup nos dados de auditoria
        motorista_data['_backups'] = backup_urls

        # Auditoria: registra exclusão do motorista COM backups
        log_audit('delete', 'motoristas', motorista_id, old_data=motorista_data)
        
        motorista_ref.delete()
        return jsonify({
            "message": "Motorista excluído com sucesso.",
            "backups": backup_urls
        }), 200

    except Exception as e:
        print(f"Erro ao excluir motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao excluir o motorista."}), 500


@app.route('/api/motoristas/<motorista_id>/upload-cnh', methods=['POST'])
@requires_auth
def upload_cnh(motorista_id):
    """Upload CNH document for a motorista"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        # Verificar se motorista existe
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()
        
        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404
        
        motorista_data = motorista_doc.to_dict()
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo foi enviado."}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Nome do arquivo está vazio."}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": "Tipo de arquivo não permitido. Use PDF, JPG ou PNG."}), 400
        
        # DELETAR todos os arquivos antigos de CNH deste motorista
        # Lista todos os blobs na pasta do motorista
        prefix = f"motoristas/{motorista_id}/"
        blobs_to_delete = bucket.list_blobs(prefix=prefix)
        for old_blob in blobs_to_delete:
            if 'cnh' in old_blob.name:
                old_blob.delete()
                print(f"[DELETE] Arquivo antigo deletado: {old_blob.name}")
        
        # Criar nome do arquivo no Storage com timestamp para evitar cache
        timestamp = int(datetime.now().timestamp())
        blob_name = f"motoristas/{motorista_id}/cnh_{timestamp}.{file_ext}"
        blob = bucket.blob(blob_name)
        
        # Upload para Firebase Storage
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Tornar o arquivo público (ou gerar signed URL se preferir)
        blob.make_public()
        
        # Obter URL pública
        cnh_url = blob.public_url
        
        print(f"[OK] CNH salva em: {blob_name}")
        print(f" URL gerada: {cnh_url}")
        
        # Atualizar documento do motorista com a URL
        motorista_ref.update({
            'cnh_url': cnh_url
        })
        
        # Mensagem diferente se foi atualização ou novo upload
        mensagem = "CNH atualizada com sucesso." if motorista_data.get('cnh_url') else "CNH enviada com sucesso."
        
        return jsonify({
            "message": mensagem,
            "cnh_url": cnh_url
        }), 200
        
    except Exception as e:
        print(f"Erro ao fazer upload da CNH: {e}")
        return jsonify({"error": "Ocorreu um erro ao fazer upload da CNH."}), 500


@app.route('/api/motoristas/<motorista_id>/cnh', methods=['GET'])
@requires_auth_historico
def get_cnh(motorista_id):
    """Get CNH document URL for a motorista"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()
        
        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404
        
        motorista_data = motorista_doc.to_dict()
        cnh_url = motorista_data.get('cnh_url')
        
        if not cnh_url:
            return jsonify({"error": "CNH não foi enviada para este motorista."}), 404
        
        return jsonify({
            "cnh_url": cnh_url
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar CNH: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar a CNH."}), 500


@app.route('/api/motoristas/<motorista_id>/status', methods=['PATCH'])
@requires_auth
def toggle_motorista_status(motorista_id):
    """Toggle motorista active status"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()
        
        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404
        
        # Obter novo status do body
        data = request.get_json()
        
        if 'status_ativo' not in data:
            return jsonify({"error": "Campo 'status_ativo' é obrigatório."}), 400
        
        status_ativo = data['status_ativo']
        
        if not isinstance(status_ativo, bool):
            return jsonify({"error": "Campo 'status_ativo' deve ser booleano."}), 400
        
        # Atualizar status
        motorista_ref.update({
            'status_ativo': status_ativo
        })
        
        status_texto = "ativo" if status_ativo else "inativo"
        
        return jsonify({
            "message": f"Motorista marcado como {status_texto}.",
            "status_ativo": status_ativo
        }), 200
        
    except Exception as e:
        print(f"Erro ao atualizar status do motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar o status."}), 500


# ============================================================================
# ENDPOINTS DE SAÍDAS (CRUD)
# ============================================================================

@app.route('/api/saidas/<saida_id>', methods=['PATCH'])
@requires_auth_historico
def update_saida(saida_id):
    """Atualiza uma saída existente"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        dados = request.get_json()
        
        # Validação básica (sem KM)
        campos_obrigatorios = ['veiculo', 'motorista', 'solicitante', 'trajeto', 'status', 'timestampSaida']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({"error": f"Campo obrigatório ausente: {campo}"}), 400

        # Busca o documento
        saida_ref = db.collection('saidas').document(saida_id)
        saida_doc = saida_ref.get()

        if not saida_doc.exists:
            return jsonify({"error": "Saída não encontrada."}), 404
        
        # Salva dados antigos para auditoria
        saida_data_old = saida_doc.to_dict()

        # Converte timestamps de string ISO para datetime
        try:
            # timestampSaida vem como string ISO do frontend (ex: "2025-09-23T16:42:00")
            ts_saida_str = dados['timestampSaida']
            # Remove 'Z' se existir e converte para datetime
            if ts_saida_str.endswith('Z'):
                ts_saida_str = ts_saida_str[:-1]
            ts_saida = datetime.fromisoformat(ts_saida_str)
            # Se não tem timezone, assume LOCAL_TZ
            if ts_saida.tzinfo is None:
                ts_saida = ts_saida.replace(tzinfo=LOCAL_TZ)
            # Converte para UTC para salvar no Firestore
            ts_saida_utc = ts_saida.astimezone(timezone.utc)
        except Exception as e:
            print(f" Erro ao converter timestampSaida: {e}")
            return jsonify({"error": f"Formato de data inválido: {e}"}), 400

        # Prepara dados para atualização
        update_data = {
            'veiculo': dados['veiculo'].upper(),
            'motorista': dados['motorista'],
            'solicitante': dados['solicitante'],
            'trajeto': dados['trajeto'],
            'status': dados['status'],
            'timestampSaida': ts_saida_utc
        }

        # Campos opcionais
        if dados.get('timestampChegada'):
            try:
                ts_chegada_str = dados['timestampChegada']
                if ts_chegada_str.endswith('Z'):
                    ts_chegada_str = ts_chegada_str[:-1]
                ts_chegada = datetime.fromisoformat(ts_chegada_str)
                if ts_chegada.tzinfo is None:
                    ts_chegada = ts_chegada.replace(tzinfo=LOCAL_TZ)
                ts_chegada_utc = ts_chegada.astimezone(timezone.utc)
                update_data['timestampChegada'] = ts_chegada_utc
            except:
                pass  # Ignora se der erro na chegada
        
        # Auditoria: registra atualização da saída
        log_audit('update', 'saidas', saida_id, old_data=saida_data_old, new_data=update_data)
        
        # Atualiza no Firestore
        saida_ref.update(update_data)
        
        #  LIMPA CACHE após edição
        dashboard_cache.clear()
        historico_cache['expires'] = 0
        print("[DELETE] Cache do dashboard e histórico invalidados após edição")
        
        print(f"[OK] Saída {saida_id} atualizada com sucesso")
        print(f"[DATE] Timestamp salvo (UTC): {update_data['timestampSaida']}")
        return jsonify({"message": "Saída atualizada com sucesso.", "id": saida_id}), 200

    except Exception as e:
        print(f" Erro ao atualizar saída: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/saidas/<saida_id>', methods=['DELETE'])
@requires_auth_historico
def delete_saida(saida_id):
    """Exclui uma saída do histórico"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        saida_ref = db.collection('saidas').document(saida_id)
        saida_doc = saida_ref.get()

        if not saida_doc.exists:
            return jsonify({"error": "Saída não encontrada."}), 404
        
        # Salva dados antigos para auditoria
        saida_data = saida_doc.to_dict()
        
        # Auditoria: registra exclusão da saída
        log_audit('delete', 'saidas', saida_id, old_data=saida_data)

        # Deleta o documento
        saida_ref.delete()
        
        #  LIMPA CACHE após exclusão
        dashboard_cache.clear()
        historico_cache['expires'] = 0
        print("[DELETE] Cache do dashboard e histórico invalidados após exclusão")
        
        print(f"[DELETE] Saída {saida_id} excluída com sucesso")
        return jsonify({"message": "Saída excluída com sucesso."}), 200

    except Exception as e:
        print(f" Erro ao excluir saída: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/saidas/<saida_id>/atualizar-rapido', methods=['PATCH'])
def atualizar_saida_rapido(saida_id):
    """Atualiza apenas solicitante e trajeto de uma saída em curso (sem autenticação)"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        dados = request.get_json()
        
        # Validação dos campos permitidos
        if 'solicitante' not in dados or 'trajeto' not in dados:
            return jsonify({"error": "Campos 'solicitante' e 'trajeto' são obrigatórios"}), 400

        # Busca o documento
        saida_ref = db.collection('saidas').document(saida_id)
        saida_doc = saida_ref.get()

        if not saida_doc.exists:
            return jsonify({"error": "Saída não encontrada."}), 404

        # Verifica se está em curso
        saida_data = saida_doc.to_dict()
        if saida_data.get('status') != 'em_curso':
            return jsonify({"error": "Apenas saídas em curso podem ser editadas desta forma."}), 400

        # Atualiza apenas solicitante e trajeto
        update_data = {
            'solicitante': dados['solicitante'].strip(),
            'trajeto': dados['trajeto'].strip()
        }
        
        saida_ref.update(update_data)
        
        #  LIMPA CACHE após edição
        dashboard_cache.clear()
        historico_cache['expires'] = 0
        print("[DELETE] Cache do dashboard e histórico invalidados após edição rápida")
        
        print(f"[OK] Saída {saida_id} atualizada rapidamente (solicitante/trajeto)")
        return jsonify({"message": "Saída atualizada com sucesso.", "id": saida_id}), 200

    except Exception as e:
        print(f" Erro ao atualizar saída rápido: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# FIM DOS ENDPOINTS DE SAÍDAS
# ============================================================================


@app.route('/motoristas')
@requires_auth
def motoristas_page():
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('motoristas.html')


@app.route('/historico')
@requires_auth_historico
def historico_page():
    """Página de histórico somente leitura (COM autenticação separada)"""
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('historico.html')

# Página de Revisões Standalone (opcional - também acessível pelo dashboard)
@app.route('/revisoes')
@requires_auth
def revisoes_page():
    """Página de gestão de revisões e chamados de manutenção"""
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('revisoes.html')

# Removido: /relatorios e /veiculos agora são abas do dashboard
# @app.route('/relatorios')
# @app.route('/veiculos')


@app.route('/motorista')
@requires_auth
def motorista_root_redirect():
    # Legacy or mistyped path: redirect to the motoristas list page
    return redirect(url_for('motoristas_page'))


@app.route('/motorista.html')
@requires_auth
def motorista_html_redirect():
    # Some users might try to open the template path directly; redirect to the route
    return redirect(url_for('motoristas_page'))


# Removido: /veiculos agora é aba do dashboard
# Se alguém acessar /veiculos, redireciona para dashboard
@app.route('/veiculos')
@requires_auth
def veiculos_page():
    """Renderiza a página de veículos, que é parte do dashboard."""
    return render_template('dashboard.html', active_tab='veiculos')


@app.route('/api/veiculos/refuel', methods=['POST'])
@app.route('/api/veiculos/refuels', methods=['POST'])
def post_refuel():
    """Registra um abastecimento. Usa coleção top-level 'refuels' com campo 'veiculo'."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json() or {}
    veiculo = (data.get('veiculo') or '').strip()
    motorista = (data.get('motorista') or '').strip()
    litros = data.get('litros')
    odometro = data.get('odometro')
    observacao = data.get('observacao') or ''
    timestamp = data.get('timestamp')

    if not veiculo:
        return jsonify({"error": "Campo 'veiculo' é obrigatório."}), 400

    veiculo = normalize_plate(veiculo)

    try:
        now_utc = datetime.now(timezone.utc)
        ts = now_utc
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                ts = now_utc

        refuels_ref = db.collection('refuels')
        doc = {
            'veiculo': veiculo,
            'motorista': motorista,
            'litros': float(litros) if litros is not None else None,
            'odometro': int(odometro) if odometro is not None else None,
            'observacao': observacao,
            'timestamp': ts
        }

        # Create a new document with an auto-id and set its data explicitly.
        doc_ref = refuels_ref.document()
        doc_ref.set(doc)
        doc_id = doc_ref.id

        # Verifica/Cria veículo e atualiza último odômetro E contador de refuels
        veiculos_ref = db.collection('veiculos')
        q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo)).limit(1).stream())
        
        if not q:
            # Veículo não existe, criar com campos completos
            veiculos_ref.add({
                'placa': veiculo,
                'tipo': 'Não especificado',
                'modelo': 'Não especificado',
                'ano': None,
                'km_atual': int(odometro) if odometro is not None else 0,
                'ultimo_odometro': int(odometro) if odometro is not None else None,
                'status_ativo': True,
                'dataCadastro': firestore.SERVER_TIMESTAMP,
                'viagens_totais': 0,
                'total_refuels': 1
            })
            print(f"[OK] Veículo {veiculo} criado automaticamente via abastecimento rápido")
        else:
            # Veículo existe, atualizar
            vdoc = q[0]
            update_fields = {'total_refuels': firestore.Increment(1)}
            if odometro is not None:
                update_fields['ultimo_odometro'] = int(odometro)
            vdoc.reference.update(update_fields)

        return jsonify({"message": "Abastecimento registrado com sucesso.", "id": doc_id}), 201
    except Exception as e:
        print(f"Erro ao registrar refuel: {e}")
        return jsonify({"error": "Ocorreu um erro ao registrar o abastecimento."}), 500


@app.route('/api/veiculos/<placa>/refuels', methods=['GET'])
def get_refuels_for_veiculo(placa):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    placa_norm = normalize_plate(placa)
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    try:
        refuels_ref = db.collection('refuels')
        
        # OTIMIZAÇÃO: Usa offset + limit ao invés de ler TUDO
        query = refuels_ref.where(filter=firestore.FieldFilter('veiculo', '==', placa_norm)).order_by('timestamp', direction=firestore.Query.DESCENDING)
        
        # Lê apenas os docs da página atual
        offset = (page - 1) * page_size
        page_docs = query.limit(page_size).offset(offset).stream()
        
        items = []
        for d in page_docs:
            item = d.to_dict()
            item['_id'] = d.id
            items.append(serialize_doc(item))
        
        # OTIMIZAÇÃO: Pega total do contador no veículo (se existir)
        # Se não existir, faz count query (1 leitura agregada)
        try:
            veiculo_ref = db.collection('veiculos').where(filter=firestore.FieldFilter('placa', '==', placa_norm)).limit(1)
            veiculo_docs = list(veiculo_ref.stream())
            if veiculo_docs:
                veiculo_data = veiculo_docs[0].to_dict()
                total = veiculo_data.get('total_refuels', 0)
            else:
                # Fallback: estima baseado na página atual
                total = offset + len(items) + (page_size if len(items) == page_size else 0)
        except Exception:
            total = offset + len(items)
        
        return jsonify({ 'items': items, 'total': total, 'page': page, 'page_size': page_size }), 200
    except Exception as e:
        print(f" Erro ao buscar refuels: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar abastecimentos."}), 500


@app.route('/api/refuels/<refuel_id>', methods=['PATCH'])
def patch_refuel(refuel_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    data = request.get_json() or {}
    try:
        ref = db.collection('refuels').document(refuel_id)
        if not ref.get().exists:
            return jsonify({"error": "Abastecimento não encontrado."}), 404
        update_fields = {}
        if 'motorista' in data:
            update_fields['motorista'] = data.get('motorista')
        if 'litros' in data:
            try:
                update_fields['litros'] = float(data.get('litros')) if data.get('litros') not in (None, '') else None
            except Exception:
                return jsonify({"error": "Valor inválido para litros."}), 400
        if 'odometro' in data:
            try:
                update_fields['odometro'] = int(data.get('odometro')) if data.get('odometro') not in (None, '') else None
            except Exception:
                return jsonify({"error": "Valor inválido para odometro."}), 400
        if 'observacao' in data:
            update_fields['observacao'] = data.get('observacao')
        if not update_fields:
            return jsonify({"error": "Nenhum campo para atualizar."}), 400
        ref.update(update_fields)
        return jsonify({"message": "Abastecimento atualizado."}), 200
    except Exception as e:
        print(f"Erro em patch_refuel: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar abastecimento."}), 500


@app.route('/api/refuels/<refuel_id>', methods=['DELETE'])
def delete_refuel(refuel_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    try:
        ref = db.collection('refuels').document(refuel_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({"error": "Abastecimento não encontrado."}), 404
        
        # Pega a placa antes de deletar para decrementar contador
        refuel_data = doc.to_dict()
        veiculo = refuel_data.get('veiculo')
        
        ref.delete()
        
        # Decrementa o contador no veículo
        if veiculo:
            try:
                veiculos_ref = db.collection('veiculos')
                q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo)).limit(1).stream())
                if q:
                    vdoc = q[0]
                    current_total = vdoc.to_dict().get('total_refuels', 0)
                    if current_total > 0:
                        vdoc.reference.update({'total_refuels': firestore.Increment(-1)})
            except Exception as e:
                print(f"Erro ao decrementar contador de refuels: {e}")
        
        return jsonify({"message": "Abastecimento removido."}), 200
    except Exception as e:
        print(f"Erro em delete_refuel: {e}")
        return jsonify({"error": "Ocorreu um erro ao remover abastecimento."}), 500


def calculate_vehicle_metrics(placa, month_param=None):
    """Calcula métricas para o veículo:
    - km_por_litro_medio: média simples dos km/l calculados entre pares de refuels (usa litros do refuel seguinte)
    - km_por_litro_ponderado: média ponderada por km
    - km_no_mes: km rodados no mês (diferença entre maior e menor odômetro do mês quando disponível)
    - ultimo_odometro: último odômetro registrado
    """
    placa_norm = normalize_plate(placa)
    refuels_ref = db.collection('refuels')
    try:
        docs = list(refuels_ref.where(filter=firestore.FieldFilter('veiculo', '==', placa_norm)).order_by('timestamp', direction=firestore.Query.ASCENDING).stream())
        items = [d.to_dict() for d in docs]

        # tenta buscar o documento do veículo para checar se há média manual informada
        media_informada = None
        try:
            veiculos_ref = db.collection('veiculos')
            vq = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa_norm)).limit(1).stream())
            if vq:
                vdoc = vq[0].to_dict()
                if vdoc.get('media_kmpl') is not None:
                    try:
                        media_informada = float(vdoc.get('media_kmpl'))
                    except Exception:
                        media_informada = None
        except Exception:
            media_informada = None

        # Último odômetro
        ultimo_odometro = None
        for it in reversed(items):
            if it.get('odometro') is not None:
                ultimo_odometro = int(it.get('odometro'))
                break

        # Calcular km/l entre pares consecutivos (usar litros do registro seguinte)
        kmpls = []
        weighted = []
        for i in range(len(items)-1):
            a = items[i]
            b = items[i+1]
            if a.get('odometro') is None or b.get('odometro') is None:
                continue
            od_a = int(a.get('odometro'))
            od_b = int(b.get('odometro'))
            if od_b <= od_a:
                continue
            litros_b = b.get('litros')
            if litros_b is None or litros_b == 0:
                continue
            km = od_b - od_a
            kmpl = km / float(litros_b)
            kmpls.append(kmpl)
            weighted.append((km, kmpl))

        kmpl_medio = None
        kmpl_ponderado = None
        if kmpls:
            kmpl_medio = sum(kmpls) / len(kmpls)
        if weighted:
            total_km = sum(w[0] for w in weighted)
            if total_km > 0:
                kmpl_ponderado = sum(w[0] * w[1] for w in weighted) / total_km

        # Se houver média manual informada no documento do veículo, usar essa como km_por_litro_medio
        media_flag = False
        media_val = None
        if media_informada is not None:
            media_flag = True
            media_val = round(media_informada, 2)

        # km no mês
        km_no_mes = None
        if month_param:
            try:
                year, month = month_param.split('-')
                year = int(year); month = int(month)
                month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                if month == 12:
                    next_month_local = datetime(year+1, 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                else:
                    next_month_local = datetime(year, month+1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                month_end_local = next_month_local - timedelta(seconds=1)
                month_start = month_start_local.astimezone(timezone.utc)
                month_end = month_end_local.astimezone(timezone.utc)

                odometers = [int(it.get('odometro')) for it in items if it.get('odometro') is not None and it.get('timestamp') and it.get('timestamp') >= month_start and it.get('timestamp') <= month_end]
                if odometers:
                    km_no_mes = max(odometers) - min(odometers) if len(odometers) > 1 else 0
            except Exception:
                km_no_mes = None

        # Calcular total de litros abastecidos
        total_litros = sum(float(it.get('litros', 0) or 0) for it in items)
        
        # Calcular km rodados estimado (total_litros × km/l médio)
        km_rodados = None
        media_usar = media_val if media_flag else (kmpl_medio if kmpl_medio is not None else None)
        if media_usar is not None and total_litros > 0:
            km_rodados = total_litros * media_usar

        return {
            'km_por_litro_medio': (media_val if media_flag else (round(kmpl_medio, 2) if kmpl_medio is not None else None)),
            'km_por_litro_medio_computed': round(kmpl_medio, 2) if kmpl_medio is not None else None,
            'km_por_litro_ponderado': round(kmpl_ponderado, 2) if kmpl_ponderado is not None else None,
            'km_no_mes': km_no_mes,
            'ultimo_odometro': ultimo_odometro,
            'media_informada': media_flag,
            'media_informada_valor': media_val,
            'total_litros': round(total_litros, 2) if total_litros else 0,
            'km_rodados': round(km_rodados, 2) if km_rodados is not None else None
        }
    except Exception as e:
        print(f"Erro ao calcular métricas: {e}")
        return None


@app.route('/api/veiculos/<placa>/metrics', methods=['GET'])
def get_veiculo_metrics(placa):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    month = request.args.get('month')
    try:
        metrics = calculate_vehicle_metrics(placa, month_param=month)
        if metrics is None:
            return jsonify({"error": "Erro ao calcular métricas."}), 500
        return jsonify(metrics), 200
    except Exception as e:
        print(f"Erro em get_veiculo_metrics: {e}")
        return jsonify({"error": "Ocorreu um erro ao calcular métricas."}), 500


@app.route('/api/refuels/summary', methods=['GET'])
def get_refuels_summary():
    """Retorna agregados de litros por veículo: totais gerais e totais no mês (opcional ?month=YYYY-MM)."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    month_param = request.args.get('month')
    now = datetime.now(timezone.utc)
    month_start = None
    month_end = None
    if month_param:
        try:
            year, month = month_param.split('-')
            year = int(year); month = int(month)
            month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
            if month == 12:
                next_month_local = datetime(year+1, 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
            else:
                next_month_local = datetime(year, month+1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
            month_end_local = next_month_local - timedelta(seconds=1)
            month_start = month_start_local.astimezone(timezone.utc)
            month_end = month_end_local.astimezone(timezone.utc)
        except Exception:
            month_start = None
            month_end = None

    try:
        refuels_ref = db.collection('refuels')
        
        # OTIMIZAÇÃO CRÍTICA: Reduzido de 5000 para 500
        # 5000 docs = consome toda a quota em poucos reloads
        # 50 docs = suficiente para ver padrões recentes e economizar quota
        docs_total = list(refuels_ref.limit(50).stream())  # 99% de economia!
        
        totals = {}
        for d in docs_total:
            r = d.to_dict()
            placa = r.get('veiculo')
            litros = r.get('litros')
            if not placa or litros is None:
                continue
            try:
                litros_val = float(litros)
            except Exception:
                continue
            totals[placa] = totals.get(placa, 0) + litros_val

        # Para o mês, usa query filtrada (muito mais eficiente)
        totals_month = {}
        if month_start and month_end:
            try:
                query_month = refuels_ref.where(filter=And([
                    firestore.FieldFilter('timestamp', '>=', month_start),
                    firestore.FieldFilter('timestamp', '<=', month_end)
                ])).limit(50)
                
                docs_month = list(query_month.stream())
                
                for d in docs_month:
                    r = d.to_dict()
                    placa = r.get('veiculo')
                    litros = r.get('litros')
                    if not placa or litros is None:
                        continue
                    try:
                        litros_val = float(litros)
                    except Exception:
                        continue
                    totals_month[placa] = totals_month.get(placa, 0) + litros_val
            except Exception as e:
                print(f"Erro ao buscar refuels do mês: {e}")
                # Fallback: filtra no Python se a query falhar
                for d in docs_total:
                    r = d.to_dict()
                    placa = r.get('veiculo')
                    litros = r.get('litros')
                    ts = r.get('timestamp')
                    if not placa or litros is None or not ts:
                        continue
                    try:
                        litros_val = float(litros)
                        if isinstance(ts, str):
                            t = datetime.fromisoformat(ts)
                            if t.tzinfo is None:
                                t = t.replace(tzinfo=timezone.utc)
                        elif isinstance(ts, datetime):
                            t = ts
                        else:
                            continue
                        if t >= month_start and t <= month_end:
                            totals_month[placa] = totals_month.get(placa, 0) + litros_val
                    except Exception:
                        continue

        # Prepare response sorted by liters desc
        def to_sorted(labels_dict):
            items = sorted(labels_dict.items(), key=lambda x: x[1], reverse=True)
            labels = [i[0] for i in items]
            data = [i[1] for i in items]
            return { 'labels': labels, 'data': data }

        resp = {
            'per_vehicle_total': to_sorted(totals),
            'per_vehicle_month': to_sorted(totals_month)
        }
        return jsonify(resp), 200
    except Exception as e:
        print(f"Erro em get_refuels_summary: {e}")
        return jsonify({"error": "Ocorreu um erro ao agregar abastecimentos."}), 500


@app.route('/api/veiculos/<placa>', methods=['GET'])
def get_veiculo(placa):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    try:
        placa_norm = normalize_plate(placa)
        veiculos_ref = db.collection('veiculos')
        q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa_norm)).limit(1).stream())
        if not q:
            return jsonify({"error": "Veículo não encontrado."}), 404
        v = q[0].to_dict()
        return jsonify(serialize_doc(v)), 200
    except Exception as e:
        print(f"Erro em get_veiculo: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar veículo."}), 500


@app.route('/api/veiculos/<placa>', methods=['PATCH'])
def patch_veiculo(placa):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    data = request.get_json() or {}
    try:
        placa_norm = normalize_plate(placa)
        veiculos_ref = db.collection('veiculos')
        q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa_norm)).limit(1).stream())
        if not q:
            return jsonify({"error": "Veículo não encontrado."}), 404
        vdoc = q[0]
        update_fields = {}
        
        # Permite atualizar modelo
        if 'modelo' in data:
            modelo = data.get('modelo', '').strip()
            update_fields['modelo'] = modelo if modelo else None
            
        # Permite atualizar categoria
        if 'categoria' in data:
            categoria = (data.get('categoria') or 'Outros').strip()
            if not categoria:
                categoria = 'Outros'
            update_fields['categoria'] = categoria
            
        # Permite atualizar visibilidade
        if 'visivel_para_motoristas' in data:
            update_fields['visivel_para_motoristas'] = data.get('visivel_para_motoristas', True)
            
        # Permite atualizar media_kmpl
        if 'media_kmpl' in data:
            try:
                update_fields['media_kmpl'] = float(data.get('media_kmpl')) if data.get('media_kmpl') not in (None, '') else None
            except Exception:
                return jsonify({"error": "Valor inválido para media_kmpl."}), 400
                
        # Permite atualizar ultimo_odometro
        if 'ultimo_odometro' in data:
            try:
                update_fields['ultimo_odometro'] = int(data.get('ultimo_odometro')) if data.get('ultimo_odometro') not in (None, '') else None
            except Exception:
                return jsonify({"error": "Valor inválido para ultimo_odometro."}), 400

        if not update_fields:
            return jsonify({"error": "Nenhum campo para atualizar."}), 400

        vdoc.reference.update(update_fields)
        return jsonify({"message": "Veículo atualizado."}), 200
    except Exception as e:
        print(f"Erro em patch_veiculo: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar veículo."}), 500

@app.route('/api/veiculos/<placa>', methods=['DELETE'])
def delete_veiculo(placa):
    """Excluir veículo"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        placa_norm = normalize_plate(placa)
        veiculos_ref = db.collection('veiculos')
        q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa_norm)).limit(1).stream())
        
        if not q:
            return jsonify({"error": "Veículo não encontrado."}), 404
        
        vdoc = q[0]
        veiculo_data = vdoc.to_dict()
        
        # [SAVE] BACKUP: Se tem documento anexado, mover para pasta de backup
        backup_urls = []
        if veiculo_data.get('documento_url'):
            try:
                # Extrair o caminho do arquivo da URL
                documento_url = veiculo_data['documento_url']
                if 'firebasestorage.googleapis.com' in documento_url:
                    import urllib.parse
                    path_start = documento_url.find('/o/') + 3
                    path_end = documento_url.find('?')
                    if path_start > 2 and path_end > path_start:
                        file_path = urllib.parse.unquote(documento_url[path_start:path_end])
                        backup_url = backup_storage_file(file_path, reason='veiculo_deleted')
                        if backup_url:
                            backup_urls.append({
                                'tipo': 'documento',
                                'url_original': documento_url,
                                'url_backup': backup_url
                            })
                            print(f"[OK] Documento do veículo {placa_norm} salvo em backup")
            except Exception as e:
                print(f" Erro ao fazer backup do documento: {e}")
        
        # Adiciona URLs de backup nos dados de auditoria
        veiculo_data['_backups'] = backup_urls
        
        # Auditoria: registra exclusão do veículo ANTES de deletar
        log_audit('delete', 'veiculos', vdoc.id, old_data=veiculo_data)
        
        # Deletar documento do Firestore
        vdoc.reference.delete()
        print(f"[OK] Veículo {placa_norm} excluído com sucesso")
        
        return jsonify({
            "message": "Veículo excluído com sucesso.",
            "backups": backup_urls
        }), 200
        
    except Exception as e:
        print(f" Erro ao excluir veículo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Ocorreu um erro ao excluir o veículo."}), 500

@app.route('/api/veiculos', methods=['GET'])
def get_veiculos():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        veiculos_ref = db.collection('veiculos').stream()
        veiculos = []
        for doc in veiculos_ref:
            veiculo_data = serialize_doc(doc.to_dict())
            veiculo_data['id'] = doc.id  # Adiciona o ID do documento
            veiculos.append(veiculo_data)
        return jsonify(veiculos), 200

    except Exception as e:
        print(f"Erro ao buscar veículos: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar os veículos."}), 500


@app.route('/api/veiculos', methods=['POST'])
def post_veiculo():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400
    
    placa = (data.get('placa') or '').strip().upper()
    if not placa:
        return jsonify({"error": "Placa é obrigatória."}), 400
    
    try:
        # Verificar se já existe
        veiculos_ref = db.collection('veiculos')
        existing = veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).get()
        if len(list(existing)) > 0:
            return jsonify({"error": "Veículo com esta placa já existe."}), 400
        
        # Criar novo veículo
        categoria = (data.get('categoria') or 'Outros').strip()
        if not categoria:
            categoria = 'Outros'
            
        veiculo_data = {
            'placa': placa,
            'modelo': data.get('modelo', '').strip(),
            'categoria': categoria,
            'visivel_para_motoristas': data.get('visivel_para_motoristas', True),
            'timestamp': datetime.now(timezone.utc),
            'documento_url': None,  # Campo para documento do veículo
            'status_ativo': True    # Status ativo/inativo do veículo
        }
        
        if 'media_kmpl' in data and data.get('media_kmpl'):
            try:
                veiculo_data['media_kmpl'] = float(data.get('media_kmpl'))
            except:
                pass
        
        doc_ref = veiculos_ref.add(veiculo_data)
        
        # Auditoria: registra criação do veículo
        log_audit('create', 'veiculos', doc_ref[1].id, new_data=veiculo_data)
        
        return jsonify({"message": "Veículo cadastrado com sucesso.", "placa": placa}), 201
        
    except Exception as e:
        print(f"Erro ao cadastrar veículo: {e}")
        return jsonify({"error": "Ocorreu um erro ao cadastrar o veículo."}), 500


@app.route('/api/veiculos/<veiculo_id>/upload-documento', methods=['POST'])
@requires_auth
def upload_documento_veiculo(veiculo_id):
    """Upload documento do veículo"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        # Verificar se veículo existe
        veiculo_ref = db.collection('veiculos').document(veiculo_id)
        veiculo_doc = veiculo_ref.get()
        
        if not veiculo_doc.exists:
            return jsonify({"error": "Veículo não encontrado."}), 404
        
        veiculo_data = veiculo_doc.to_dict()
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo foi enviado."}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Nome do arquivo está vazio."}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": "Tipo de arquivo não permitido. Use PDF, JPG ou PNG."}), 400
        
        # DELETAR todos os arquivos antigos de documento deste veículo
        prefix = f"veiculos/{veiculo_id}/"
        blobs_to_delete = bucket.list_blobs(prefix=prefix)
        for old_blob in blobs_to_delete:
            if 'documento' in old_blob.name:
                old_blob.delete()
                print(f"[DELETE] Arquivo antigo deletado: {old_blob.name}")
        
        # Criar nome do arquivo no Storage com timestamp para evitar cache
        timestamp = int(datetime.now().timestamp())
        blob_name = f"veiculos/{veiculo_id}/documento_{timestamp}.{file_ext}"
        blob = bucket.blob(blob_name)
        
        # Upload para Firebase Storage
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Tornar o arquivo público
        blob.make_public()
        
        # Obter URL pública
        documento_url = blob.public_url
        
        print(f"[OK] Documento salvo em: {blob_name}")
        print(f" URL gerada: {documento_url}")
        
        # Atualizar documento do veículo com a URL
        veiculo_ref.update({
            'documento_url': documento_url
        })
        
        # Mensagem diferente se foi atualização ou novo upload
        mensagem = "Documento atualizado com sucesso." if veiculo_data.get('documento_url') else "Documento enviado com sucesso."
        
        return jsonify({
            "message": mensagem,
            "documento_url": documento_url
        }), 200
        
    except Exception as e:
        print(f"Erro ao fazer upload do documento: {e}")
        return jsonify({"error": "Ocorreu um erro ao fazer upload do documento."}), 500


@app.route('/api/veiculos/<veiculo_id>/documento', methods=['GET'])
@requires_auth_historico
def get_documento_veiculo(veiculo_id):
    """Get documento URL for a veiculo"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        veiculo_ref = db.collection('veiculos').document(veiculo_id)
        veiculo_doc = veiculo_ref.get()
        
        if not veiculo_doc.exists:
            return jsonify({"error": "Veículo não encontrado."}), 404
        
        veiculo_data = veiculo_doc.to_dict()
        documento_url = veiculo_data.get('documento_url')
        
        if not documento_url:
            return jsonify({"error": "Documento não foi enviado para este veículo."}), 404
        
        return jsonify({
            "documento_url": documento_url
        }), 200
        
    except Exception as e:
        print(f"Erro ao buscar documento: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar o documento."}), 500


@app.route('/api/veiculos/<veiculo_id>/status', methods=['PATCH'])
@requires_auth
def toggle_veiculo_status(veiculo_id):
    """Toggle veiculo active status - aceita ID do documento ou placa"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        # Tentar buscar por ID do documento primeiro
        veiculo_ref = db.collection('veiculos').document(veiculo_id)
        veiculo_doc = veiculo_ref.get()
        
        # Se não encontrar por ID, tentar por placa
        if not veiculo_doc.exists:
            print(f" Veículo não encontrado por ID: {veiculo_id}, tentando por placa...")
            placas_query = db.collection('veiculos').where(
                filter=firestore.FieldFilter('placa', '==', veiculo_id.upper())
            ).limit(1).stream()
            
            placas_docs = list(placas_query)
            
            if not placas_docs:
                return jsonify({"error": "Veículo não encontrado."}), 404
            
            # Usar o documento encontrado pela placa
            veiculo_doc = placas_docs[0]
            veiculo_ref = veiculo_doc.reference
        
        # Obter novo status do body
        data = request.get_json()
        
        if 'status_ativo' not in data:
            return jsonify({"error": "Campo 'status_ativo' é obrigatório."}), 400
        
        status_ativo = data['status_ativo']
        
        if not isinstance(status_ativo, bool):
            return jsonify({"error": "Campo 'status_ativo' deve ser booleano."}), 400
        
        # Atualizar status
        veiculo_ref.update({
            'status_ativo': status_ativo
        })
        
        status_texto = "ativo" if status_ativo else "inativo"
        
        return jsonify({
            "message": f"Veículo marcado como {status_texto}.",
            "status_ativo": status_ativo
        }), 200
        
    except Exception as e:
        print(f"Erro ao atualizar status do veículo: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar o status."}), 500


import time

# Cache simples para dashboard (1 hora = 3600 segundos)
# Não é limpo automaticamente - use o botão "Atualizar" no dashboard
dashboard_cache = {}
CACHE_DURATION = 3600  # 1 hora

@app.route('/api/dashboard_stats', methods=['GET'])
def get_dashboard_stats():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        now = time.time()
        
        # Se o frontend enviar ?month=YYYY-MM, usaremos esse intervalo apenas para os charts mensais
        month_param = request.args.get('month')  # formato esperado: YYYY-MM
        
        # OTIMIZAÇÃO: Verifica cache (5 minutos) - MAS CONSIDERA O MÊS FILTRADO
        # Cache deve ser diferente para cada mês
        cache_key = month_param if month_param else 'default'
        
        # [OK] CACHE ATIVO: 5 minutos (300s) - Atualiza apenas quando necessário
        # Invalidado automaticamente em novas saídas/chegadas
        # Garante que a chave existe no cache
        if cache_key not in dashboard_cache:
            dashboard_cache[cache_key] = {'data': None, 'expires': 0}
        
        if dashboard_cache[cache_key].get('expires', 0) > now and dashboard_cache[cache_key].get('data'):
            print(f'[OK] Dashboard do CACHE (mês: {cache_key}) - economia ~160 leituras')
            return jsonify(dashboard_cache[cache_key]['data']), 200
        print(f' Recalculando dashboard (cache expirado: {cache_key})')
            
        # OTIMIZAÇÃO: Lê apenas motoristas e veículos (poucos docs)
        motoristas_docs = list(db.collection('motoristas').stream())
        veiculos_docs = list(db.collection('veiculos').stream())

        now_datetime = datetime.now(timezone.utc)  # Para comparações de data
        
        # [OK] CORREÇÃO: start_of_today deve ser 00:00 no fuso LOCAL, depois converter para UTC
        now_local = datetime.now(LOCAL_TZ)
        start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_today = start_of_today_local.astimezone(timezone.utc)  # Converte para UTC
        print(f"[TIME] Hoje LOCAL: {start_of_today_local} → UTC: {start_of_today}")
        
        month_start = None
        month_end = None
        if month_param:
            try:
                year, month = month_param.split('-')
                year = int(year)
                month = int(month)
                print(f"[SEARCH] Filtrando dashboard por mês: {month_param} (ano={year}, mês={month})")
                
                # início do mês no fuso local (00:00 do primeiro dia)
                month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                # fim do mês: primeiro dia do próximo mês menos 1 segundo
                if month == 12:
                    next_month_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                else:
                    next_month_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                month_end_local = next_month_local - timedelta(seconds=1)
                
                print(f"[DATE] Período local: {month_start_local} até {month_end_local}")
                
                # converter para UTC para comparar com timestamps armazenados em UTC
                month_start = month_start_local.astimezone(timezone.utc)
                month_end = month_end_local.astimezone(timezone.utc)
                
                print(f"[DATE] Período UTC: {month_start} até {month_end}")
            except Exception as e:
                print(f" Erro ao parsear mês: {e}")
                month_start = None
                month_end = None
        
        # OTIMIZAÇÃO: Lê SOMENTE o período necessário (mês específico ou 30 dias)
        window_start = month_start if month_start else (now_datetime - timedelta(days=30))
        window_end = month_end if month_end else now_datetime

        # OTIMIZAÇÃO: Query com LIMIT AGRESSIVO (50 docs max)
        print(f"[FIND] Buscando saídas entre {window_start} e {window_end}")
        query_mes = db.collection('saidas').where(filter=And([
            firestore.FieldFilter('timestampSaida', '>=', window_start),
            firestore.FieldFilter('timestampSaida', '<=', window_end)
        ])).limit(50)  # [OK] REDUZIDO PARA 50 (economia massiva)
        saidas_mes_docs = list(query_mes.stream())
        saidas_mes = [doc.to_dict() for doc in saidas_mes_docs]
        print(f"[OK] Encontrou {len(saidas_mes)} saídas no período (LIMIT 50)")
        
        # DEBUG: Mostra as primeiras 3 datas para verificar
        if saidas_mes:
            for i, s in enumerate(saidas_mes[:3]):
                ts = s.get('timestampSaida')
                print(f"  [DATE] Saída {i+1}: {ts} (tipo: {type(ts)})")
        elif month_param:
            # Se não encontrou nada no mês filtrado, mostra TODAS as datas disponíveis
            print(f" Não encontrou registros para {month_param}. Listando TODAS as datas disponíveis:")
            all_saidas = list(db.collection('saidas').limit(50).stream())
            for i, doc in enumerate(all_saidas[:10]):
                data = doc.to_dict()
                ts = data.get('timestampSaida')
                print(f"  [DATE] Registro {i+1}: {ts}")
        
        # [OK] CORREÇÃO: Viagens HOJE deve ser uma query SEPARADA (não usar saidas_mes)
        # porque "HOJE" sempre mostra o dia atual, independente do filtro de mês
        end_of_today = start_of_today + timedelta(days=1) - timedelta(seconds=1)
        query_hoje = db.collection('saidas').where(filter=And([
            firestore.FieldFilter('timestampSaida', '>=', start_of_today),
            firestore.FieldFilter('timestampSaida', '<=', end_of_today)
        ])).stream()
        viagens_hoje = len(list(query_hoje))
        print(f"[STATS] Viagens HOJE: {viagens_hoje} (entre {start_of_today} e {end_of_today})")
        
        viagens_em_curso = 0
        total_horas_em_rua_seconds = 0

        # Processa apenas as saídas do mês para estatísticas mensais
        for saida in saidas_mes:
            timestamp_saida = saida.get('timestampSaida')
            if not timestamp_saida or not isinstance(timestamp_saida, datetime):
                continue

            if saida.get('status') == 'em_curso':
                viagens_em_curso += 1

            if saida.get('status') == 'finalizada':
                timestamp_chegada = saida.get('timestampChegada')
                if timestamp_chegada and isinstance(timestamp_chegada, datetime):
                    duracao = timestamp_chegada - timestamp_saida
                    total_horas_em_rua_seconds += duracao.total_seconds()

        # Recalcule as listas do mês usando os dados eficientes
        viagens_mes_motoristas = []
        viagens_mes_veiculos = []
        for saida in saidas_mes:
            if saida.get('motorista'):
                viagens_mes_motoristas.append(saida.get('motorista'))
            if saida.get('veiculo'):
                viagens_mes_veiculos.append(saida.get('veiculo'))

        motorista_do_mes = Counter(viagens_mes_motoristas).most_common(1)
        veiculo_do_mes = Counter(viagens_mes_veiculos).most_common(1)

        total_horas = int(total_horas_em_rua_seconds // 3600)
        total_minutos = int((total_horas_em_rua_seconds % 3600) // 60)
        horas_formatadas = f"{total_horas:02d}:{total_minutos:02d}"

        # ---- ESTA É A GRANDE MUDANÇA ----
        # Substitua seus cálculos de totais por este bloco:
        
        # Cálculo dos TOTAIS GERAIS (Lendo os contadores, não a coleção 'saidas')
        viagens_por_veiculo_total = {}
        for doc in veiculos_docs:
            data = doc.to_dict()
            placa = data.get('placa')
            total = data.get('viagens_totais', 0) # Pega o total do campo
            if placa and total > 0:
                viagens_por_veiculo_total[placa] = total

        viagens_por_motorista_total = {}
        for doc in motoristas_docs:
            data = doc.to_dict()
            nome = data.get('nome')
            total = data.get('viagens_totais', 0) # Pega o total do campo
            if nome and total > 0:
                viagens_por_motorista_total[nome] = total
        
        # Agregados do mês (como você já fazia, mas com a consulta eficiente)
        viagens_por_veiculo_mes = dict(Counter(viagens_mes_veiculos))
        viagens_por_motorista_mes = dict(Counter(viagens_mes_motoristas))

        # OTIMIZAÇÃO: Histórico recente - limit reduzido de 50 para 20 (60% economia)
        # Dashboard não precisa mostrar mais de 20 registros recentes
        query_hist = db.collection('saidas').order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(20)
        historico_recente_docs = query_hist.stream()
        historico_recente = []
        for doc in historico_recente_docs:
            data = serialize_doc(doc.to_dict())
            data['id'] = doc.id  # Adiciona o ID do documento
            historico_recente.append(data)
        
        # Debug: verificar se os IDs estão sendo adicionados
        if historico_recente:
            print(f'[LIST] Histórico recente: {len(historico_recente)} registros')
            print(f'[SEARCH] Primeiro registro tem ID? {historico_recente[0].get("id") is not None}')
        
        historico_final = sorted(historico_recente, key=lambda x: x.get('status') == 'em_curso', reverse=True)


        stats = {
            "viagens_em_curso": viagens_em_curso,
            "viagens_hoje": viagens_hoje,
            "total_motoristas": len(motoristas_docs),
            "total_veiculos": len(veiculos_docs),
            "motorista_do_mes": {
                "nome": motorista_do_mes[0][0] if motorista_do_mes else "N/A",
                "viagens": motorista_do_mes[0][1] if motorista_do_mes else 0
            },
            "veiculo_do_mes": {
                "placa": veiculo_do_mes[0][0] if veiculo_do_mes else "N/A",
                "viagens": veiculo_do_mes[0][1] if veiculo_do_mes else 0
            },
            "total_horas_na_rua": horas_formatadas,
            
            # Gráficos do Mês (já estão corretos)
            "chart_viagens_por_veiculo": {
                "labels": list(viagens_por_veiculo_mes.keys()),
                "data": list(viagens_por_veiculo_mes.values())
            },
            "chart_viagens_por_motorista": {
                "labels": list(viagens_por_motorista_mes.keys()),
                "data": list(viagens_por_motorista_mes.values())
            },

            # Gráficos de Total Geral (AGORA SÃO EFICIENTES)
            "chart_viagens_por_veiculo_total": {
                "labels": list(viagens_por_veiculo_total.keys()),
                "data": list(viagens_por_veiculo_total.values())
            },
            "chart_viagens_por_motorista_total": {
                "labels": list(viagens_por_motorista_total.keys()),
                "data": list(viagens_por_motorista_total.values())
            },
            
            "historico_recente": historico_final
        }

        # Salva no cache (5 minutos) - POR MÊS
        cache_timestamp = time.time()
        
        # [OK] CACHE REATIVADO: 5 minutos (300 segundos)
        # Garante que a chave existe antes de salvar
        if cache_key not in dashboard_cache:
            dashboard_cache[cache_key] = {}
            
        dashboard_cache[cache_key]['data'] = stats
        dashboard_cache[cache_key]['expires'] = cache_timestamp + 300  # 5 minutos
        print(f' Dashboard no cache por 5min (mês: {cache_key})')

        return jsonify(stats)

    except Exception as e:
        print(f"Erro em get_dashboard_stats: {e}")
        return jsonify({"error": "Ocorreu um erro ao calcular as estatísticas."}), 500


@app.route('/api/dashboard_cache/clear', methods=['POST'])
@requires_auth
def clear_dashboard_cache():
    """Limpa o cache do dashboard manualmente"""
    try:
        global dashboard_cache
        dashboard_cache.clear()
        print(f'[DELETE] Cache do dashboard limpo manualmente')
        return jsonify({"message": "Cache limpo com sucesso"}), 200
    except Exception as e:
        print(f"Erro ao limpar cache: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dashboard_realtime', methods=['GET'])
def get_dashboard_realtime():
    """
    Retorna estatísticas em TEMPO REAL (SEM CACHE)
    Para atualização instantânea de veículos em curso e viagens de hoje
    """
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        now_datetime = datetime.now(timezone.utc)
        start_of_today = now_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Busca APENAS saídas de hoje
        query_hoje = db.collection('saidas').where(
            filter=firestore.FieldFilter('timestampSaida', '>=', start_of_today)
        ).stream()
        
        saidas_hoje = [doc.to_dict() for doc in query_hoje]
        
        # Calcula estatísticas
        viagens_em_curso = sum(1 for s in saidas_hoje if s.get('status') == 'em_curso')
        viagens_hoje = len(saidas_hoje)
        
        # Calcula total de horas na rua (apenas viagens finalizadas hoje)
        total_horas_em_rua_seconds = 0
        for saida in saidas_hoje:
            if saida.get('status') == 'finalizada':
                ts_saida = saida.get('timestampSaida')
                ts_chegada = saida.get('timestampChegada')
                if ts_saida and ts_chegada and isinstance(ts_saida, datetime) and isinstance(ts_chegada, datetime):
                    delta = (ts_chegada - ts_saida).total_seconds()
                    if delta > 0:
                        total_horas_em_rua_seconds += delta
        
        # Formata horas
        total_horas = int(total_horas_em_rua_seconds // 3600)
        total_minutos = int((total_horas_em_rua_seconds % 3600) // 60)
        total_horas_na_rua = f'{total_horas:02d}:{total_minutos:02d}'
        
        result = {
            'viagens_em_curso': viagens_em_curso,
            'viagens_hoje': viagens_hoje,
            'total_horas_na_rua': total_horas_na_rua,
            'timestamp': now_datetime.isoformat()
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Erro em get_dashboard_realtime: {e}")
        return jsonify({"error": "Ocorreu um erro ao calcular as estatísticas."}), 500


# --- Lógica de Negócio ---

def handle_saida(veiculo_placa, motorista_nome, solicitante, trajeto, horario=None, veiculo_categoria='Outros', motorista_secao='Outros'):
    try:
        # Normaliza placa recebida
        veiculo_placa = normalize_plate(veiculo_placa) if veiculo_placa else veiculo_placa
        
        #  PROTEÇÃO ANTI-DUPLICATA: Verifica se já existe saída recente (últimos 2 minutos)
        now_utc = datetime.now(timezone.utc)
        dois_minutos_atras = now_utc - timedelta(minutes=2)
        
        saidas_ref = db.collection('saidas')
        duplicata_query = saidas_ref.where(filter=And([
            firestore.FieldFilter('veiculo', '==', veiculo_placa),
            firestore.FieldFilter('motorista', '==', motorista_nome),
            firestore.FieldFilter('timestampSaida', '>=', dois_minutos_atras)
        ])).limit(1).stream()
        
        saidas_recentes = list(duplicata_query)
        if len(saidas_recentes) > 0:
            saida_duplicada = saidas_recentes[0].to_dict()
            horario_duplicata = saida_duplicada.get('horarioSaida', 'N/A')
            return f" Saída duplicada bloqueada! Este veículo com este motorista já tem um registro de saída recente (às {horario_duplicata}). Aguarde 2 minutos para registrar nova saída."
        
        # REGRA DE NEGÓCIO: Verifica se o veículo já está em curso
        viagem_em_curso = saidas_ref.where(filter=And([
            firestore.FieldFilter('veiculo', '==', veiculo_placa),
            firestore.FieldFilter('status', '==', 'em_curso')
        ])).limit(1).stream()
        
        if len(list(viagem_em_curso)) > 0:
            return f"O veículo {veiculo_placa} já está em curso e não pode sair novamente."

        # 1. Verificar/Registar Motorista E INCREMENTAR
        motoristas_ref = db.collection('motoristas')
        motorista_query = motoristas_ref.where(filter=firestore.FieldFilter('nome', '==', motorista_nome)).limit(1).stream()
        motorista_docs = list(motorista_query)
        
        if not motorista_docs:
            # Motorista é novo. Cria o documento já com o total 1.
            motoristas_ref.add({
                'nome': motorista_nome,
                'secao': motorista_secao,
                'status': 'nao_credenciado',
                'dataCadastro': firestore.SERVER_TIMESTAMP,
                'viagens_totais': 1  # Inicia a contagem em 1
            })
        else:
            # Motorista já existe. Incrementa o total.
            motorista_ref = motorista_docs[0].reference
            motorista_ref.update({
                'viagens_totais': firestore.Increment(1)
            })

        # 2. Verificar/Registar Veículo E INCREMENTAR
        veiculos_ref = db.collection('veiculos')
        veiculo_query = veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo_placa)).limit(1).stream()
        veiculo_docs = list(veiculo_query)

        if not veiculo_docs:
            # Veículo é novo. Cria o documento já com o total 1 e campos necessários.
            veiculos_ref.add({
                'placa': veiculo_placa,
                'tipo': 'Não especificado',  # Campo padrão
                'modelo': 'Não especificado',  # Campo padrão
                'categoria': veiculo_categoria,
                'visivel_para_motoristas': True,
                'ano': None,
                'km_atual': 0,
                'status_ativo': True,  # Ativo por padrão
                'dataCadastro': firestore.SERVER_TIMESTAMP,
                'viagens_totais': 1  # Inicia a contagem em 1
            })
        else:
            # Veículo já existe. Incrementa o total.
            veiculo_ref = veiculo_docs[0].reference
            veiculo_ref.update({
                'viagens_totais': firestore.Increment(1)
            })

        # 3. Criar Registo de Saída
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(LOCAL_TZ)

        horario_saida_str = horario
        timestamp_saida = now_local  # Usa horário local, não UTC

        if horario:  # Se um horário foi fornecido
            try:
                horario_obj = datetime.strptime(horario, "%H:%M").time()
                # Cria o datetime no fuso horário local (dia de hoje + horário informado)
                local_dt = now_local.replace(hour=horario_obj.hour, minute=horario_obj.minute, second=0, microsecond=0)
                timestamp_saida = local_dt  # Mantém em horário local
                horario_saida_str = horario_obj.strftime("%H:%M")
            except ValueError:
                # Se o formato do horário for inválido, usa a hora atual como fallback
                timestamp_saida = now_local
                horario_saida_str = now_local.strftime("%H:%M")
        else:  # Se nenhum horário foi fornecido
            timestamp_saida = now_local
            horario_saida_str = now_local.strftime("%H:%M")

        saidas_ref.add({
            'veiculo': veiculo_placa,
            'motorista': motorista_nome,
            'solicitante': solicitante,
            'trajeto': trajeto,
            'horarioSaida': horario_saida_str,
            'timestampSaida': timestamp_saida,
            'status': 'em_curso',
            'horarioChegada': "",
            'timestampChegada': None
        })

        # [OK] INVALIDA O CACHE DO DASHBOARD e HISTÓRICO após nova saída
        dashboard_cache.clear()
        historico_cache.clear()  # Limpa TODAS as chaves do cache
        print("[DELETE] Cache do dashboard e histórico invalidados após nova saída")

        return f"Saída do veículo {veiculo_placa} registrada com sucesso."

    except Exception as e:
        print(f"Erro no handle_saida: {e}")
        return "Ocorreu um erro interno ao registrar a saída."

def handle_chegada(veiculo_placa, horario=None, litros=None, odometro=None):
    try:
        # Normaliza placa recebida
        veiculo_placa = normalize_plate(veiculo_placa) if veiculo_placa else veiculo_placa
        saidas_ref = db.collection('saidas')
        query = saidas_ref.where(filter=And([
            firestore.FieldFilter('veiculo', '==', veiculo_placa),
            firestore.FieldFilter('status', '==', 'em_curso')
        ])).order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(1)
        
        viagens = list(query.stream())

        if not viagens:
            return f"Nenhum registro de saída 'em curso' encontrado para o veículo {veiculo_placa}."

        viagem_doc = viagens[0]
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(LOCAL_TZ)

        horario_chegada_str = horario
        timestamp_chegada = now_utc

        if horario:  # Se um horário foi fornecido
            try:
                horario_obj = datetime.strptime(horario, "%H:%M").time()
                # Cria o datetime no fuso horário local
                local_dt = now_local.replace(hour=horario_obj.hour, minute=horario_obj.minute, second=0, microsecond=0)
                # Converte para UTC para armazenamento
                timestamp_chegada = local_dt.astimezone(timezone.utc)
                horario_chegada_str = horario_obj.strftime("%H:%M")
            except ValueError:
                # Se o formato do horário for inválido, usa a hora atual como fallback
                timestamp_chegada = now_utc
                horario_chegada_str = now_local.strftime("%H:%M")
        else:  # Se nenhum horário foi fornecido
            timestamp_chegada = now_utc
            horario_chegada_str = now_local.strftime("%H:%M")

        viagem_doc.reference.update({
            'horarioChegada': horario_chegada_str,
            'timestampChegada': timestamp_chegada,
            'status': 'finalizada'
        })

        return_msg = f"Chegada do veículo {veiculo_placa} registrada com sucesso. Viagem finalizada."

        # Se litros/odometro foram enviados via API (passados como parâmetros), registra um refuel
        try:
            litros_val = litros
            odometro_val = odometro
            # Se não vierem via parâmetros, tenta pegar do body como fallback
            if litros_val is None and request.json:
                litros_val = request.json.get('litros')
            if odometro_val is None and request.json:
                odometro_val = request.json.get('odometro')

            if litros_val is not None or odometro_val is not None:
                ref = db.collection('refuels').document()
                ref.set({
                    'veiculo': veiculo_placa,
                    'motorista': viagem_doc.to_dict().get('motorista'),
                    'litros': float(litros_val) if litros_val is not None else None,
                    'odometro': int(odometro_val) if odometro_val is not None else None,
                    'observacao': '',
                    'timestamp': timestamp_chegada
                })
                
                # Verifica/Cria o veículo se não existir
                veiculos_ref = db.collection('veiculos')
                q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo_placa)).limit(1).stream())
                
                if not q:
                    # Veículo não existe, criar com campos completos
                    veiculos_ref.add({
                        'placa': veiculo_placa,
                        'tipo': 'Não especificado',
                        'modelo': 'Não especificado',
                        'ano': None,
                        'km_atual': int(odometro_val) if odometro_val is not None else 0,
                        'ultimo_odometro': int(odometro_val) if odometro_val is not None else None,
                        'status_ativo': True,
                        'dataCadastro': firestore.SERVER_TIMESTAMP,
                        'viagens_totais': 0
                    })
                    print(f"[OK] Veículo {veiculo_placa} criado automaticamente via abastecimento")
                elif odometro_val is not None:
                    # Atualiza o ultimo odometro no veiculo existente
                    vdoc = q[0]
                    vdoc.reference.update({'ultimo_odometro': int(odometro_val)})
                
                return_msg += ' Abastecimento registrado (litros/odômetro).'
        except Exception as e:
            print(f"Erro ao registrar refuel na chegada: {e}")
            # não falha a chegada por causa do refuel

        # [OK] INVALIDA O CACHE DO DASHBOARD e HISTÓRICO após chegada
        dashboard_cache.clear()
        historico_cache.clear()  # Limpa TODAS as chaves do cache
        print("[DELETE] Cache do dashboard e histórico invalidados após chegada")

        return return_msg

    except Exception as e:
        print(f"Erro no handle_chegada: {e}")
        return "Ocorreu um erro interno ao registrar a chegada."


# ========================================
# ROTAS - KM MENSAL
# ========================================

@app.route('/api/km-mensal', methods=['GET'])
@requires_auth
def get_km_mensal():
    """Lista todos os registros de KM mensal, opcionalmente filtrados por veículo, mês ou ano."""
    print("[SEARCH] [KM MENSAL] Iniciando requisição GET /api/km-mensal")
    
    if not db:
        print(" [KM MENSAL] Erro: DB não conectado")
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        placa = request.args.get('placa')
        mes_ano = request.args.get('mes_ano')  # formato: YYYY-MM
        ano = request.args.get('ano')  # formato: YYYY (novo filtro)
        
        print(f"[LIST] [KM MENSAL] Filtros: placa={placa}, mes_ano={mes_ano}, ano={ano}")
        
        km_ref = db.collection('km_mensal')
        
        # Aplica filtros se fornecidos
        if placa:
            km_ref = km_ref.where(filter=firestore.FieldFilter('placa', '==', placa.upper()))
        if mes_ano:
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '==', mes_ano))
        elif ano:
            # Filtrar por range de datas do ano
            # mes_ano >= '2025-01' AND mes_ano <= '2025-12'
            ano_inicio = f"{ano}-01"
            ano_fim = f"{ano}-12"
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '>=', ano_inicio))
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '<=', ano_fim))
        
        # Ordena se possível (pode falhar se faltarem índices)
        try:
            if not placa and not mes_ano and not ano:
                print("[STATS] [KM MENSAL] Ordenando no Firestore")
                km_ref = km_ref.order_by('mes_ano', direction=firestore.Query.DESCENDING)
        except:
            print(" [KM MENSAL] Não foi possível ordenar no Firestore")
        
        print("[RELOAD] [KM MENSAL] Buscando documentos...")
        docs = km_ref.stream()
        registros = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # Serializa timestamp se existir
            if 'data_registro' in data and isinstance(data['data_registro'], datetime):
                data['data_registro'] = data['data_registro'].isoformat()
            registros.append(data)
        
        print(f"[OK] [KM MENSAL] Encontrados {len(registros)} registros")
        
        # Ordena em Python sempre
        print("[STATS] [KM MENSAL] Ordenando em Python")
        registros.sort(key=lambda x: x.get('mes_ano', ''), reverse=True)
        
        return jsonify(registros), 200
    except Exception as e:
        print(f" [KM MENSAL] Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/km-mensal', methods=['POST'])
@requires_auth
def post_km_mensal():
    """Cria ou atualiza um registro de KM mensal (UPSERT)."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    placa = (data.get('placa') or '').strip().upper()
    mes_ano = (data.get('mes_ano') or '').strip()  # formato: YYYY-MM
    km_valor = data.get('km_valor')
    observacao = (data.get('observacao') or '').strip()
    
    if not placa or not mes_ano or km_valor is None:
        return jsonify({"error": "Campos 'placa', 'mes_ano' e 'km_valor' são obrigatórios."}), 400
    
    # Valida formato mes_ano (YYYY-MM)
    if not re.match(r'^\d{4}-\d{2}$', mes_ano):
        return jsonify({"error": "Formato de 'mes_ano' inválido. Use YYYY-MM."}), 400
    
    try:
        km_ref = db.collection('km_mensal')
        
        # Verifica se já existe registro para este veículo neste mês
        existing = list(km_ref.where(filter=And([
            firestore.FieldFilter('placa', '==', placa),
            firestore.FieldFilter('mes_ano', '==', mes_ano)
        ])).limit(1).stream())
        
        doc_data = {
            'placa': placa,
            'mes_ano': mes_ano,
            'km_valor': int(km_valor),
            'observacao': observacao,
            'ativo': True,
            'data_registro': firestore.SERVER_TIMESTAMP
        }
        
        if existing:
            # Atualiza o registro existente
            existing_doc = existing[0]
            existing_doc.reference.update({
                'km_valor': int(km_valor),
                'observacao': observacao,
                'data_registro': firestore.SERVER_TIMESTAMP
            })
            return jsonify({"message": "Registro de KM atualizado com sucesso."}), 200
        else:
            # Cria novo registro
            km_ref.add(doc_data)
            return jsonify({"message": "Registro de KM criado com sucesso."}), 201
            
    except Exception as e:
        print(f"Erro ao salvar KM mensal: {e}")
        return jsonify({"error": "Erro ao salvar registro de KM mensal."}), 500


@app.route('/api/km-mensal/<registro_id>', methods=['PUT'])
@requires_auth
def update_km_mensal(registro_id):
    """Atualiza um registro de KM mensal existente."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    
    try:
        km_ref = db.collection('km_mensal').document(registro_id)
        km_doc = km_ref.get()
        
        if not km_doc.exists:
            return jsonify({"error": "Registro não encontrado."}), 404
        
        # Campos atualizáveis
        update_data = {}
        
        if 'ativo' in data:
            update_data['ativo'] = bool(data['ativo'])
        if 'km_valor' in data:
            update_data['km_valor'] = int(data['km_valor']) if data['km_valor'] is not None else None
        if 'observacao' in data:
            update_data['observacao'] = data['observacao'].strip()
        
        update_data['data_registro'] = firestore.SERVER_TIMESTAMP
        
        if update_data:
            km_ref.update(update_data)
            return jsonify({"message": "Registro atualizado com sucesso."}), 200
        else:
            return jsonify({"message": "Nenhum campo para atualizar."}), 200
            
    except Exception as e:
        print(f"Erro ao atualizar KM mensal: {e}")
        return jsonify({"error": "Erro ao atualizar registro."}), 500


@app.route('/api/km-mensal/<registro_id>', methods=['DELETE'])
@requires_auth
def delete_km_mensal(registro_id):
    """Deleta um registro de KM mensal."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        km_ref = db.collection('km_mensal').document(registro_id)
        km_doc = km_ref.get()
        
        if not km_doc.exists:
            return jsonify({"error": "Registro não encontrado."}), 404
        
        km_ref.delete()
        return jsonify({"message": "Registro deletado com sucesso."}), 200
        
    except Exception as e:
        print(f"Erro ao deletar KM mensal: {e}")
        return jsonify({"error": "Erro ao deletar registro."}), 500


# ========================================
# ROTAS - MULTAS
# ========================================

@app.route('/api/multas', methods=['GET'])
@requires_auth
def get_multas():
    """Lista todas as multas, opcionalmente filtradas por veículo ou status."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        placa = request.args.get('placa')
        status = request.args.get('status')  # pendente, paga, contestada
        
        multas_ref = db.collection('multas')
        
        # Aplica filtros se fornecidos
        if placa:
            multas_ref = multas_ref.where(filter=firestore.FieldFilter('placa', '==', placa.upper()))
        if status:
            multas_ref = multas_ref.where(filter=firestore.FieldFilter('status', '==', status))
        
        # Ordena por data de vencimento (mais próxima primeiro)
        multas_ref = multas_ref.order_by('data_vencimento')
        
        docs = multas_ref.stream()
        multas = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # Serializa datas
            for field in ['data_infracao', 'data_vencimento', 'data_pagamento', 'data_registro']:
                if field in data and isinstance(data[field], datetime):
                    data[field] = data[field].isoformat()
            multas.append(data)
        
        return jsonify(multas), 200
    except Exception as e:
        print(f"Erro ao buscar multas: {e}")
        return jsonify({"error": "Erro ao buscar multas."}), 500


@app.route('/api/multas', methods=['POST'])
@requires_auth
def post_multa():
    """Cria uma nova multa."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    placa = (data.get('placa') or '').strip().upper()
    descricao = (data.get('descricao') or '').strip()
    data_infracao = (data.get('data_infracao') or '').strip()
    data_vencimento = (data.get('data_vencimento') or '').strip()
    valor = data.get('valor')
    motorista = (data.get('motorista') or '').strip()
    local = (data.get('local') or '').strip()
    observacao = (data.get('observacao') or '').strip()
    status = (data.get('status') or 'pendente').strip()
    
    if not placa or not descricao or not data_vencimento or valor is None:
        return jsonify({"error": "Campos 'placa', 'descricao', 'data_vencimento' e 'valor' são obrigatórios."}), 400
    
    try:
        # Converte datas para datetime
        dt_infracao = None
        if data_infracao:
            dt_infracao = datetime.fromisoformat(data_infracao.replace('Z', '+00:00'))
        
        dt_vencimento = datetime.fromisoformat(data_vencimento.replace('Z', '+00:00'))
        
        # Cria a multa
        multas_ref = db.collection('multas')
        doc_data = {
            'placa': placa,
            'descricao': descricao,
            'data_infracao': dt_infracao,
            'data_vencimento': dt_vencimento,
            'valor': float(valor),
            'motorista': motorista,
            'local': local,
            'observacao': observacao,
            'status': status,
            'data_registro': firestore.SERVER_TIMESTAMP,
            'data_pagamento': None
        }
        
        multas_ref.add(doc_data)
        
        return jsonify({"message": "Multa registrada com sucesso."}), 201
    except Exception as e:
        print(f"Erro ao criar multa: {e}")
        return jsonify({"error": "Erro ao criar multa."}), 500


@app.route('/api/multas/<multa_id>', methods=['PUT'])
@requires_auth
def update_multa(multa_id):
    """Atualiza uma multa existente."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    data = request.get_json() or {}
    
    try:
        multa_ref = db.collection('multas').document(multa_id)
        multa_doc = multa_ref.get()
        
        if not multa_doc.exists:
            return jsonify({"error": "Multa não encontrada."}), 404
        
        update_data = {}
        
        # Campos atualizáveis
        if 'descricao' in data:
            update_data['descricao'] = data['descricao'].strip()
        if 'data_infracao' in data and data['data_infracao']:
            update_data['data_infracao'] = datetime.fromisoformat(data['data_infracao'].replace('Z', '+00:00'))
        if 'data_vencimento' in data and data['data_vencimento']:
            update_data['data_vencimento'] = datetime.fromisoformat(data['data_vencimento'].replace('Z', '+00:00'))
        if 'valor' in data:
            update_data['valor'] = float(data['valor'])
        if 'motorista' in data:
            update_data['motorista'] = data['motorista'].strip()
        if 'local' in data:
            update_data['local'] = data['local'].strip()
        if 'observacao' in data:
            update_data['observacao'] = data['observacao'].strip()
        if 'status' in data:
            update_data['status'] = data['status'].strip()
            # Se marcar como paga, registra data de pagamento
            if data['status'] == 'paga' and 'data_pagamento' not in update_data:
                update_data['data_pagamento'] = firestore.SERVER_TIMESTAMP
        if 'data_pagamento' in data and data['data_pagamento']:
            update_data['data_pagamento'] = datetime.fromisoformat(data['data_pagamento'].replace('Z', '+00:00'))
        
        if update_data:
            multa_ref.update(update_data)
            return jsonify({"message": "Multa atualizada com sucesso."}), 200
        else:
            return jsonify({"message": "Nenhum campo para atualizar."}), 200
            
    except Exception as e:
        print(f"Erro ao atualizar multa: {e}")
        return jsonify({"error": "Erro ao atualizar multa."}), 500


@app.route('/api/multas/<multa_id>', methods=['DELETE'])
@requires_auth
def delete_multa(multa_id):
    """Deleta uma multa."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        multa_ref = db.collection('multas').document(multa_id)
        multa_doc = multa_ref.get()
        
        if not multa_doc.exists:
            return jsonify({"error": "Multa não encontrada."}), 404
        
        multa_data = multa_doc.to_dict()
        
        # Se tem documento no storage, deletar também
        if multa_data.get('documento_url'):
            try:
                # Extrair o caminho do arquivo da URL
                documento_url = multa_data['documento_url']
                if 'firebasestorage.googleapis.com' in documento_url:
                    import urllib.parse
                    path_start = documento_url.find('/o/') + 3
                    path_end = documento_url.find('?')
                    if path_start > 2 and path_end > path_start:
                        file_path = urllib.parse.unquote(documento_url[path_start:path_end])
                        bucket = firebase_storage.bucket()
                        blob = bucket.blob(file_path)
                        blob.delete()
                        print(f"[OK] Documento da multa {multa_id} deletado do storage: {file_path}")
            except Exception as e:
                print(f" Erro ao deletar documento do storage: {e}")
        
        multa_ref.delete()
        return jsonify({"message": "Multa deletada com sucesso."}), 200
        
    except Exception as e:
        print(f"Erro ao deletar multa: {e}")
        return jsonify({"error": "Erro ao deletar multa."}), 500


@app.route('/api/multas/<multa_id>/upload-documento', methods=['POST'])
@requires_auth
def upload_documento_multa(multa_id):
    """Upload documento da multa"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        # Verificar se multa existe
        multa_ref = db.collection('multas').document(multa_id)
        multa_doc = multa_ref.get()
        
        if not multa_doc.exists:
            return jsonify({"error": "Multa não encontrada."}), 404
        
        multa_data = multa_doc.to_dict()
        
        # Verificar se tem arquivo
        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo foi enviado."}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Nome de arquivo vazio."}), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"Tipo de arquivo não permitido. Use: {', '.join(allowed_extensions)}"}), 400
        
        # Se já existe documento, deletar o antigo do storage
        if multa_data.get('documento_url'):
            try:
                old_url = multa_data['documento_url']
                if 'firebasestorage.googleapis.com' in old_url:
                    import urllib.parse
                    path_start = old_url.find('/o/') + 3
                    path_end = old_url.find('?')
                    if path_start > 2 and path_end > path_start:
                        old_file_path = urllib.parse.unquote(old_url[path_start:path_end])
                        bucket = firebase_storage.bucket()
                        old_blob = bucket.blob(old_file_path)
                        old_blob.delete()
                        print(f"[OK] Documento antigo da multa deletado: {old_file_path}")
            except Exception as e:
                print(f" Erro ao deletar documento antigo: {e}")
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        placa = multa_data.get('placa', 'SEMPLACA')
        safe_filename = f"multa_{placa}_{timestamp}{file_ext}"
        
        # Upload para Firebase Storage
        bucket = firebase_storage.bucket()
        blob = bucket.blob(f'multas/{safe_filename}')
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Tornar o arquivo publicamente acessível
        blob.make_public()
        documento_url = blob.public_url
        
        # Atualizar Firestore com a URL do documento
        multa_ref.update({
            'documento_url': documento_url,
            'documento_updated_at': datetime.now(timezone.utc)
        })
        
        print(f"[OK] Documento da multa {multa_id} enviado: {safe_filename}")
        
        return jsonify({
            "message": "Documento enviado com sucesso!",
            "documento_url": documento_url
        }), 200
        
    except Exception as e:
        print(f" Erro ao fazer upload do documento da multa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erro ao fazer upload do documento."}), 500


@app.route('/api/multas/<multa_id>/documento', methods=['GET'])
def get_documento_multa(multa_id):
    """Retorna a URL do documento da multa"""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        multa_ref = db.collection('multas').document(multa_id)
        multa_doc = multa_ref.get()
        
        if not multa_doc.exists:
            return jsonify({"error": "Multa não encontrada."}), 404
        
        multa_data = multa_doc.to_dict()
        documento_url = multa_data.get('documento_url')
        
        if not documento_url:
            return jsonify({"error": "Multa não possui documento anexado."}), 404
        
        return jsonify({"documento_url": documento_url}), 200
        
    except Exception as e:
        print(f"Erro ao buscar documento da multa: {e}")
        return jsonify({"error": "Erro ao buscar documento."}), 500


# ============================================
# REVISÕES - Gestão de Manutenção Periódica
# ============================================

@app.route('/api/revisoes', methods=['GET', 'POST'])
def revisoes():
    """Lista todas as revisões ou cria uma nova"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    if request.method == 'GET':
        try:
            placa_filtro = request.args.get('placa', '').strip().upper()
            status_filtro = request.args.get('status', '').strip().lower()
            
            revisoes_ref = db.collection('revisoes')
            
            if placa_filtro:
                revisoes_ref = revisoes_ref.where('placa', '==', placa_filtro)
            
            revisoes_docs = revisoes_ref.order_by('data_revisao', direction=firestore.Query.DESCENDING).stream()
            
            revisoes_list = []
            for doc in revisoes_docs:
                revisao = doc.to_dict()
                revisao['id'] = doc.id
                
                # Calcular status dinamicamente baseado no KM atual do KM Mensal
                if 'km_proxima_revisao' in revisao and 'placa' in revisao:
                    # Buscar último registro de KM do veículo
                    km_docs = db.collection('km_mensal').where('placa', '==', revisao['placa']).order_by('mes_ano', direction=firestore.Query.DESCENDING).limit(1).stream()
                    km_atual = 0
                    
                    for km_doc in km_docs:
                        km_data = km_doc.to_dict()
                        km_atual = km_data.get('km_valor', 0) or 0
                        break
                    
                    km_proxima = revisao.get('km_proxima_revisao', 0)
                    
                    if km_atual > 0:
                        if km_atual >= km_proxima:
                            revisao['status'] = 'atrasada'
                        elif km_atual >= (km_proxima - 1000):  # 1000 km antes
                            revisao['status'] = 'proxima'
                        else:
                            revisao['status'] = 'em_dia'
                        
                        revisao['km_atual'] = km_atual
                        revisao['km_restante'] = km_proxima - km_atual
                    else:
                        revisao['status'] = 'em_dia'
                        revisao['km_atual'] = 0
                        revisao['km_restante'] = km_proxima
                
                # Aplicar filtro de status se especificado
                if status_filtro and revisao.get('status', '') != status_filtro:
                    continue
                
                revisoes_list.append(revisao)
            
            return jsonify(revisoes_list), 200
            
        except Exception as e:
            print(f"Erro ao buscar revisões: {e}")
            return jsonify({"error": "Erro ao buscar revisões."}), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            # Validações
            if not data.get('placa') or not data.get('tipo_revisao'):
                return jsonify({"error": "Placa e tipo de revisão são obrigatórios."}), 400
            
            placa = data['placa'].strip().upper()
            
            # Criar documento de revisão
            revisao = {
                'placa': placa,
                'tipo_revisao': data.get('tipo_revisao', '').strip(),
                'km_revisao': int(data.get('km_revisao', 0)),
                'data_revisao': data.get('data_revisao'),
                'km_proxima_revisao': int(data.get('km_proxima_revisao', 0)),
                'data_proxima_prevista': data.get('data_proxima_prevista'),
                'oficina': data.get('oficina', '').strip(),
                'valor': float(data.get('valor', 0)) if data.get('valor') else None,
                'observacao': data.get('observacao', '').strip(),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            db.collection('revisoes').add(revisao)
            
            print(f"[OK] Revisão cadastrada: {placa} - {revisao['tipo_revisao']}")
            return jsonify({"message": "Revisão cadastrada com sucesso!"}), 201
            
        except ValueError as ve:
            return jsonify({"error": f"Erro de validação: {str(ve)}"}), 400
        except Exception as e:
            print(f"Erro ao criar revisão: {e}")
            return jsonify({"error": "Erro ao criar revisão."}), 500


@app.route('/api/revisoes/<revisao_id>', methods=['GET', 'PUT', 'DELETE'])
def revisao_detail(revisao_id):
    """Obtém, atualiza ou deleta uma revisão específica"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    revisao_ref = db.collection('revisoes').document(revisao_id)
    
    if request.method == 'GET':
        try:
            revisao_doc = revisao_ref.get()
            if not revisao_doc.exists:
                return jsonify({"error": "Revisão não encontrada."}), 404
            
            revisao = revisao_doc.to_dict()
            revisao['id'] = revisao_doc.id
            
            return jsonify(revisao), 200
            
        except Exception as e:
            print(f"Erro ao buscar revisão: {e}")
            return jsonify({"error": "Erro ao buscar revisão."}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.json
            
            revisao_doc = revisao_ref.get()
            if not revisao_doc.exists:
                return jsonify({"error": "Revisão não encontrada."}), 404
            
            # Atualizar campos
            update_data = {
                'placa': data.get('placa', '').strip().upper(),
                'tipo_revisao': data.get('tipo_revisao', '').strip(),
                'km_revisao': int(data.get('km_revisao', 0)),
                'data_revisao': data.get('data_revisao'),
                'km_proxima_revisao': int(data.get('km_proxima_revisao', 0)),
                'data_proxima_prevista': data.get('data_proxima_prevista'),
                'oficina': data.get('oficina', '').strip(),
                'valor': float(data.get('valor', 0)) if data.get('valor') else None,
                'observacao': data.get('observacao', '').strip(),
                'updated_at': datetime.now(timezone.utc)
            }
            
            revisao_ref.update(update_data)
            
            print(f"[OK] Revisão {revisao_id} atualizada")
            return jsonify({"message": "Revisão atualizada com sucesso!"}), 200
            
        except ValueError as ve:
            return jsonify({"error": f"Erro de validação: {str(ve)}"}), 400
        except Exception as e:
            print(f"Erro ao atualizar revisão: {e}")
            return jsonify({"error": "Erro ao atualizar revisão."}), 500
    
    elif request.method == 'DELETE':
        try:
            revisao_doc = revisao_ref.get()
            if not revisao_doc.exists:
                return jsonify({"error": "Revisão não encontrada."}), 404
            
            revisao_ref.delete()
            
            print(f"[OK] Revisão {revisao_id} deletada")
            return jsonify({"message": "Revisão deletada com sucesso."}), 200
            
        except Exception as e:
            print(f"Erro ao deletar revisão: {e}")
            return jsonify({"error": "Erro ao deletar revisão."}), 500


# ============================================
# ROTAS DE GERAÇÃO DE PDF
# ============================================

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO

@app.route('/pdf/motoristas', methods=['GET'])
@requires_auth
def pdf_motoristas():
    """Gera PDF com lista de todos os motoristas"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    try:
        # Obter filtro de status (todos, ativos, inativos)
        filtro_status = request.args.get('status', 'todos')  # 'todos', 'ativos', 'inativos'
        
        # Buscar motoristas
        motoristas_ref = db.collection('motoristas').stream()
        motoristas = []
        for doc in motoristas_ref:
            m = doc.to_dict()
            m['id'] = doc.id
            
            # Aplicar filtro de status
            status_ativo = m.get('status_ativo', True)  # Default true se não existir
            if filtro_status == 'ativos' and not status_ativo:
                continue
            elif filtro_status == 'inativos' and status_ativo:
                continue
            
            motoristas.append(m)
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Título com filtro
        titulo_filtro = {
            'todos': 'RELATÓRIO DE MOTORISTAS - TODOS',
            'ativos': 'RELATÓRIO DE MOTORISTAS - APENAS ATIVOS',
            'inativos': 'RELATÓRIO DE MOTORISTAS - APENAS INATIVOS'
        }
        
        elements.append(Paragraph(titulo_filtro.get(filtro_status, 'RELATÓRIO DE MOTORISTAS'), title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"Total de motoristas: {len(motoristas)}", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela com coluna Status
        data = [['Nome', 'Empresa', 'Função', 'Status', 'Viagens']]
        for m in motoristas:
            status_ativo = m.get('status_ativo', True)
            status_texto = 'Ativo' if status_ativo else 'Inativo'
            
            data.append([
                m.get('nome', '-'),
                m.get('empresa', '-'),
                m.get('funcao', '-'),
                status_texto,
                str(m.get('viagens_totais', 0))
            ])
        
        table = Table(data, colWidths=[5*cm, 3.5*cm, 3.5*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename=motoristas_{filtro_status}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de motoristas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/pdf/veiculos', methods=['GET'])
@requires_auth
def pdf_veiculos():
    """Gera PDF com lista de veículos (com filtro de status)"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    try:
        # Filtro de status (ativos, inativos ou todos)
        status_filter = request.args.get('status', 'todos')  # 'todos', 'ativos', 'inativos'
        
        # Buscar veículos
        veiculos_ref = db.collection('veiculos').stream()
        veiculos = []
        for doc in veiculos_ref:
            v = doc.to_dict()
            v['id'] = doc.id
            
            # Aplicar filtro de status
            status_ativo = v.get('status_ativo', True)
            if status_filter == 'ativos' and not status_ativo:
                continue
            elif status_filter == 'inativos' and status_ativo:
                continue
            
            # Buscar total real de abastecimentos e litros
            placa = v.get('placa')
            if placa:
                refuels_query = db.collection('refuels').where(
                    filter=firestore.FieldFilter('veiculo', '==', placa)
                ).stream()
                
                total_count = 0
                total_litros = 0
                for refuel_doc in refuels_query:
                    total_count += 1
                    refuel_data = refuel_doc.to_dict()
                    litros = refuel_data.get('litros', 0)
                    if litros:
                        try:
                            total_litros += float(litros)
                        except:
                            pass
                
                v['total_refuels_real'] = total_count
                v['total_litros_real'] = total_litros
            else:
                v['total_refuels_real'] = 0
                v['total_litros_real'] = 0
                
            veiculos.append(v)
        
        # Ordenar: ativos primeiro, inativos no final
        veiculos.sort(key=lambda x: (not x.get('status_ativo', True), x.get('placa', '')))
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Título com filtro
        if status_filter == 'ativos':
            titulo = "RELATÓRIO DE VEÍCULOS - APENAS ATIVOS"
        elif status_filter == 'inativos':
            titulo = "RELATÓRIO DE VEÍCULOS - APENAS INATIVOS"
        else:
            titulo = "RELATÓRIO DE VEÍCULOS - TODOS"
        
        elements.append(Paragraph(titulo, title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela
        data = [['Placa', 'Modelo', 'Status', 'Km Atual', 'Média km/L', 'Total Abast.', 'Total Litros']]
        for v in veiculos:
            total_abast = v.get('total_refuels_real', 0)
            total_litros = v.get('total_litros_real', 0)
            status_ativo = v.get('status_ativo', True)
            status_texto = 'Ativo' if status_ativo else 'Inativo'
            
            data.append([
                v.get('placa', '-'),
                v.get('modelo', '-'),
                status_texto,
                str(v.get('ultimo_odometro', '-')),
                f"{v.get('media_kmpl', 0):.2f}" if v.get('media_kmpl') else '-',
                str(total_abast),
                f"{total_litros:.1f}L" if total_litros > 0 else '0L'
            ])
        
        table = Table(data, colWidths=[2.2*cm, 3.0*cm, 1.8*cm, 2.2*cm, 2.4*cm, 2.4*cm, 2.4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename=veiculos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de veículos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/pdf/abastecimentos', methods=['GET'])
@requires_auth
def pdf_abastecimentos():
    """Gera PDF com lista de abastecimentos (filtros opcionais via query params)"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    try:
        # Filtros opcionais
        veiculo = request.args.get('veiculo')
        motorista = request.args.get('motorista')
        tipo_combustivel = request.args.get('tipo_combustivel')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Query base
        query = db.collection('refuels')
        
        # Aplicar filtros
        filters = []
        if veiculo:
            filters.append(firestore.FieldFilter('veiculo', '==', veiculo))
        if motorista:
            filters.append(firestore.FieldFilter('motorista', '==', motorista))
        if tipo_combustivel:
            filters.append(firestore.FieldFilter('tipo_combustivel', '==', tipo_combustivel))
        
        if data_inicio:
            try:
                # Converte data local (Brasil) para UTC
                dt_inicio_local = datetime.fromisoformat(data_inicio)
                if dt_inicio_local.tzinfo is None:
                    dt_inicio_local = dt_inicio_local.replace(tzinfo=LOCAL_TZ)
                dt_inicio_utc = dt_inicio_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('timestamp', '>=', dt_inicio_utc))
                print(f'[DATE] Filtro data_inicio: {data_inicio} (local) -> {dt_inicio_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_inicio: {e}')
                pass
        
        if data_fim:
            try:
                # Converte data local (Brasil) para UTC
                dt_fim_local = datetime.fromisoformat(data_fim)
                if dt_fim_local.tzinfo is None:
                    dt_fim_local = dt_fim_local.replace(tzinfo=LOCAL_TZ)
                dt_fim_utc = dt_fim_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('timestamp', '<=', dt_fim_utc))
                print(f'[DATE] Filtro data_fim: {data_fim} (local) -> {dt_fim_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_fim: {e}')
                pass
        
        if filters:
            query = query.where(filter=And(filters))
        elif not data_inicio and not data_fim:
            #  SEGURANÇA: Se não tem filtro de data, busca apenas do mês atual
            now_local = datetime.now(LOCAL_TZ)
            primeiro_dia = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ultimo_dia = (primeiro_dia.replace(month=primeiro_dia.month % 12 + 1, day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            
            primeiro_dia_utc = primeiro_dia.astimezone(timezone.utc)
            ultimo_dia_utc = ultimo_dia.astimezone(timezone.utc)
            
            query = query.where(filter=And([
                firestore.FieldFilter('timestamp', '>=', primeiro_dia_utc),
                firestore.FieldFilter('timestamp', '<=', ultimo_dia_utc)
            ]))
            print(f' Sem filtros: buscando apenas mês atual ({primeiro_dia.strftime("%m/%Y")})')
        
        # Limitar a 500 registros
        refuels_docs = list(query.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(500).stream())
        
        refuels = []
        for doc in refuels_docs:
            r = doc.to_dict()
            r['id'] = doc.id
            refuels.append(r)
        
        # Criar PDF em paisagem para mais colunas
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Título
        titulo = "RELATÓRIO DE ABASTECIMENTOS"
        if veiculo:
            titulo += f" - Veículo: {veiculo}"
        elements.append(Paragraph(titulo, title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Se for de um veículo específico, simplifica (sem valor e km/L)
        if veiculo:
            data = [['Data', 'Motorista', 'Litros', 'Odômetro']]
            
            if len(refuels) == 0:
                data.append(['Nenhum abastecimento encontrado', '', '', ''])
            
            for r in refuels:
                ts = r.get('timestamp')
                data_str = '-'
                if ts:
                    if isinstance(ts, datetime):
                        data_str = ts.strftime('%d/%m/%Y')
                    else:
                        try:
                            data_str = datetime.fromisoformat(str(ts)).strftime('%d/%m/%Y')
                        except:
                            pass
                
                litros = r.get('litros')
                odometro = r.get('odometro')
                
                data.append([
                    data_str if data_str else '-',
                    r.get('motorista', '-') or '-',
                    f"{float(litros):.1f}L" if litros not in (None, '', 0) else '-',
                    str(odometro) if odometro not in (None, '', '-') else '-'
                ])
            
            table = Table(data, colWidths=[4*cm, 8*cm, 4*cm, 5*cm])
        else:
            # Relatório geral (todos veículos)
            data = [['Data', 'Veículo', 'Motorista', 'Litros', 'Valor', 'Odômetro', 'km/L']]
            
            if len(refuels) == 0:
                data.append(['Nenhum abastecimento encontrado', '', '', '', '', '', ''])
            
            for r in refuels:
                ts = r.get('timestamp')
                data_str = '-'
                if ts:
                    if isinstance(ts, datetime):
                        data_str = ts.strftime('%d/%m/%Y')
                    else:
                        try:
                            data_str = datetime.fromisoformat(str(ts)).strftime('%d/%m/%Y')
                        except:
                            pass
                
                litros = r.get('litros')
                valor = r.get('valor')
                odometro = r.get('odometro')
                kmpl = r.get('kmpl')
                
                data.append([
                    data_str if data_str else '-',
                    r.get('veiculo', '-') or '-',
                    r.get('motorista', '-') or '-',
                    f"{float(litros):.1f}L" if litros not in (None, '', 0) else '-',
                    f"R$ {float(valor):.2f}" if valor not in (None, '', 0) else '-',
                    str(odometro) if odometro not in (None, '', '-') else '-',
                    f"{float(kmpl):.2f}" if kmpl not in (None, '', '-') and isinstance(kmpl, (int, float)) else '-'
                ])
            
            table = Table(data, colWidths=[3*cm, 3*cm, 4*cm, 2.5*cm, 3*cm, 3*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f'abastecimentos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de abastecimentos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/pdf/saidas', methods=['GET'])
@requires_auth
def pdf_saidas():
    """Gera PDF com lista de saídas (filtros opcionais via query params)"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    try:
        # Filtros opcionais
        veiculo = request.args.get('veiculo')
        motorista = request.args.get('motorista')
        solicitante = request.args.get('solicitante')
        status = request.args.get('status')  # 'em_curso' ou 'finalizada'
        categoria = request.args.get('categoria')  # 'Base ETE de Araçatiba' ou 'Vans'
        status_aprovacao = request.args.get('status_aprovacao')
        status_direcionamento = request.args.get('status_direcionamento')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Query base
        query = db.collection('saidas')
        
        # Aplicar filtros
        filters = []
        if veiculo:
            filters.append(firestore.FieldFilter('veiculo', '==', veiculo))
        if motorista:
            filters.append(firestore.FieldFilter('motorista', '==', motorista))
        if solicitante:
            filters.append(firestore.FieldFilter('solicitante', '==', solicitante))
        if status:
            filters.append(firestore.FieldFilter('status', '==', status))
        if categoria:
            filters.append(firestore.FieldFilter('veiculo_categoria', '==', categoria))
        if status_aprovacao:
            filters.append(firestore.FieldFilter('status_aprovacao', '==', status_aprovacao))
        if status_direcionamento:
            filters.append(firestore.FieldFilter('status_direcionamento', '==', status_direcionamento))
        
        if data_inicio:
            try:
                # Converte data local (Brasil) para UTC para comparar com timestampSaida
                dt_inicio_local = datetime.fromisoformat(data_inicio)
                # Se não tem timezone, adiciona o timezone local
                if dt_inicio_local.tzinfo is None:
                    dt_inicio_local = dt_inicio_local.replace(tzinfo=LOCAL_TZ)
                dt_inicio_utc = dt_inicio_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('timestampSaida', '>=', dt_inicio_utc))
                print(f'[DATE] Filtro data_inicio: {data_inicio} (local) -> {dt_inicio_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_inicio: {e}')
                pass
        
        if data_fim:
            try:
                # Converte data local (Brasil) para UTC para comparar com timestampSaida
                dt_fim_local = datetime.fromisoformat(data_fim)
                # Se não tem timezone, adiciona o timezone local
                if dt_fim_local.tzinfo is None:
                    dt_fim_local = dt_fim_local.replace(tzinfo=LOCAL_TZ)
                dt_fim_utc = dt_fim_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('timestampSaida', '<=', dt_fim_utc))
                print(f'[DATE] Filtro data_fim: {data_fim} (local) -> {dt_fim_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_fim: {e}')
                pass
        
        if filters:
            query = query.where(filter=And(filters))
        elif not data_inicio and not data_fim:
            #  SEGURANÇA: Se não tem filtro de data, busca apenas do mês atual
            now_local = datetime.now(LOCAL_TZ)
            primeiro_dia = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ultimo_dia = (primeiro_dia.replace(month=primeiro_dia.month % 12 + 1, day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            
            primeiro_dia_utc = primeiro_dia.astimezone(timezone.utc)
            ultimo_dia_utc = ultimo_dia.astimezone(timezone.utc)
            
            query = query.where(filter=And([
                firestore.FieldFilter('timestampSaida', '>=', primeiro_dia_utc),
                firestore.FieldFilter('timestampSaida', '<=', ultimo_dia_utc)
            ]))
            print(f' Sem filtros: buscando apenas mês atual ({primeiro_dia.strftime("%m/%Y")})')
        
        # [OK] LIMITE MÁXIMO: 500 registros para proteger quota
        saidas_docs = list(query.order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(500).stream())
        
        print(f'[PDF] Gerando com {len(saidas_docs)} registros')
        
        saidas = []
        for doc in saidas_docs:
            s = doc.to_dict()
            s['id'] = doc.id
            saidas.append(s)
        
        # Criar PDF em paisagem
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Título
        titulo = "RELATÓRIO DE SAÍDAS"
        if veiculo:
            titulo += f" - Veículo: {veiculo}"
        if motorista:
            titulo += f" - Motorista: {motorista}"
        elements.append(Paragraph(titulo, title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela
        data = [['Data Saída', 'Veículo', 'Motorista', 'Destino', 'Status', 'Data Retorno']]
        for s in saidas:
            ts_saida = s.get('timestampSaida')
            data_saida = '-'
            if ts_saida:
                if isinstance(ts_saida, datetime):
                    data_saida = ts_saida.strftime('%d/%m/%Y %H:%M')
                else:
                    try:
                        data_saida = datetime.fromisoformat(str(ts_saida)).strftime('%d/%m/%Y %H:%M')
                    except:
                        pass
            
            ts_retorno = s.get('timestampRetorno') or s.get('timestampChegada')
            data_retorno = '-'
            if ts_retorno:
                if isinstance(ts_retorno, datetime):
                    data_retorno = ts_retorno.strftime('%d/%m/%Y %H:%M')
                else:
                    try:
                        data_retorno = datetime.fromisoformat(str(ts_retorno)).strftime('%d/%m/%Y %H:%M')
                    except:
                        pass
            
            status_text = '[OK] Finalizada' if s.get('status') == 'finalizada' else ' Em Curso'
            
            # Buscar trajeto/destino
            destino = s.get('trajeto') or s.get('destino') or '-'
            if destino != '-' and len(destino) > 30:
                destino = destino[:30] + '...'
            
            data.append([
                data_saida,
                s.get('veiculo', '-') or '-',
                s.get('motorista', '-') or '-',
                destino,
                status_text,
                data_retorno
            ])
        
        table = Table(data, colWidths=[4*cm, 3*cm, 4*cm, 5*cm, 3*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f'saidas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de saídas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/pdf/multas', methods=['GET'])
@requires_auth
def pdf_multas():
    """Gera PDF com lista de multas (filtros opcionais via query params)"""
    if not db:
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    try:
        # Filtros opcionais
        veiculo = request.args.get('veiculo')
        status = request.args.get('status')  # 'pendente', 'paga', 'contestada'
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Query base
        query = db.collection('multas')
        
        # Aplicar filtros
        filters = []
        if veiculo:
            filters.append(firestore.FieldFilter('placa', '==', veiculo))
        if status:
            filters.append(firestore.FieldFilter('status', '==', status))
        
        if data_inicio:
            try:
                # Converte data local (Brasil) para UTC
                dt_inicio_local = datetime.fromisoformat(data_inicio)
                if dt_inicio_local.tzinfo is None:
                    dt_inicio_local = dt_inicio_local.replace(tzinfo=LOCAL_TZ)
                dt_inicio_utc = dt_inicio_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('data_vencimento', '>=', dt_inicio_utc))
                print(f'[DATE] Filtro data_inicio: {data_inicio} (local) -> {dt_inicio_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_inicio: {e}')
                pass
        
        if data_fim:
            try:
                # Converte data local (Brasil) para UTC
                dt_fim_local = datetime.fromisoformat(data_fim)
                if dt_fim_local.tzinfo is None:
                    dt_fim_local = dt_fim_local.replace(tzinfo=LOCAL_TZ)
                dt_fim_utc = dt_fim_local.astimezone(timezone.utc)
                filters.append(firestore.FieldFilter('data_vencimento', '<=', dt_fim_utc))
                print(f'[DATE] Filtro data_fim: {data_fim} (local) -> {dt_fim_utc} (UTC)')
            except Exception as e:
                print(f' Erro ao converter data_fim: {e}')
                pass
        
        if filters:
            query = query.where(filter=And(filters))
        elif not data_inicio and not data_fim:
            #  SEGURANÇA: Se não tem filtro de data, busca apenas do mês atual
            now_local = datetime.now(LOCAL_TZ)
            primeiro_dia = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ultimo_dia = (primeiro_dia.replace(month=primeiro_dia.month % 12 + 1, day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            
            primeiro_dia_utc = primeiro_dia.astimezone(timezone.utc)
            ultimo_dia_utc = ultimo_dia.astimezone(timezone.utc)
            
            query = query.where(filter=And([
                firestore.FieldFilter('data_vencimento', '>=', primeiro_dia_utc),
                firestore.FieldFilter('data_vencimento', '<=', ultimo_dia_utc)
            ]))
            print(f' Sem filtros: buscando apenas mês atual ({primeiro_dia.strftime("%m/%Y")})')
        
        # Limitar a 500 registros
        multas_docs = list(query.order_by('data_vencimento', direction=firestore.Query.DESCENDING).limit(500).stream())
        
        multas = []
        for doc in multas_docs:
            m = doc.to_dict()
            m['id'] = doc.id
            multas.append(m)
        
        # Criar PDF em paisagem
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Título
        titulo = "RELATÓRIO DE MULTAS"
        if veiculo:
            titulo += f" - Veículo: {veiculo}"
        if status:
            status_texto = {'pendente': 'Pendentes', 'paga': 'Pagas', 'contestada': 'Contestadas'}.get(status, status)
            titulo += f" - Status: {status_texto}"
        
        elements.append(Paragraph(titulo, title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabela
        data = [['Status', 'Veículo', 'Descrição', 'Valor', 'Vencimento', 'Motorista', 'Local']]
        
        if len(multas) == 0:
            data.append(['Nenhuma multa encontrada', '', '', '', '', '', ''])
        
        total_valor = 0
        for m in multas:
            data_vencimento = m.get('data_vencimento')
            data_venc_str = '-'
            if data_vencimento:
                if isinstance(data_vencimento, datetime):
                    data_venc_str = data_vencimento.strftime('%d/%m/%Y')
                else:
                    try:
                        data_venc_str = datetime.fromisoformat(str(data_vencimento)).strftime('%d/%m/%Y')
                    except:
                        pass
            
            # Status text
            status_map = {
                'pendente': '⏳ Pendente',
                'paga': '[OK] Paga',
                'contestada': ' Contestada'
            }
            status_text = status_map.get(m.get('status', 'pendente'), '⏳ Pendente')
            
            # Verifica se está vencida
            if m.get('status') == 'pendente' and data_vencimento:
                try:
                    dt_venc = datetime.fromisoformat(str(data_vencimento)) if isinstance(data_vencimento, str) else data_vencimento
                    if dt_venc < datetime.now(timezone.utc):
                        status_text = '⏰ VENCIDA'
                except:
                    pass
            
            valor = m.get('valor', 0) or 0
            total_valor += valor
            
            descricao = m.get('descricao', '-') or '-'
            if len(descricao) > 30:
                descricao = descricao[:30] + '...'
            
            local = m.get('local', '-') or '-'
            if len(local) > 20:
                local = local[:20] + '...'
            
            data.append([
                status_text,
                m.get('placa', '-') or '-',
                descricao,
                f"R$ {valor:.2f}",
                data_venc_str,
                m.get('motorista', '-') or '-',
                local
            ])
        
        # Adicionar linha de total
        if len(multas) > 0:
            data.append(['', '', 'TOTAL:', f"R$ {total_valor:.2f}", '', '', ''])
        
        table = Table(data, colWidths=[3.5*cm, 3*cm, 5*cm, 3*cm, 3*cm, 4*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E5E7EB')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f'multas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de multas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/pdf/revisoes', methods=['GET', 'POST'])
@requires_auth
def pdf_revisoes():
    """Gera PDF com lista de chamados de manutenção (filtros opcionais via query params ou POST)"""
    print("\n" + "="*60)
    print("[PDF] INICIANDO GERACAO DE PDF DE REVISOES")
    print("="*60)
    
    if not db:
        print("[ERRO] Banco de dados não conectado")
        return jsonify({"error": "Banco de dados não conectado"}), 500
    
    def sanitize_text(text):
        """Remove apenas caracteres problemáticos, mantém texto legível"""
        if not text:
            return '-'
        try:
            text = str(text)
            # Remove apenas emojis e caracteres de controle, mantém acentos
            import unicodedata
            # Normaliza e remove categorias problemáticas (emojis, símbolos)
            cleaned = ''.join(
                char for char in text 
                if unicodedata.category(char)[0] not in ('C', 'S') or char in ' \n\t'
            )
            return cleaned.strip() if cleaned.strip() else str(text).encode('ascii', 'ignore').decode('ascii')
        except:
            return str(text)[:50]  # Retorna primeiros 50 chars se falhar
    
    try:
        # Inicializa variáveis de filtro
        placa = ''
        status_chamado = None
        categoria = None
        aprovacao = None
        direcionamento = None
        
        # Se for POST, pega dados do body (vindo do frontend/LocalStorage)
        if request.method == 'POST':
            data = request.get_json()
            chamados = data.get('chamados', [])
            print(f"[PDF] Recebidos {len(chamados)} chamados do LocalStorage")
        else:
            # Se for GET, busca do Firestore (modo antigo)
            # Filtros opcionais (novos filtros do sistema de chamados)
            placa = request.args.get('placa', '').strip()
            status_chamado = request.args.get('status')  # 'pendente', 'andamento', 'resolvido'
            categoria = request.args.get('categoria')  # 'pneu', 'revisao', 'mecanica', 'lataria'
            aprovacao = request.args.get('aprovacao')  # 'aprovado', 'falta_aprovacao'
            direcionamento = request.args.get('direcionamento')  # 'direcionado', 'nao_direcionado', 'sem_direcionamento'
            
            # Query base na coleção de chamados
            query = db.collection('revisoes')
            
            # Aplicar filtros do Firestore quando possível
            if placa:
                query = query.where('plate', '==', placa.upper())
            
            if status_chamado:
                query = query.where('status', '==', status_chamado)
            
            if categoria:
                query = query.where('category', '==', categoria)
            
            # Buscar chamados
            try:
                chamados_docs = list(query.limit(100).stream())
            except Exception as e:
                print(f"[PDF] Erro ao buscar chamados: {e}")
                query = db.collection('revisoes')
                chamados_docs = list(query.limit(100).stream())
            
            print(f"[PDF] {len(chamados_docs)} chamados encontrados no Firestore")
            
            chamados = []
            for doc in chamados_docs:
                c = doc.to_dict()
                c['id'] = doc.id
                
                # Aplicar filtros de aprovação e direcionamento (não suportados no Firestore diretamente)
                if aprovacao:
                    c_aprovacao = c.get('aprovacao', '')
                    if aprovacao == 'aprovado' and c_aprovacao != 'aprovado':
                        continue
                    elif aprovacao == 'falta_aprovacao' and c_aprovacao != 'falta_aprovacao':
                        continue
                
                if direcionamento:
                    c_direcionamento = c.get('direcionamento', '')
                    if direcionamento == 'direcionado' and c_direcionamento != 'direcionado':
                        continue
                    elif direcionamento == 'nao_direcionado' and c_direcionamento != 'nao_direcionado':
                        continue
                    elif direcionamento == 'sem_direcionamento' and c_direcionamento != 'sem_direcionamento':
                        continue
                
                chamados.append(c)
        
        # Criar PDF em paisagem
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#7c3aed'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Título (SEM ACENTOS)
        titulo = "RELATORIO DE CHAMADOS DE MANUTENCAO"
        filtros_aplicados = []
        if placa:
            filtros_aplicados.append(f"Veiculo: {placa}")
        if status_chamado:
            status_map = {'pendente': 'Pendente', 'andamento': 'Em Andamento', 'resolvido': 'Resolvido'}
            filtros_aplicados.append(f"Status: {status_map.get(status_chamado, status_chamado)}")
        if categoria:
            cat_map = {'pneu': 'Pneus', 'revisao': 'Revisao', 'mecanica': 'Mecanica', 'lataria': 'Lataria'}
            filtros_aplicados.append(f"Categoria: {cat_map.get(categoria, categoria)}")
        if aprovacao:
            apr_map = {'aprovado': 'Aprovados', 'falta_aprovacao': 'Falta Aprovacao'}
            filtros_aplicados.append(f"Aprovacao: {apr_map.get(aprovacao, aprovacao)}")
        if direcionamento:
            dir_map = {'direcionado': 'Direcionado', 'nao_direcionado': 'Nao Direcionado', 'sem_direcionamento': 'Sem Direcionamento'}
            filtros_aplicados.append(f"Direcionamento: {dir_map.get(direcionamento, direcionamento)}")
        
        if filtros_aplicados:
            titulo += f" ({', '.join(filtros_aplicados)})"
        
        elements.append(Paragraph(titulo, title_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.4*cm))
        
        # Tabela (SEM ACENTOS)
        data = [['Status', 'Placa', 'Motorista', 'Categoria', 'Titulo', 'KM', 'Aprovacao', 'Direcionamento', 'Data']]
        
        if len(chamados) == 0:
            data.append(['', '', '', '', '', '', '', '', ''])
            data.append(['', '', 'NENHUM CHAMADO ENCONTRADO NO FIRESTORE', '', '', '', '', '', ''])
            data.append(['', '', '', '', '', '', '', '', ''])
            data.append(['', 'Os chamados estao salvos apenas no LocalStorage do navegador.', '', '', '', '', '', '', ''])
            data.append(['', 'Para gerar PDF, e necessario cadastrar chamados via sistema.', '', '', '', '', '', '', ''])
        
        for c in chamados:
            # Status (SEM EMOJIS) - LocalStorage usa 'mainStatus' em português
            status_map = {
                'pendente': 'Pendente',
                'andamento': 'Em Andamento',
                'resolvido': 'Resolvido'
            }
            status_text = status_map.get(c.get('mainStatus', 'pendente'), 'Pendente')
            
            # Categoria (SEM EMOJIS)
            cat_map = {
                'pneu': 'Pneu',
                'revisao': 'Revisao',
                'mecanica': 'Mecanica',
                'lataria': 'Lataria'
            }
            cat_text = cat_map.get(c.get('category', ''), '-')
            
            # Aprovação - LocalStorage tem campo direto
            approval_status = c.get('aprovacao', '')
            apr_map = {
                'aprovado': 'Aprovado',
                'falta_aprovacao': 'Pendente'
            }
            apr_text = apr_map.get(approval_status, '-')
            
            # Direcionamento - LocalStorage tem campo direto
            assignment_status = c.get('direcionamento', '')
            dir_map = {
                'direcionado': 'Sim',
                'nao_direcionado': 'Aguardando',
                'sem_direcionamento': 'Sem'
            }
            dir_text = dir_map.get(assignment_status, '-')
            
            # Data - LocalStorage tem campo 'date' como string
            data_str = c.get('date', '-')
            # Se for "Não informada" ou vazio, mostra "-"
            if not data_str or data_str.lower() in ['não informada', 'nao informada', '']:
                data_str = '-'
            
            data.append([
                status_text,
                sanitize_text(c.get('plate', '-')),
                sanitize_text(c.get('driver', '-')),
                cat_text,
                sanitize_text(c.get('title', '-'))[:30],  # Limita título a 30 chars
                sanitize_text(c.get('km', '-')),
                apr_text,
                dir_text,
                data_str
            ])
        
        table = Table(data, colWidths=[2.5*cm, 2.5*cm, 3.5*cm, 2.5*cm, 5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f'chamados_manutencao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF de revisões: {e}")
        import traceback
        traceback.print_exc()
        # Retorna erro sem caracteres especiais
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        return jsonify({"error": error_msg if error_msg else "Erro ao gerar PDF"}), 500


@app.route('/pdf/km-mensal', methods=['GET'])
@requires_auth
def gerar_pdf_km_mensal():
    """Gera PDF com dados de km mensal por veículo"""
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from datetime import datetime
        
        # Obter filtros da query string
        mes_filtro = request.args.get('mes')  # Formato: YYYY-MM
        ano_filtro = request.args.get('ano')  # Formato: YYYY
        
        print(f"[STATS] [PDF KM] Gerando PDF com filtros: mes={mes_filtro}, ano={ano_filtro}")
        
        # Buscar dados de km mensal da coleção km_mensal
        km_ref = db.collection('km_mensal')
        
        # Aplicar filtros
        if mes_filtro:
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '==', mes_filtro))
        elif ano_filtro:
            # Filtrar por ano (YYYY-01 até YYYY-12)
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '>=', f'{ano_filtro}-01'))
            km_ref = km_ref.where(filter=firestore.FieldFilter('mes_ano', '<=', f'{ano_filtro}-12'))
        
        docs = km_ref.stream()
        
        # Processar dados
        registros = []
        for doc in docs:
            data = doc.to_dict()
            registros.append({
                'placa': data.get('placa', 'N/A'),
                'mes_ano': data.get('mes_ano', 'N/A'),
                'km_valor': data.get('km_valor', 0) or 0,
                'observacao': data.get('observacao', '')
            })
        
        print(f" [PDF KM] Encontrados {len(registros)} registros")
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título com filtro
        titulo_filtro = "Relatório de Km Mensal por Veículo"
        if mes_filtro:
            mes_nome = datetime.strptime(mes_filtro, '%Y-%m').strftime('%B/%Y')
            titulo_filtro += f" - {mes_nome}"
        elif ano_filtro:
            titulo_filtro += f" - Ano {ano_filtro}"
        
        title = Paragraph(f"<b>{titulo_filtro}</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))
        
        # Subtítulo com data
        subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal'])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.8*cm))
        
        # Criar tabela (simplificada)
        header = ['Placa', 'Mês/Ano', 'KM (Odômetro)', 'Observação']
        data = [header]
        
        if registros:
            # Ordenar por mes_ano e placa
            registros.sort(key=lambda x: (x['mes_ano'], x['placa']))
            
            for reg in registros:
                mes_formatado = datetime.strptime(reg['mes_ano'], '%Y-%m').strftime('%b/%Y') if reg['mes_ano'] != 'N/A' else 'N/A'
                
                row = [
                    reg['placa'],
                    mes_formatado,
                    f"{reg['km_valor']:,} km".replace(',', '.'),
                    reg['observacao'][:40] if reg['observacao'] else '-'
                ]
                data.append(row)
        else:
            data.append(['Nenhum registro encontrado', '', '', ''])
        
        # Criar tabela com larguras de coluna ajustadas
        col_widths = [3.5*cm, 3*cm, 4*cm, 8*cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E5E7EB')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Nome do arquivo com filtro
        filename_base = 'km_mensal_veiculos'
        if mes_filtro:
            filename_base += f'_{mes_filtro}'
        elif ano_filtro:
            filename_base += f'_{ano_filtro}'
        filename = f'{filename_base}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        print(f"[OK] [PDF KM] PDF gerado: {filename}")
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        
    except Exception as e:
        print(f" [PDF KM] Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


from waitress import serve

# [OK] Endpoint de health check para UptimeRobot/Render
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - mantém servidor acordado no Render"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Frota Sanemar"
    }), 200

# Handler de erro global
@app.errorhandler(Exception)
def handle_exception(e):
    """Captura todas as exceções não tratadas para evitar crashes"""
    import traceback
    error_trace = traceback.format_exc()
    print(f"\n[ERRO] Exceção capturada:")
    print(error_trace)
    
    # Sanitiza erro para ASCII
    try:
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        if not error_msg:
            error_msg = "Erro interno do servidor"
    except:
        error_msg = "Erro interno do servidor"
    
    return jsonify({"error": error_msg}), 500

if __name__ == '__main__':
    print("RODOUUUUUUUUUUU")
    # threads=8: Permite processar 8 requisições simultâneas
    # channel_timeout=60: Timeout de 60s para requisições longas
    serve(app, host='0.0.0.0', port=5000, threads=8, channel_timeout=60)
