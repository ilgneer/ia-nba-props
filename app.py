from flask import Flask, render_template, jsonify, request
import requests
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonplayerinfo
import time
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- SEGURANÇA MÁXIMA ---
# Carrega as chaves do arquivo invisível .env para não expor no GitHub
load_dotenv()

app = Flask(__name__)

# PUXANDO AS CHAVES DE FORMA SEGURA DO .env
CHAVE_ODDS_API = os.getenv('CHAVE_ODDS_API')
CHAVE_GEMINI_IA = os.getenv('CHAVE_GEMINI_IA')

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

# --- FUNÇÃO MÁGICA: GERA O TEXTO E O PESO MATEMÁTICO DA DEFESA ---
def gerar_relatorio_ia(nome_jogador, nome_mercado, linha, sugestao, media, historico, adversario, confianca_base):
    if not model:
        return 1.0, f"Matemática indica: {sugestao} {linha} {nome_mercado}."
        
    # A COLEIRA DA IA: Forçando ela a concordar com a matemática
    prompt = (
        f"Aja como um analista de NBA. O nosso sistema matemático JÁ DECIDIU que a melhor aposta é OBRIGATORIAMENTE: '{sugestao}' {linha} {nome_mercado} para {nome_jogador} contra o {adversario}.\n"
        f"Média recente (10 jogos): {media:.1f}. Histórico: {historico}.\n\n"
        f"Sua tarefa:\n"
        f"1. Avalie a defesa do {adversario} e defina um PESO de 0.8 (difícil) a 1.2 (fácil).\n"
        f"2. Escreva 3 linhas EXPLICANDO o porquê essa aposta '{sugestao}' é excelente. NUNCA sugira o contrário do que o sistema mandou.\n\n"
        f"Responda EXATAMENTE:\n"
        f"PESO: [numero]\n"
        f"TEXTO: [sua analise]"
    )
    
    try:
        response = model.generate_content(prompt)
        resposta_texto = response.text.strip().replace('**', '')
        
        peso_defesa = 1.0
        texto_final = f"Análise: Recomendação forte de {sugestao} {linha} {nome_mercado}."
        
        linhas_resposta = resposta_texto.split('\n')
        for linha_resp in linhas_resposta:
            if linha_resp.upper().startswith('PESO:'):
                try: peso_defesa = float(linha_resp.split(':')[1].strip())
                except: pass
            elif linha_resp.upper().startswith('TEXTO:'):
                texto_final = linha_resp.split('TEXTO:')[1].strip()
                
        return peso_defesa, texto_final

    except Exception as e:
        print(f"❌ Erro na IA: {e}")
        return 1.0, f"Matemática indica: {sugestao} {linha} {nome_mercado}."

# --- FUNÇÃO DO RADAR AUTOMÁTICO ---
def buscar_analises():
    print("\n📡 INICIANDO O RADAR ANTI-RED (10 JOGOS)...")
    if not CHAVE_ODDS_API:
        print("⚠️ ERRO: Chave da Odds API não encontrada no .env!")
        return []
        
    url_jogos = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
    resposta_jogos = requests.get(url_jogos, params={'apiKey': CHAVE_ODDS_API})
    
    creditos = resposta_jogos.headers.get('x-requests-remaining', 'Desconhecido')
    print(f"💳 CRÉDITOS THE ODDS API RESTANTES: {creditos}")
    
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
                jogador_info = next((p for p in nba_players if p['full_name'] == nome_jogador), None)
                if not jogador_info: continue
                try:
                    # OLHAMOS OS ÚLTIMOS 10 JOGOS
                    historico = playergamelog.PlayerGameLog(player_id=jogador_info['id'])
                    df_jogos = historico.get_data_frames()[0].head(10) 
                    tamanho_amostra = len(df_jogos)
                    if tamanho_amostra < 6: continue 
                    
                    valores = df_jogos[coluna_nba].tolist()
                    media = sum(valores) / tamanho_amostra
                    
                    # CÁLCULO REAL DE HIT RATE (TAXA DE ACERTO)
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
                    
                    # FILTRO PROFISSIONAL: Só aprova se a Taxa de Acerto for >= 70% E Confiança alta
                    if confianca > 80.0 and taxa_acerto >= 70.0:
                        analises_finais.append({
                            'jogador': nome_jogador,
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

# --- ROTAS DO SITE ---
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
    jogador_info = next((p for p in nba_players if p['full_name'].lower() == nome_jogador.lower().strip()), None)
    if not jogador_info: return jsonify({'erro': f'Jogador "{nome_jogador}" não encontrado na base da NBA.'})
        
    try:
        # --- BUSCA AUTOMÁTICA DO ADVERSÁRIO ---
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
        # --------------------------------------

        # SNIPER COM HISTÓRICO DE 10 JOGOS
        historico = playergamelog.PlayerGameLog(player_id=jogador_info['id'])
        df_jogos = historico.get_data_frames()[0].head(10)
        tamanho_amostra = len(df_jogos)
        if tamanho_amostra < 5: return jsonify({'erro': 'Poucos jogos recentes na temporada.'})
        
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
        
        # Chama a IA para pegar o Peso da Defesa e o Texto
        peso_adversario, texto_unico_ia = gerar_relatorio_ia(
            jogador_info['full_name'], nome_bonito, linha, 
            recomendacao, media, valores, adversario, confianca_base
        )
        
        # Ajusta a nota com base no adversário
        confianca_final = confianca_base * peso_adversario
        confianca_final = min(max(confianca_final, 0.0), 99.0)
        
        return jsonify({
            'jogador': jogador_info['full_name'],
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
        return jsonify({'erro': 'Erro nos servidores da NBA ou The Odds API.'})

if __name__ == '__main__':
    app.run(debug=True)