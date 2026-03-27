import sqlite3

print("🧠 Ligando o Motor de Análise Avançado...")

conexao = sqlite3.connect('nba_bet.db')
cursor = conexao.cursor()

jogador_id = 1 
# Aqui simulamos as linhas que a Bet365 ofereceu para esse jogador hoje
linhas_bet365 = {
    'pts': 25.5,   # Pontos
    'reb': 7.5,    # Rebotes
    'ast': 8.5,    # Assistências
    'fg3m': 2.5    # Cestas de 3
}

# Nomes bonitos para exibir na tela
nomes_mercados = {'pts': 'Pontos', 'reb': 'Rebotes', 'ast': 'Assistências', 'fg3m': 'Cestas de 3'}

print(f"\n📊 VASculhando AS MELHORES OPORTUNIDADES (Garantindo os últimos 5 jogos):")
print("-" * 60)

# O sistema vai testar mercado por mercado
for mercado, linha in linhas_bet365.items():
    
    # Busca estritamente os últimos 5 jogos garantidos
    cursor.execute(f'''
        SELECT {mercado}, game_date 
        FROM player_stats 
        WHERE player_id = ? 
        ORDER BY game_date DESC 
        LIMIT 5
    ''', (jogador_id,))

    jogos = cursor.fetchall()
    
    if len(jogos) < 5:
        print(f"❌ Aguardando mais dados. Temos apenas {len(jogos)} jogos no banco.")
        continue

    total = 0
    vezes_bateu_a_linha = 0

    for jogo in jogos:
        valor = jogo[0]
        total += valor
        if valor > linha:
            vezes_bateu_a_linha += 1

    media = total / len(jogos)
    recomendacao = 'MAIS DE' if media > linha else 'MENOS DE'
    taxa_acerto = (vezes_bateu_a_linha / len(jogos)) * 100

    # Calcula a confiança
    if recomendacao == 'MAIS DE':
        confianca = taxa_acerto + ((media - linha) * 2)
    else:
        confianca = (100 - taxa_acerto) + ((linha - media) * 2)

    confianca = min(confianca, 99.0)

    # Destaca a oportunidade se for muito boa (acima de 80%)
    alerta = "🔥" if confianca >= 80 else "  "

    print(f"{alerta} Mercado: {nomes_mercados[mercado].ljust(15)} | Linha: {linha}")
    print(f"   Média Real: {media:.1f} | Bateu a linha: {vezes_bateu_a_linha} de 5 vezes")
    print(f"   Recomendação: {recomendacao} | Confiança: {confianca:.1f}%\n")

conexao.close()
print("-" * 60)
print("✅ Análise concluída.")