import sqlite3
import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import time

print("🏀 Conectando ao banco de dados e aos servidores da NBA...")

conexao = sqlite3.connect('nba_bet.db')
cursor = conexao.cursor()

nba_players = players.get_players()
nome_jogador = 'LeBron James'
jogador_info = next((player for player in nba_players if player['full_name'] == nome_jogador), None)

if not jogador_info:
    print(f"❌ Jogador {nome_jogador} não encontrado.")
    exit()

nba_id = jogador_info['id']
print(f"✅ Jogador encontrado: {nome_jogador} (ID: {nba_id})")
print("📊 Puxando as estatísticas dos últimos jogos...")

historico = playergamelog.PlayerGameLog(player_id=nba_id)
df_jogos = historico.get_data_frames()[0]
ultimos_5_jogos = df_jogos.head(5)

insercoes = 0
jogos_ignorados = 0
player_id_banco = 1 

for index, jogo in ultimos_5_jogos.iterrows():
    data_jogo = jogo['GAME_DATE']
    pts = jogo['PTS']
    reb = jogo['REB']
    ast = jogo['AST']
    stl = jogo['STL']
    blk = jogo['BLK']
    fg3m = jogo['FG3M']

    # TRAVA DE SEGURANÇA: Verifica se este jogo específico já está no banco
    cursor.execute('''
        SELECT id FROM player_stats 
        WHERE player_id = ? AND game_date = ?
    ''', (player_id_banco, data_jogo))
    
    jogo_existe = cursor.fetchone()

    if jogo_existe:
        jogos_ignorados += 1
    else:
        cursor.execute('''
            INSERT INTO player_stats (player_id, pts, reb, ast, stl, blk, fg3m, game_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_id_banco, pts, reb, ast, stl, blk, fg3m, data_jogo))
        insercoes += 1
        print(f"   -> NOVO JOGO SALVO: {data_jogo} | {pts} Pts | {reb} Reb")

conexao.commit()
conexao.close()

print(f"\n🚀 Sucesso! {insercoes} novos jogos salvos. ({jogos_ignorados} jogos já existiam e foram ignorados para evitar duplicidade).")