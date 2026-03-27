# 🏀 IA NBA Props - Assistente de Dados e Risco

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)

Um SaaS (Software as a Service) preditivo para o mercado de Player Props da NBA. O sistema atua como um assistente de gestão de risco, cruzando o histórico recente de jogadores com o ranking defensivo dos times adversários para encontrar disparidades matemáticas no mercado de apostas esportivas.

## 🚀 Funcionalidades

* **🎯 Modo Sniper:** Consulta individual de jogadores. O usuário insere o nome e a linha de aposta, e a API da NBA cruza o Hit Rate (Taxa de Acerto) dos últimos 10 jogos com o adversário atual.
* **📡 Radar Global:** Varredura automática das linhas abertas nas casas de aposta. O algoritmo filtra e exibe apenas as entradas que possuem uma probabilidade de acerto estritamente superior a 70%.
* **🤖 Cérebro Narrador (Google Gemini):** Integração com IA Generativa que escreve análises sintéticas em tempo real sobre a força defensiva do confronto.
* **🌡️ Termômetro de Risco Glassmorphism:** Interface de alto impacto visual desenvolvida com Bootstrap, Animate.css e CSS puro, gerando barras de risco progressivas e design de vidro transparente.

## ⚙️ Como rodar o projeto localmente

1. Clone este repositório:
```bash
git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git)
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
Crie um arquivo `.env` na raiz do projeto e insira suas chaves de API:
```text
CHAVE_ODDS_API=sua_chave_the_odds_api
CHAVE_GEMINI_IA=sua_chave_google_gemini
```

4. Inicie o servidor Flask:
```bash
python app.py
```
Acesse `http://127.0.0.1:5000` no seu navegador.

## ⚠️ Disclaimer e Jogo Responsável
Este software é uma ferramenta de análise estatística e assistência preditiva, não uma bola de cristal ou recomendação financeira. Apostas esportivas envolvem risco financeiro. O objetivo do sistema é auxiliar na gestão de banca e análise de dados. Jogue com responsabilidade.