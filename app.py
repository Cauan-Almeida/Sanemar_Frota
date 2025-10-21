import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template, redirect, url_for
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import And
from dotenv import load_dotenv
from collections import Counter

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

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o Flask App
app = Flask(__name__)

# Inicializa o cliente Firestore
try:
    db = firestore.Client()
    print("Conexão com o Firestore estabelecida com sucesso.")
except Exception as e:
    print(f"Erro ao conectar com o Firestore: {e}")
    db = None

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
    motoristas = []
    if db:
        try:
            veiculos_ref = db.collection('veiculos').stream()
            veiculos = [doc.to_dict().get('placa') for doc in veiculos_ref if doc.to_dict().get('placa')]
            veiculos.sort()

            motoristas_ref = db.collection('motoristas').stream()
            motoristas = [doc.to_dict().get('nome') for doc in motoristas_ref if doc.to_dict().get('nome')]
            motoristas.sort()

        except Exception as e:
            mark_firestore_unavailable_if_quota(e)
            print(f"Erro ao buscar veículos ou motoristas: {e}")
            return render_template('maintenance.html'), 503

    return render_template('index.html', veiculos=veiculos, motoristas=motoristas)


# --- Rota para o Dashboard de Análise ---
@app.route('/dashboard')
def dashboard():
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('dashboard.html')

@app.route('/motorista/<nome>')
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
        return jsonify({"message": "Viagem cancelada."}), 200
    except Exception as e:
        print(f"Erro ao cancelar viagem: {e}")
        return jsonify({"error": "Ocorreu um erro ao cancelar a viagem."}), 500

@app.route('/veiculo/<placa>')
def veiculo_detalhes(placa):
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    if not db:
        return "Erro: Conexão com o banco de dados não estabelecida.", 500

    try:
        # Busca os detalhes do veículo
        veiculos_ref = db.collection('veiculos')
        veiculo_query = veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', placa)).limit(1).stream()
        veiculo = next(veiculo_query, None)
        if not veiculo:
            return "Veículo não encontrado.", 404
        
        veiculo_data = serialize_doc(veiculo.to_dict())

        # Busca o histórico de viagens do veículo
        saidas_ref = db.collection('saidas')
        viagens_query = saidas_ref.where(filter=firestore.FieldFilter('veiculo', '==', placa)).order_by('timestampSaida', direction=firestore.Query.DESCENDING).stream()
        
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

        return render_template('veiculo_detalhes.html', veiculo=veiculo_data, viagens=viagens, stats=stats)

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

    # Normaliza entradas: placa em maiúsculas; nomes e textos capitalizados
    def title_case(s):
        return ' '.join([w.capitalize() for w in s.split()]) if s else s

    veiculo = normalize_plate(veiculo) if veiculo else veiculo
    motorista = title_case(motorista)
    solicitante = title_case(solicitante)
    trajeto = title_case(trajeto)

    if not all([veiculo, motorista, solicitante, trajeto]):
        return jsonify({"error": "Todos os campos de saída são obrigatórios."}), 400

    response_message = handle_saida(veiculo, motorista, solicitante, trajeto, horario)

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

    if "sucesso" in response_message:
        return jsonify({"message": response_message}), 200
    else:
        if "Nenhum registro" in response_message:
            return jsonify({"error": response_message}), 404  # 404 Not Found
        return jsonify({"error": response_message}), 500

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
            veiculos.append({
                "veiculo": data.get("veiculo"),
                "motorista": data.get("motorista"),
                "horarioSaida": data.get("horarioSaida")
            })
        
        return jsonify(veiculos), 200

    except Exception as e:
        print(f"Erro ao buscar veículos em curso: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar os veículos em curso."}), 500

