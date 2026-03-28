import requests

# Suas chaves exatas
URL = "https://thorough-crayfish-86582.upstash.io"
TOKEN = "gQAAAAAAAVI2AAIncDE0MGE1YmM4ZDJiZDE0ZDViYjBhMzZhMmY3OGE1NGNhNXAxODY1ODI"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("1. Testando envio para a nuvem...")
# Mandando um texto simples para ver se ele aceita
resposta_salvar = requests.post(f"{URL}/set/teste_juninho", headers=headers, json="FOGUETE NUVEM OK")
print("Resposta do Banco (Salvar):", resposta_salvar.json())

print("\n2. Testando leitura da nuvem...")
resposta_ler = requests.get(f"{URL}/get/teste_juninho", headers=headers)
print("Resposta do Banco (Ler):", resposta_ler.json())