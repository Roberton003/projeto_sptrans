from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak
from reportlab.lib.enums import TA_CENTER

TITULO = "Guia Instrutivo da API Olho Vivo SPTrans"
ARQUIVO_PDF = "guia_api_olho_vivo_sptrans.pdf"

conteudo = [
    ("Introdução", "A API Olho Vivo da SPTrans permite acesso a dados em tempo real e cadastrais do transporte público de São Paulo. Este guia apresenta os principais recursos, exemplos e dicas para uso profissional da API."),
    ("1. Autenticação", "Todas as requisições exigem autenticação prévia.\nExemplo:\nPOST /Login/Autenticar?token={token}\nRetorno: true (sucesso) ou false (erro)"),
    ("2. Linhas", "- Buscar linhas: GET /Linha/Buscar?termosBusca={termo}\n  Exemplo: /Linha/Buscar?termosBusca=8000\n- Buscar linha por sentido: GET /Linha/BuscarLinhaSentido?termosBusca={termo}&sentido={1|2}\n- Carregar detalhes: GET /Linha/CarregarDetalhes?codigoLinha={codigo}"),
    ("3. Paradas", "- Buscar paradas: GET /Parada/Buscar?termosBusca={termo}\n- Buscar paradas por linha: GET /Parada/BuscarParadasPorLinha?codigoLinha={codigo}\n- Buscar paradas por corredor: GET /Parada/BuscarParadasPorCorredor?codigoCorredor={codigo}"),
    ("4. Corredores", "- Listar corredores: GET /Corredor\nRetorna todos os corredores inteligentes da cidade."),
    ("5. Empresas", "- Listar empresas: GET /Empresa\nRetorna todas as empresas operadoras por área de operação."),
    ("6. Posição dos Veículos", "- Todos os veículos: GET /Posicao\n- Por linha: GET /Posicao/Linha?codigoLinha={codigo}\n- Por garagem: GET /Posicao/Garagem?codigoEmpresa={codigo}[&codigoLinha={codigoLinha}]"),
    ("7. Previsão de Chegada", "- Por parada e linha: GET /Previsao?codigoParada={codigo}&codigoLinha={codigo}\n- Por linha: GET /Previsao/Linha?codigoLinha={codigo}\n- Por parada: GET /Previsao/Parada?codigoParada={codigo}"),
    ("8. Velocidade nas Vias", "- Mapa completo: GET /KMZ\n- Por corredor: GET /KMZ/Corredor\n- Outras vias: GET /KMZ/OutrasVias"),
    ("Exemplo de Uso", "Buscar posição de todos os veículos:\nGET /Posicao\nResposta:\n{\n  'hr': '11:30',\n  'l': [\n    {\n      'c': '5015-10',\n      'cl': 33887,\n      'sl': 2,\n      'lt0': 'METRÔ JABAQUARA',\n      'lt1': 'JD. SÃO JORGE',\n      'qv': 1,\n      'vs': [\n        {\n          'p':68021,\n          'a':true,\n          'ta':'2017-05-12T14:30:37Z',\n          'py':-23.6787,\n          'px':-46.6567\n        }\n      ]\n    }\n  ]\n}"),
    ("Dicas e Possibilidades", "- Sempre autentique antes de qualquer requisição.\n- Use os endpoints de busca para obter códigos necessários para outras consultas.\n- Combine dados de diferentes endpoints para análises mais ricas.\n- Os dados de posição e previsão são dinâmicos e mudam ao longo do dia.\n- Possível criar dashboards, mapas, alertas, análises de mobilidade e eficiência operacional."),
    ("Referência", "Documentação oficial: https://www.sptrans.com.br/desenvolvedores/api-do-olho-vivo-guia-de-referencia/documentacao-api/")
]

def gerar_pdf_instrutivo_moderno(arquivo_pdf, titulo, conteudo):
    doc = SimpleDocTemplate(arquivo_pdf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []
    style_title = styles['Title']
    style_title.alignment = TA_CENTER
    story.append(Paragraph(titulo, style_title))
    story.append(Spacer(1, 18))
    for secao, texto in conteudo:
        story.append(Paragraph(f'<b>{secao}</b>', styles['Heading2']))
        for par in texto.split('\n'):
            if par.strip():
                story.append(Paragraph(par, styles['Normal']))
        story.append(Spacer(1, 12))
    doc.build(story)
    print(f"PDF gerado: {arquivo_pdf}")

if __name__ == "__main__":
    gerar_pdf_instrutivo_moderno(ARQUIVO_PDF, TITULO, conteudo)