@app.route('/api/historico', methods=['GET'])
def get_historico():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        data_filtro = request.args.get('data')
        placa_filtro = request.args.get('placa')
        motorista_filtro = request.args.get('motorista')

        query = db.collection('saidas').order_by('timestampSaida', direction=firestore.Query.DESCENDING)
        
        historico_docs = query.stream()

        historico = [serialize_doc(doc.to_dict()) for doc in historico_docs]

        if data_filtro:
            try:
                data_obj = datetime.strptime(data_filtro, '%d/%m/%Y')
                historico = [h for h in historico if h['timestampSaida'].startswith(data_obj.strftime('%Y-%m-%d'))]
            except ValueError:
                # Ignore invalid date format
                pass
        
        if placa_filtro:
            historico = [h for h in historico if placa_filtro.lower() in h.get('veiculo', '').lower()]

        if motorista_filtro:
            historico = [h for h in historico if motorista_filtro.lower() in h.get('motorista', '').lower()]

        # Ordena o resultado: 'em_curso' primeiro, mantendo a ordem de data para o resto
        historico_final = sorted(historico, key=lambda x: x.get('status') == 'em_curso', reverse=True)

        return jsonify(historico_final), 200

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
def post_motorista():
    """Cria um motorista com campos opcionais: funcao, empresa."""
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    funcao = (data.get('funcao') or '').strip()
    empresa = (data.get('empresa') or '').strip()

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
            'status': 'nao_credenciado',
            'dataCadastro': firestore.SERVER_TIMESTAMP
        })

        return jsonify({"message": "Motorista cadastrado com sucesso."}), 201
    except Exception as e:
        print(f"Erro ao cadastrar motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao cadastrar o motorista."}), 500


@app.route('/api/motoristas/<motorista_id>', methods=['PUT'])
def update_motorista(motorista_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    data = request.get_json() or {}
    funcao = (data.get('funcao') or '').strip()
    empresa = (data.get('empresa') or '').strip()

    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()

        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404

        update_data = {}
        if funcao:
            update_data['funcao'] = funcao
        if empresa:
            update_data['empresa'] = empresa

        if not update_data:
            return jsonify({"error": "Nenhum campo para atualizar."}), 400

        motorista_ref.update(update_data)
        return jsonify({"message": "Motorista atualizado com sucesso."}), 200

    except Exception as e:
        print(f"Erro ao atualizar motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao atualizar o motorista."}), 500


@app.route('/api/motoristas/<motorista_id>', methods=['DELETE'])
def delete_motorista(motorista_id):
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        motorista_ref = db.collection('motoristas').document(motorista_id)
        motorista_doc = motorista_ref.get()

        if not motorista_doc.exists:
            return jsonify({"error": "Motorista não encontrado."}), 404

        motorista_ref.delete()
        return jsonify({"message": "Motorista excluído com sucesso."}), 200

    except Exception as e:
        print(f"Erro ao excluir motorista: {e}")
        return jsonify({"error": "Ocorreu um erro ao excluir o motorista."}), 500


@app.route('/motoristas')
def motoristas_page():
    if not FIRESTORE_AVAILABLE:
        return render_template('maintenance.html'), 503
    return render_template('motoristas.html')


@app.route('/motorista')
def motorista_root_redirect():
    # Legacy or mistyped path: redirect to the motoristas list page
    return redirect(url_for('motoristas_page'))


