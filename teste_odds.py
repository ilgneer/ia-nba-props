import requests
import json

minha_chave = 'COLOQUE_SUA_CHAVE_AQUI'

print("📡 Passo 1: Buscando o calendário de jogos da NBA de hoje...")

# 1. Buscar a lista de jogos (events)
url_jogos = 'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
resposta_jogos = requests.get(url_jogos, params={'apiKey': '4da83f576c91a6efcc9b5bac95f6c3ab'

})

if resposta_jogos.status_code == 200:
    jogos = resposta_jogos.json()
    
    if len(jogos) > 0:
        # Pega o primeiro jogo da lista para testar
        jogo_teste = jogos[0]
        id_do_jogo = jogo_teste['id']
        print(f"✅ Jogo encontrado! Partida: {jogo_teste['home_team']} vs {jogo_teste['away_team']}")

        print("\n📡 Passo 2: Buscando as linhas de Pontos (Bet365) para este jogo...")
        
        # 2. Buscar as odds de jogadores apenas para a ID deste jogo
        url_odds = f'https://api.the-odds-api.com/v4/sports/basketball_nba/events/{id_do_jogo}/odds'
        parametros_odds = {
            'apiKey': '4da83f576c91a6efcc9b5bac95f6c3ab'

,
            'regions': 'us,eu,uk',      # Regiões onde a Bet365 atua
            'markets': 'player_points', # Mercado de pontos
            'bookmakers': 'bet365'      # Filtrando só a Bet365
        }

        resposta_odds = requests.get(url_odds, params=parametros_odds)

        if resposta_odds.status_code == 200:
            dados_odds = resposta_odds.json()
            print("✅ Sucesso Absoluto! Veja a resposta da API:\n")
            print(json.dumps(dados_odds, indent=4))
        else:
            print(f"❌ Erro ao buscar as odds. Código: {resposta_odds.status_code}")
            print("Detalhe:", resposta_odds.text)
    else:
        print("⚠️ A API conectou, mas não encontrou nenhum jogo agendado para hoje.")
else:
    print(f"❌ Erro ao buscar jogos. Código: {resposta_jogos.status_code}")
    print("Detalhe:", resposta_jogos.text)