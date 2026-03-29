from flask import Flask, render_template, jsonify, request
import requests
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonplayerinfo
from nba_api.live.nba.endpoints import scoreboard, boxscore
import time
import google.generativeai as genai
import os
import json
import unicodedata
from dotenv import load_dotenv
from upstash_redis import Redis

# Carrega as chaves do arquivo invisível .env (apenas no seu PC)
load_dotenv()

app = Flask(__name__)

# PUXANDO AS CHAVES DE FORMA SEGURA
CHAVE_ODDS_API = os.getenv('CHAVE_ODDS_API')
CHAVE_GEMINI_IA = os.getenv('CHAVE_GEMINI_IA')

# Chaves do Upstash (Vercel KV)
URL_BANCO = os.getenv('KV_REST_API_URL')
TOKEN_BANCO = os.getenv('KV_REST_API_TOKEN')

# Inicializa o Banco de Dados Oficial
redis_db = None
if URL_BANCO and TOKEN_BANCO:
    try:
        redis_db = Redis(url=URL_BANCO, token=TOKEN_BANCO)
    except Exception as e:
        print(f"Erro ao conectar no Upstash: {e}")

# Ligando a IA do Google
if CHAVE_GEMINI_IA:
    genai.configure(api_key=CHAVE_GEMINI_IA)
    model = genai.GenerativeModel('gemini-2.5-flash') 
else:
    model = None

MAPA_MERCADOS = {
    'player_points': {'coluna': 'PTS', 'nome': 'Pontos'},
    'player_rebounds': {'coluna': 'REB', 'nome': 'Rebotes'},
    'player_assists': {'coluna': 'AST', 'nome': 'Assistências'},
    'player_threes': {'coluna': 'FG3M', 'nome': 'Cestas de 3'},
    'player_blocks': {'coluna': 'BLK', 'nome': 'Tocos'},
    'player_steals': {'coluna': 'STL', 'nome': 'Roubos'}
}

# --- MOTOR DE BUSCA FLEXÍVEL (ANTI-ARRILIA) ---
def limpar_nome(nome):
    """Remove acentos, pontos e deixa tudo minúsculo"""
    return unicodedata.normalize('NFD', str(nome)).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def encontrar_jogador_flexivel(nome_digitado, lista_jogadores, chave_nome=None):
    busca = limpar_nome(nome_digitado)
    busca_termos = busca.replace('.', ' ').split() # "n. jokic" vira ["n", "jokic"]
    
    possiveis = []
    for p in lista_jogadores:
        # Se for dicionario (NBA API), usa a chave. Se for string (Live Tracker), usa direto.
        nome_db = limpar_nome(p[chave_nome]) if chave_nome else limpar_nome(p)
        
        # 1. Match Exato (já sem acento)
        if busca == nome_db:
            return p
            
        # 2. Match Parcial Inteligente (Todos os pedaços digitados estão no nome real)
        if all(termo in nome_db for termo in busca_termos):
            possiveis.append(p)
            
    if possiveis:
        # Se achou vários e for dados da NBA, prioriza quem ainda joga (is_active)
        if chave_nome and 'is_active' in possiveis[0]:
            ativos = [p for p in possiveis if p.get('is_active')]
            if ativos: return ativos[0]
        return possiveis[0] # Retorna o primeiro que achar
        
    return None
# ----------------------------------------------

