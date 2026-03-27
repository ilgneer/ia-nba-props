import requests
import time
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog

CHAVE_ODDS_API = '4da83f576c91a6efcc9b5bac95f6c3ab'

# Dicionário mágico: Traduz o mercado das casas de aposta para as colunas oficiais da NBA
# Dicionário mágico CORRIGIDO
MAPA_MERCADOS = {
    'player_points': {'coluna': 'PTS', 'nome': 'Pontos'},
    'player_rebounds': {'coluna': 'REB', 'nome': 'Rebotes'},
    'player_assists': {'coluna': 'AST', 'nome': 'Assistências'},
    'player_threes': {'coluna': 'FG3M', 'nome': 'Cestas de 3'}, # <- O erro estava aqui!
    'player_blocks': {'coluna': 'BLK', 'nome': 'Tocos'},
    'player_steals': {'coluna': 'STL', 'nome': 'Roubos'}
}

print("🤖 INICIANDO O ROBÔ MULTI-MERCADOS...\n")

print("📡 Buscando o calendário de jogos...")
url_jogos = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
jogos = requests.get(url_jogos, params={'apiKey': '4da83f576c91a6efcc9b5bac95f6c3ab'

}).json()

if not isinstance(jogos, list) or len(jogos) == 0:
    print("❌ Nenhum jogo encontrado para hoje ou erro na API.")
    exit()

print(f"✅ {len(jogos)} jogos encontrados. Varrendo Pontos, Rebotes, Assistências, Tocos e Roubos...\n")

nba_players = players.get_players()
analises_finais = []
mercados_string = ",".join(MAPA_MERCADOS.keys()) # Junta todos os mercados num texto só para a API

for jogo in jogos:
    id_jogo = jogo['id']
    partida_nome = f"{jogo['home_team']} vs {jogo['away_team']}"
    
    url_odds = f'https://api.the-odds-api.com/v4/sports/basketball_nba/events/{id_jogo}/odds'
    parametros = {
        'apiKey': '4da83f576c91a6efcc9b5bac95f6c3ab'

,
        'regions': 'us,eu,uk',
        'markets': mercados_string # Agora o robô pede TODOS os mercados de uma vez
    }
    
    resposta_odds = requests.get(url_odds, params=parametros).json()
    
    # Se a API nos devolver uma mensagem de erro, ele vai gritar na tela:
    if 'message' in resposta_odds:
        print(f"\n❌ A API BLOQUEOU! Motivo: {resposta_odds['message']}")
        break # Para o robô na hora
        
    if not isinstance(resposta_odds, dict) or len(resposta_odds.get('bookmakers', [])) == 0:
        continue
        
    print(f"🎯 Analisando: {partida_nome}...")
    
    try:
        # Pega a lista de todos os mercados abertos na primeira casa de aposta que achar
        lista_mercados_abertos = resposta_odds['bookmakers'][0]['markets']
    except (IndexError, KeyError):
        continue
    
    jogadores_processados = []
    
    # O robô agora varre cada mercado (Pontos, depois Rebotes, etc.)
    for mercado_info in lista_mercados_abertos:
        chave_mercado = mercado_info['key']
        
        if chave_mercado not in MAPA_MERCADOS:
            continue
            
        coluna_nba = MAPA_MERCADOS[chave_mercado]['coluna']
        nome_bonito = MAPA_MERCADOS[chave_mercado]['nome']
        
        for aposta in mercado_info['outcomes']:
            if 'description' not in aposta or 'point' not in aposta:
                continue
                
            nome_jogador = aposta['description']
            linha_casa = aposta['point']
            tipo_aposta = aposta['name'] 
            
            # Identificador único para não calcular o mesmo cara no mesmo mercado duas vezes
            id_processamento = f"{nome_jogador}_{chave_mercado}"
            
            if id_processamento in jogadores_processados or tipo_aposta != 'Over':
                continue
                
            jogadores_processados.append(id_processamento)
            
            jogador_info = next((p for p in nba_players if p['full_name'] == nome_jogador), None)
            if not jogador_info:
                continue
                
            try:
                historico = playergamelog.PlayerGameLog(player_id=jogador_info['id'])
                df_jogos = historico.get_data_frames()[0].head(5)
                
                if len(df_jogos) < 5:
                    continue
                    
                # Extrai os números corretos dependendo do mercado atual (PTS, REB, AST, etc)
                valores = df_jogos[coluna_nba].tolist()
                
                media = sum(valores) / len(valores)
                vezes_bateu = sum(1 for v in valores if v > linha_casa)
                taxa_acerto = (vezes_bateu / 5) * 100
                
                recomendacao = 'MAIS DE' if media > linha_casa else 'MENOS DE'
                
                if recomendacao == 'MAIS DE':
                    confianca = taxa_acerto + ((media - linha_casa) * 2)
                else:
                    confianca = (100 - taxa_acerto) + ((linha_casa - media) * 2)
                    
                confianca = min(confianca, 99.0)
                
                analises_finais.append({
                    'jogador': nome_jogador,
                    'partida': partida_nome,
                    'mercado': nome_bonito,
                    'linha': linha_casa,
                    'sugestao': recomendacao,
                    'confianca': confianca,
                    'media': media,
                    'historico': valores
                })
                
                time.sleep(0.6) 
                
            except Exception as e:
                continue

if len(analises_finais) == 0:
    print("\n⚠️ O mercado ainda está se formando nas casas. Tente rodar mais tarde.")
else:
    analises_finais = sorted(analises_finais, key=lambda x: x['confianca'], reverse=True)
    
    print("\n🏆 AS 10 MELHORES SELEÇÕES DO DIA PARA O 'MAIS OU MENOS' 🏆")
    print("=" * 65)
    
    for i, a in enumerate(analises_finais[:10], 1): 
        print(f"{i}º | {a['jogador'].upper()} ({a['partida']})")
        print(f"   ↳ Aposta: {a['sugestao']} {a['linha']} {a['mercado']}")
        print(f"   ↳ Confiança da IA: {a['confianca']:.1f}% | Média real recente: {a['media']:.1f}")
        print(f"   ↳ Últimos 5 jogos (Sequência): {a['historico']}")
        print("-" * 65)