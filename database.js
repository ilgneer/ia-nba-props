const sqlite3 = require('sqlite3').verbose();

// Isso vai criar um arquivo chamado 'nba_bet.db' na sua pasta automaticamente
const db = new sqlite3.Database('./nba_bet.db');

db.serialize(() => {
    // 1. Tabela de Jogadores
    db.run(`CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        team TEXT,
        position TEXT
    )`);

    // 2. Tabela de Jogos (para o filtro de partida específica)
    db.run(`CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        home_team TEXT,
        away_team TEXT,
        game_date DATETIME
    )`);

    // 3. Tabela de Linhas da Bet365 (com o mercado de pontos, rebotes, etc)
    db.run(`CREATE TABLE IF NOT EXISTS betting_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        game_id INTEGER,
        market_type TEXT,
        line_value REAL,
        FOREIGN KEY(player_id) REFERENCES players(id),
        FOREIGN KEY(game_id) REFERENCES games(id)
    )`);

    // 4. Tabela de Projeções da IA (para o filtro das "Top 8" com maior confiança)
    db.run(`CREATE TABLE IF NOT EXISTS ai_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        betting_line_id INTEGER,
        projected_value REAL,
        recommendation TEXT,
        confidence_percentage REAL,
        FOREIGN KEY(betting_line_id) REFERENCES betting_lines(id)
    )`);

    console.log("Tabelas criadas com sucesso, chefe!");
});

db.close();