def gerar_relatorio_ia(nome_jogador, nome_mercado, linha, sugestao, media, historico, adversario, confianca_base):
    if not model:
        return 1.0, f"Matemática indica: {sugestao} {linha} {nome_mercado}."
        
    prompt = (
        f"Aja como um analista de NBA. O nosso sistema matemático JÁ DECIDIU que a melhor aposta é OBRIGATORIAMENTE: '{sugestao}' {linha} {nome_mercado} para {nome_jogador} contra o {adversario}.\n"
        f"Média recente (10 jogos): {media:.1f}. Histórico: {historico}.\n\n"
        f"Sua tarefa:\n"
        f"1. Avalie a defesa do {adversario} e defina um PESO de 0.8 (difícil) a 1.2 (fácil).\n"
        f"2. Escreva 3 linhas EXPLICANDO o porquê essa aposta '{sugestao}' é excelente. NUNCA sugira o contrário.\n\n"
        f"Responda EXATAMENTE:\n"
        f"PESO: [numero]\n"
        f"TEXTO: [sua analise]"
    )
    
    try:
        response = model.generate_content(prompt)
        resposta_texto = response.text.strip().replace('**', '')
        
        peso_defesa = 1.0
        texto_final = f"Análise: Recomendação forte de {sugestao} {linha} {nome_mercado}."
        
        for linha_resp in resposta_texto.split('\n'):
            if linha_resp.upper().startswith('PESO:'):
                try: peso_defesa = float(linha_resp.split(':')[1].strip())
                except: pass
            elif linha_resp.upper().startswith('TEXTO:'):
                texto_final = linha_resp.split('TEXTO:')[1].strip()
                
        return peso_defesa, texto_final

    except Exception as e:
        print(f"❌ Erro na IA: {e}")
        return 1.0, f"Matemática indica: {sugestao} {linha} {nome_mercado}."

def buscar_analises():
    print("\n📡 INICIANDO O RADAR ANTI-RED (10 JOGOS)...")
    if not CHAVE_ODDS_API:
        return []
        
    url_jogos = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
    resposta_jogos = requests.get(url_jogos, params={'apiKey': CHAVE_ODDS_API})
    jogos = resposta_jogos.json()
    if not isinstance(jogos, list): return []

    nba_players = players.get_players()
    analises_finais = []
    mercados_string = ",".join(MAPA_MERCADOS.keys())

    for jogo in jogos:
        id_jogo = jogo['id']
        partida_nome = f"{jogo['home_team']} vs {jogo['away_team']}"
        url_odds = f'https://api.the-odds-api.com/v4/sports/basketball_nba/events/{id_jogo}/odds'
        parametros = {'apiKey': CHAVE_ODDS_API, 'regions': 'us,eu,uk', 'markets': mercados_string}
        resposta_odds = requests.get(url_odds, params=parametros).json()
        
        if len(resposta_odds.get('bookmakers', [])) == 0: continue
        try: lista_mercados_abertos = resposta_odds['bookmakers'][0]['markets']
        except: continue
        
        jogadores_processados = []
        for mercado_info in lista_mercados_abertos:
            chave_mercado = mercado_info['key']
            if chave_mercado not in MAPA_MERCADOS: continue
            coluna_nba = MAPA_MERCADOS[chave_mercado]['coluna']
            nome_bonito = MAPA_MERCADOS[chave_mercado]['nome']
            
            for aposta in mercado_info['outcomes']:
                nome_jogador = aposta['description']
                linha_casa = aposta['point']
                tipo_aposta = aposta['name'] 
                id_processamento = f"{nome_jogador}_{chave_mercado}"
                
                if id_processamento in jogadores_processados or tipo_aposta != 'Over': continue
                jogadores_processados.append(id_processamento)
                
                jogador_info = encontrar_jogador_flexivel(nome_jogador, nba_players, 'full_name')
                if not jogador_info: continue
                
                try:
                    historico = playergamelog.PlayerGameLog(player_id=jogador_info['id'])
                    df_jogos = historico.get_data_frames()[0].head(10) 
                    tamanho_amostra = len(df_jogos)
                    if tamanho_amostra < 6: continue 
                    
                    valores = df_jogos[coluna_nba].tolist()
                    media = sum(valores) / tamanho_amostra
                    
                    overs = sum(1 for v in valores if v > linha_casa)
                    unders = sum(1 for v in valores if v < linha_casa)
                    
                    recomendacao = 'MAIS DE' if media > linha_casa else 'MENOS DE'
                    if recomendacao == 'MAIS DE':
                        taxa_acerto = (overs / tamanho_amostra) * 100
                        confianca = taxa_acerto + ((media - linha_casa) * 2)
                    else:
                        taxa_acerto = (unders / tamanho_amostra) * 100
                        confianca = taxa_acerto + ((linha_casa - media) * 2)
                        
                    confianca = min(max(confianca, 0.0), 99.0)
                    
                    if confianca > 80.0 and taxa_acerto >= 70.0:
                        analises_finais.append({
                            'jogador': jogador_info['full_name'], # Usa o nome limpo da API
                            'partida': partida_nome,
                            'mercado': nome_bonito,
                            'linha': linha_casa,
                            'sugestao': recomendacao,
                            'confianca': confianca,
                            'media': media,
                            'historico': valores,
                            'explicacao': f"Filtro Rigoroso: Bateu a linha em {taxa_acerto:.0f}% dos últimos {tamanho_amostra} jogos."
                        })
                    time.sleep(0.5) 
                except: continue
    
    return sorted(analises_finais, key=lambda x: x['confianca'], reverse=True)[:10]

