import requests
import time
import json

# Substitua pelo seu token da SPTrans
TOKEN = 'SUA_CHAVE_AQUI'
BASE_URL = 'http://api.olhovivo.sptrans.com.br/v2.1'

# Função para autenticar na API
def autenticar(token):
    url = f"{BASE_URL}/Login/Autenticar?token={token}"
    resp = requests.post(url)
    if resp.status_code == 200 and resp.json() is True:
        print('Autenticado com sucesso!')
        return True
    else:
        print('Falha na autenticação:', resp.text)
        return False

# Função para coletar posição dos ônibus
def coletar_posicoes():
    url = f"{BASE_URL}/Posicao"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    else:
        print('Erro ao coletar posições:', resp.text)
        return None

if __name__ == "__main__":
    if autenticar(TOKEN):
        dados = coletar_posicoes()
        if dados:
            # Salva os dados em um arquivo JSON
            with open('posicoes_onibus.json', 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            print('Dados salvos em posicoes_onibus.json')
        else:
            print('Nenhum dado coletado.')
    else:
        print('Não foi possível autenticar na API.')