@app.route('/motorista.html')
def motorista_html_redirect():
    # Some users might try to open the template path directly; redirect to the route
    return redirect(url_for('motoristas_page'))


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

        # Atualiza veículo com último odômetro se fornecido
        if odometro is not None:
            veiculos_ref = db.collection('veiculos')
            # procura doc do veículo
            q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo)).limit(1).stream())
            if q:
                vdoc = q[0]
                vdoc.reference.update({'ultimo_odometro': int(odometro)})

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
        # firestore cursor-based pagination is preferred, but for simplicity we will fetch and slice
        query = refuels_ref.where(filter=firestore.FieldFilter('veiculo', '==', placa_norm)).order_by('timestamp', direction=firestore.Query.DESCENDING)
        docs = list(query.stream())
        total = len(docs)
        start = (page - 1) * page_size
        end = start + page_size
        page_docs = docs[start:end]
        items = []
        for d in page_docs:
            item = d.to_dict()
            item['_id'] = d.id
            items.append(serialize_doc(item))
        return jsonify({ 'items': items, 'total': total, 'page': page, 'page_size': page_size }), 200
    except Exception as e:
        print(f"Erro ao buscar refuels: {e}")
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
        if not ref.get().exists:
            return jsonify({"error": "Abastecimento não encontrado."}), 404
        ref.delete()
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

        return {
            'km_por_litro_medio': (media_val if media_flag else (round(kmpl_medio, 2) if kmpl_medio is not None else None)),
            'km_por_litro_medio_computed': round(kmpl_medio, 2) if kmpl_medio is not None else None,
            'km_por_litro_ponderado': round(kmpl_ponderado, 2) if kmpl_ponderado is not None else None,
            'km_no_mes': km_no_mes,
            'ultimo_odometro': ultimo_odometro,
            'media_informada': media_flag,
            'media_informada_valor': media_val
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
        docs = list(refuels_ref.stream())
        totals = {}
        totals_month = {}
        for d in docs:
            r = d.to_dict()
            placa = r.get('veiculo')
            litros = r.get('litros')
            ts = r.get('timestamp')
            if not placa or litros is None:
                continue
            try:
                litros_val = float(litros)
            except Exception:
                continue
            totals[placa] = totals.get(placa, 0) + litros_val
            if month_start and month_end and ts:
                # ts can be datetime or string
                try:
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
        # Permitimos atualizar media_kmpl, ultimo_odometro e outros campos livres
        if 'media_kmpl' in data:
            try:
                update_fields['media_kmpl'] = float(data.get('media_kmpl')) if data.get('media_kmpl') not in (None, '') else None
            except Exception:
                return jsonify({"error": "Valor inválido para media_kmpl."}), 400
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

@app.route('/api/veiculos', methods=['GET'])
def get_veiculos():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500
    
    try:
        veiculos_ref = db.collection('veiculos').stream()
        veiculos = [serialize_doc(doc.to_dict()) for doc in veiculos_ref]
        return jsonify(veiculos), 200

    except Exception as e:
        print(f"Erro ao buscar veículos: {e}")
        return jsonify({"error": "Ocorreu um erro ao buscar os veículos."}), 500

@app.route('/api/dashboard_stats', methods=['GET'])
def get_dashboard_stats():
    if not db:
        return jsonify({"error": "Conexão com o banco de dados não foi estabelecida."}), 500

    try:
        # Essas leituras agora são a fonte dos seus totais
        saidas_docs = [] # NÃO VAMOS MAIS LER TUDO DE SAIDAS AQUI
        motoristas_docs = list(db.collection('motoristas').stream())
        veiculos_docs = list(db.collection('veiculos').stream())

        now = datetime.now(timezone.utc)
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = now - timedelta(days=30)

        # Se o frontend enviar ?month=YYYY-MM, usaremos esse intervalo apenas para os charts mensais
        month_param = request.args.get('month')  # formato esperado: YYYY-MM
        month_start = None
        month_end = None
        if month_param:
            try:
                year, month = month_param.split('-')
                year = int(year)
                month = int(month)
                # início do mês no fuso local (00:00 do primeiro dia)
                month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                # fim do mês: primeiro dia do próximo mês menos 1 segundo
                if month == 12:
                    next_month_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                else:
                    next_month_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=LOCAL_TZ)
                month_end_local = next_month_local - timedelta(seconds=1)
                # converter para UTC para comparar com timestamps armazenados em UTC
                month_start = month_start_local.astimezone(timezone.utc)
                month_end = month_end_local.astimezone(timezone.utc)
            except Exception:
                month_start = None
                month_end = None
        
        # Você ainda precisa ler as saídas DO MÊS.
        # Vamos fazer uma consulta eficiente SÓ PARA O MÊS.
        
        window_start = month_start if month_start else thirty_days_ago
        window_end = month_end if month_end else now

        # Consulta eficiente para os dados do mês/período
        query_mes = db.collection('saidas').where(filter=And([
            firestore.FieldFilter('timestampSaida', '>=', window_start),
            firestore.FieldFilter('timestampSaida', '<=', window_end)
        ]))
        saidas_mes_docs = list(query_mes.stream())
        saidas_mes = [doc.to_dict() for doc in saidas_mes_docs]
        
        viagens_em_curso = 0
        viagens_hoje = 0
        total_horas_em_rua_seconds = 0

        # Processa apenas as saídas do mês para estatísticas mensais
        for saida in saidas_mes:
            timestamp_saida = saida.get('timestampSaida')
            if not timestamp_saida or not isinstance(timestamp_saida, datetime):
                continue

            if saida.get('status') == 'em_curso':
                viagens_em_curso += 1
            
            if timestamp_saida >= start_of_today:
                viagens_hoje += 1

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

        # ... (lógica do histórico recente, use o .limit(50) que sugeri antes) ...
        query_hist = db.collection('saidas').order_by('timestampSaida', direction=firestore.Query.DESCENDING).limit(50)
        historico_recente_docs = query_hist.stream()
        historico_recente = [serialize_doc(doc.to_dict()) for doc in historico_recente_docs]
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

        return jsonify(stats)

    except Exception as e:
        print(f"Erro em get_dashboard_stats: {e}")
        return jsonify({"error": "Ocorreu um erro ao calcular as estatísticas."}), 500