@app.route('/')
def pagina_vendas():
    return render_template('landing.html')

@app.route('/app')
def aplicativo_robo():
    return render_template('index.html')

@app.route('/api/dados')
def api_dados():
    return jsonify(buscar_analises())

@app.route('/api/sniper', methods=['POST'])
def api_sniper():
    dados = request.json
    nome_jogador = dados.get('jogador')
    linha = float(dados.get('linha'))
    chave_mercado = dados.get('mercado')
    
    coluna_nba = MAPA_MERCADOS[chave_mercado]['coluna']
    nome_bonito = MAPA_MERCADOS[chave_mercado]['nome']
    
    nba_players = players.get_players()
    
    # Busca inteligente conectada aqui!
    jogador_info = encontrar_jogador_flexivel(nome_jogador, nba_players, 'full_name')
    if not jogador_info: 
        return jsonify({'erro': f'Jogador "{nome_jogador}" não encontrado. Tente outro nome.'})
        
    try:
        info_nba = commonplayerinfo.CommonPlayerInfo(player_id=jogador_info['id']).get_data_frames()[0]
        time_do_jogador = str(info_nba['TEAM_NAME'].iloc[0]) 
        adversario = "o time adversário" 
        
        if CHAVE_ODDS_API:
            url_jogos = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
            jogos_de_hoje = requests.get(url_jogos, params={'apiKey': CHAVE_ODDS_API}).json()
            if isinstance(jogos_de_hoje, list):
                for jogo in jogos_de_hoje:
                    if time_do_jogador.lower() in jogo['home_team'].lower():
                        adversario = jogo['away_team']
                        break
                    elif time_do_jogador.lower() in jogo['away_team'].lower():
                        adversario = jogo['home_team']
                        break

        historico = playergamelog.PlayerGameLog(player_id=jogador_info['id'])
        df_jogos = historico.get_data_frames()[0].head(10)
        tamanho_amostra = len(df_jogos)
        if tamanho_amostra < 5: return jsonify({'erro': 'Poucos jogos recentes.'})
        
        valores = df_jogos[coluna_nba].tolist()
        media = sum(valores) / tamanho_amostra
        
        overs = sum(1 for v in valores if v > linha)
        unders = sum(1 for v in valores if v < linha)
        
        recomendacao = 'MAIS DE' if media > linha else 'MENOS DE'
        if recomendacao == 'MAIS DE': 
            taxa_acerto = (overs / tamanho_amostra) * 100
            confianca_base = taxa_acerto + ((media - linha) * 2)
        else: 
            taxa_acerto = (unders / tamanho_amostra) * 100
            confianca_base = taxa_acerto + ((linha - media) * 2)
            
        confianca_base = min(max(confianca_base, 0.0), 99.0)
        
        peso_adversario, texto_unico_ia = gerar_relatorio_ia(
            jogador_info['full_name'], nome_bonito, linha, 
            recomendacao, media, valores, adversario, confianca_base
        )
        
        confianca_final = confianca_base * peso_adversario
        confianca_final = min(max(confianca_final, 0.0), 99.0)
        
        return jsonify({
            'jogador': jogador_info['full_name'], # Retorna o nome certinho com acento!
            'mercado': nome_bonito,
            'linha': linha,
            'sugestao': recomendacao,
            'confianca': confianca_final,
            'media': media,
            'historico': valores,
            'explicacao': texto_unico_ia,
            'adversario_encontrado': adversario
        })
    except Exception as e:
        print(f"Erro no Sniper: {e}")
        return jsonify({'erro': f'🕵️ Erro: {str(e)}'})

