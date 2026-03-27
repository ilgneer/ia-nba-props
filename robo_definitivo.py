import sqlite3
import requests
import time
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog

print("🤖 INICIANDO O ROBÔ DE ANÁLISE AUTOMÁTICA...\n")

# ==========================================
# 1. BUSCAR AS LINHAS DE HOJE NA OPTICODDS
# ==========================================
print("📡 Buscando linhas de aposta de hoje na OpticOdds...")
CHAVE_OPTICODDS = 'COLOQUE_SUA_CHAVE_AQUI'

# Endpoint fictício/padrão baseado na documentação deles para Player Props
url_odds = 'https://api.opticodds.com/api/v3/fixtures/player-props' 
headers = {'X-Api-Key': CHAVE_OPTICODDS}

# --- SIMULADOR DE RESPOSTA ---
# Como você ainda vai colocar a chave, criei este bloco para o código não quebrar e você ver a mágica.
# Quando for usar a API real, você vai usar: resposta = requests.get(url_odds, headers=headers).json()
dados_opticodds = [
    {'jogador': 'LeBron James', 'mercado': 'pts', 'linha': 24.5},
    {'jogador': 'Stephen Curry', 'mercado': 'fg3m', 'linha': 4.5},
    {'jogador': 'Nikola Jokic', 'mercado': 'reb', 'linha': 11.5},
    {'jogador': 'Luka Doncic', 'mercado': 'pts', 'linha': 32.5}
]
# -----------------------------

print(f"✅ Foram encontradas apostas para {len(dados_opticodds)} jogadores hoje.\n")

# ==========================================
# 2. CRUZAR COM OS DADOS REAIS DA NBA
# ==========================================
nba_players = players.get_players()
analises_finais = []

print("📊 Calculando probabilidades com base nos últimos 5 jogos...")

for aposta in dados_opticodds:
    nome_jogador = aposta['jogador']
    mercado = aposta['mercado']
    linha_casa = aposta['linha']
    
    # Busca o ID do jogador na NBA
    jogador_info = next((p for p in nba_players if p['full_name'] == nome_jogador), None)
    if not jogador_info:
        continue
        
    nba_id = jogador_info['id']
    
    try:
        # Puxa o histórico de jogos
        historico = playergamelog.PlayerGameLog(player_id=nba_id)
        df_jogos = historico.get_data_frames()[0].head(5) # Pega os 5 mais recentes
        
        if len(df_jogos) < 5:
            continue # Pula se não tiver histórico suficiente
            
        # Extrai os números dependendo do mercado que a OpticOdds mandou
        if mercado == 'pts':
            valores = df_jogos['PTS'].tolist()
        elif mercado == 'reb':
            valores = df_jogos['REB'].tolist()
        elif mercado == 'ast':
            valores = df_jogos['AST'].tolist()
        elif mercado == 'fg3m':
            valores = df_jogos['FG3M'].tolist()
        else:
            continue

        # A MATEMÁTICA
        media = sum(valores) / len(valores)
        vezes_bateu = sum(1 for v in valores if v > linha_casa)
        taxa_acerto = (vezes_bateu / 5) * 100
        
        # Fórmula de Confiança
        recomendacao = 'MAIS DE' if media > linha_casa else 'MENOS DE'
        if recomendacao == 'MAIS DE':
            confianca = taxa_acerto + ((media - linha_casa) * 2)
        else:
            confianca = (100 - taxa_acerto) + ((linha_casa - media) * 2)
            
        confianca = min(confianca, 99.0)
        
        # Salva a análise na lista
        analises_finais.append({
            'jogador': nome_jogador,
            'mercado': mercado.upper(),
            'linha': linha_casa,
            'sugestao': recomendacao,
            'confianca': confianca,
            'media': media,
            'historico': valores
        })
        
        time.sleep(1) # Pausa para a NBA não bloquear
        
    except Exception as e:
        print(f"❌ Erro ao analisar {nome_jogador}: {e}")

# ==========================================
# 3. O VEREDITO (RANKING TOP SELEÇÕES)
# ==========================================
# Ordena da maior confiança para a menor
analises_finais = sorted(analises_finais, key=lambda x: x['confianca'], reverse=True)

print("\n🏆 AS MELHORES SELEÇÕES PARA HOJE 🏆")
print("=" * 65)

# Mostra as opções ranqueadas
for i, a in enumerate(analises_finais[:10], 1): # Top 10 pra você ter margem de escolha
    print(f"{i}º | {a['jogador'].upper()}")
    print(f"   ↳ Aposta: {a['sugestao']} {a['linha']} {a['mercado']}")
    print(f"   ↳ Confiança: {a['confianca']:.1f}% | Média real: {a['media']:.1f}")
    print(f"   ↳ Sequência (últimos 5): {a['historico']}")
    print("-" * 65)