# --- Lógica de Negócio ---

def handle_saida(veiculo_placa, motorista_nome, solicitante, trajeto, horario=None):
    try:
        # Normaliza placa recebida
        veiculo_placa = normalize_plate(veiculo_placa) if veiculo_placa else veiculo_placa
        # REGRA DE NEGÓCIO: Verifica se o veículo já está em curso
        saidas_ref = db.collection('saidas')
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
            # Veículo é novo. Cria o documento já com o total 1.
            veiculos_ref.add({
                'placa': veiculo_placa,
                'dataCadastro': firestore.SERVER_TIMESTAMP,
                'viagens_totais': 1 # Inicia a contagem em 1
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
        timestamp_saida = now_utc

        if horario:  # Se um horário foi fornecido
            try:
                horario_obj = datetime.strptime(horario, "%H:%M").time()
                # Cria o datetime no fuso horário local
                local_dt = now_local.replace(hour=horario_obj.hour, minute=horario_obj.minute, second=0, microsecond=0)
                # Converte para UTC para armazenamento
                timestamp_saida = local_dt.astimezone(timezone.utc)
                horario_saida_str = horario_obj.strftime("%H:%M")
            except ValueError:
                # Se o formato do horário for inválido, usa a hora atual como fallback
                timestamp_saida = now_utc
                horario_saida_str = now_local.strftime("%H:%M")
        else:  # Se nenhum horário foi fornecido
            timestamp_saida = now_utc
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
                # Atualiza o ultimo odometro no veiculo
                if odometro_val is not None:
                    veiculos_ref = db.collection('veiculos')
                    q = list(veiculos_ref.where(filter=firestore.FieldFilter('placa', '==', veiculo_placa)).limit(1).stream())
                    if q:
                        vdoc = q[0]
                        vdoc.reference.update({'ultimo_odometro': int(odometro_val)})
                return_msg += ' Abastecimento registrado (litros/odômetro).'
        except Exception as e:
            print(f"Erro ao registrar refuel na chegada: {e}")
            # não falha a chegada por causa do refuel

        return return_msg

    except Exception as e:
        print(f"Erro no handle_chegada: {e}")
        return "Ocorreu um erro interno ao registrar a chegada."

from waitress import serve

if __name__ == '__main__':
    print("RODOUUUUUUUUUUU")
    serve(app, host='0.0.0.0', port=5000)