@app.route('/api/live', methods=['POST'])
def api_live():
    from datetime import datetime, timezone
    dados = request.json
    apostas = dados.get('apostas', [])
    if not apostas: return jsonify({})

    resultados = {}
    try:
        board = scoreboard.ScoreBoard()
        jogos = board.games.get_dict()
        jogadores_ativos = {}
        
        agora = datetime.now(timezone.utc)

        for jogo in jogos:
            status = jogo['gameStatus']
            texto_status = jogo['gameStatusText']
            
            # --- FILTRO MÃO DE FERRO (ANTI-FOGUETE RETROATIVO) ---
            try:
                horario_jogo = datetime.strptime(jogo['gameTimeUTC'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                horas_passadas = (agora - horario_jogo).total_seconds() / 3600
                
                # Se o jogo começou há mais de 15 horas, ele é lixo histórico. 
                # Ignoramos 100%, mesmo que o jogador esteja lá.
                if horas_passadas > 15:
                    continue
            except:
                pass
            # ----------------------------------------------------
            
            if status in [2, 3]:
                try:
                    bx = boxscore.BoxScore(jogo['gameId'])
                    dados_jogo = bx.game.get_dict()
                    todos_jogadores = dados_jogo['homeTeam']['players'] + dados_jogo['awayTeam']['players']
                    
                    for p in todos_jogadores:
                        nome_exato = p['name']
                        jogadores_ativos[nome_exato] = {
                            'status_jogo': texto_status,
                            'stats': p['statistics'],
                            'em_quadra': str(p.get('oncourt', '0')) == '1'
                        }
                except:
                    continue

        mapa_stats = {
            'Pontos': 'points', 'Rebotes': 'reboundsTotal', 'Assistências': 'assists',
            'Cestas de 3': 'threePointersMade', 'Tocos': 'blocks', 'Roubos': 'steals'
        }
        
        nomes_ativos = list(jogadores_ativos.keys())

        for aposta in apostas:
            id_ap = str(aposta['id'])
            nome_digitado = aposta['jogador']
            mercado_ap = aposta['mercado']
            
            nome_correto = encontrar_jogador_flexivel(nome_digitado, nomes_ativos)
            
            if nome_correto:
                dados_jog = jogadores_ativos[nome_correto]
                chave_stat = mapa_stats.get(mercado_ap, 'points')
                valor_atual = dados_jog['stats'].get(chave_stat, 0)
                
                resultados[id_ap] = {
                    'iniciado': True,
                    'status': dados_jog['status_jogo'],
                    'valor_atual': valor_atual,
                    'em_quadra': dados_jog['em_quadra']
                }
            else:
                resultados[id_ap] = {
                    'iniciado': False,
                    'status': "Aguardando início",
                    'valor_atual': 0
                }
                
        return jsonify(resultados)
    except Exception as e:
        print(f"Erro no Live Tracker: {e}")
        return jsonify({'erro': 'Falha ao buscar dados ao vivo'})

@app.route('/api/banco', methods=['GET'])
def ler_banco():
    if not redis_db:
        return jsonify({'tracker': [], 'historico': []})
    
    try:
        dados = redis_db.get("dados_juninho")
        if dados:
            if isinstance(dados, str):
                return jsonify(json.loads(dados))
            return jsonify(dados)
    except Exception as e:
        print(f"Erro ao ler nuvem: {e}")
        
    return jsonify({'tracker': [], 'historico': []})

@app.route('/api/banco', methods=['POST'])
def salvar_banco():
    if not redis_db:
        return jsonify({'erro': 'Banco não configurado'})
        
    dados = request.json
    try:
        redis_db.set("dados_juninho", json.dumps(dados))
        return jsonify({'status': 'sucesso'})
    except Exception as e:
        print(f"Erro ao salvar na nuvem: {e}")
        return jsonify({'erro': 'Falha na gravação'})

if __name__ == '__main__':
    app.run(debug=True, port=5001)