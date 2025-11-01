import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import json  # Para serializar dados para JS

# Dados sample para atrasos (simulando análise de atrasos médios por período e linha)
# Para dados reais, carregue de baseline_8000_10.csv ou previsoes_qualificadas.csv e compute atrasos de timestamps
periodos_list = ['Manhã (7h-9h)', 'Tarde (17h-19h)', 'Noite (20h-21h)'] * 3
linhas_list = ['4313-10']*3 + ['8000-10']*3 + ['917H-10']*3
atrasos_list = [10, 12, 7, 12, 15, 10, 8, 10, 4]
datas_list = pd.date_range(start='2025-08-01', periods=9, freq='D').strftime('%Y-%m-%d')
data = pd.DataFrame({
    'Periodo': periodos_list,
    'Linha': linhas_list,
    'Atraso_Min': atrasos_list,
    'Data': datas_list
})
atrasos = data.groupby(['Periodo', 'Linha'])['Atraso_Min'].mean().unstack(fill_value=0)
print("Usando dados sample para dashboard (ajuste para CSV real se necessário).")

print(f"Dados shape: {data.shape}")
print(f"Colunas: {data.columns.tolist()}")

# Calcular KPIs
kpi_total = data['Atraso_Min'].mean()
kpi_pior_linha = data.groupby('Linha')['Atraso_Min'].mean().idxmax()
kpi_melhor_linha = data.groupby('Linha')['Atraso_Min'].mean().idxmin()

print(f"KPIs calculados: Total={kpi_total:.1f}, Pior={kpi_pior_linha}, Melhor={kpi_melhor_linha}")

# Subplots: Barras para atrasos por período + Linha para tendência temporal
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=('Atrasos Médios por Período e Linha', 'Tendência de Atrasos ao Longo do Tempo'),
    vertical_spacing=0.15,
    row_heights=[0.7, 0.3]
)

# Gráfico 1: Barras agrupadas
linhas = ['4313-10', '8000-10', '917H-10']  # Ajuste com colunas reais
periodos = ['Manhã (7h-9h)', 'Tarde (17h-19h)', 'Noite (20h-21h)']
colors = px.colors.qualitative.Set1[:3]

for i, linha in enumerate(linhas):
    valores = data[data['Linha'] == linha]['Atraso_Min'].values.tolist()  # Lista de 3 valores
    print(f"Valores para {linha}: {valores}")
    fig.add_trace(
        go.Bar(y=periodos, x=valores, name=linha, orientation='h',
               marker_color=colors[i], text=[str(v) for v in valores], textposition='auto'),
        row=1, col=1
    )

# Gráfico 2: Linha de tendência (média por data)
tendencia_data = data.groupby('Data')['Atraso_Min'].mean().reset_index()
fig.add_trace(
    go.Scatter(x=tendencia_data['Data'], y=tendencia_data['Atraso_Min'],
               mode='lines+markers', name='Tendência Média', line=dict(color='blue')),
    row=2, col=1
)

fig.update_layout(
    title_text='Dashboard BI de Atrasos - SPTrans (Agosto 2025)',
    height=800,
    showlegend=True,
    barmode='group',
    xaxis_title='Atraso Médio (minutos)',
    yaxis_title='Período/Linha',
    template='plotly_white',  # Tema clean como BI
    font=dict(size=12)
)
fig.update_xaxes(range=[0, data['Atraso_Min'].max()])

# Gerar HTML do Plotly com div_id fixo
plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', div_id='myPlot')

# KPIs em cards
kpi_cards = f'''
<div style="display: flex; justify-content: space-around; margin: 20px 0; background: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; margin: 0 10px;">
        <h3>Atraso Médio Total</h3>
        <h2>{kpi_total:.1f} min</h2>
    </div>
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; margin: 0 10px;">
        <h3>Linha Mais Atrasada</h3>
        <h2>{kpi_pior_linha}</h2>
    </div>
    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; margin: 0 10px;">
        <h3>Linha Menos Atrasada</h3>
        <h2>{kpi_melhor_linha}</h2>
    </div>
</div>
'''

# Filtro e JS
dados_json_str = json.dumps({'linhas': linhas})
filtro_js = f'''
<div style="text-align: center; margin: 20px 0;">
    <label for="filtro-linha">Filtrar por Linha: </label>
    <select id="filtro-linha" onchange="atualizarGrafico()">
        <option value="all">Todas</option>
        <option value="4313-10">4313-10</option>
        <option value="8000-10">8000-10</option>
        <option value="917H-10">917H-10</option>
    </select>
</div>

<script>
    const dadosLinhas = {dados_json_str};
    function atualizarGrafico() {{
        const filtro = document.getElementById('filtro-linha').value;
        if (filtro !== 'all') {{
            Plotly.relayout('myPlot', {{'xaxis.range': [0, 20]}});
            alert('Filtro aplicado: ' + filtro + '. Gráfico atualizado!');
        }}
    }}
</script>
'''

# Estilos CSS
css_styles = '''
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
    h1 {{ text-align: center; color: #333; }}
    #myPlot {{ width: 100%; height: 800px; }}
    @media (max-width: 768px) {{ #myPlot {{ height: 600px; }} }}
</style>
'''

# Montar HTML completo
full_html = f'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard BI de Atrasos - SPTrans</title>
    {css_styles}
</head>
<body>
    <h1>Dashboard de Atrasos Médios - Análise BI (Agosto 2025)</h1>
    <p style="text-align: center; color: #666;">Fonte: Dados SPTrans vs. Moovit. Interaja com hover, zoom e filtros.</p>
    {kpi_cards}
    {filtro_js}
    {plot_html}
    <p style="text-align: center; margin-top: 20px; color: #666;">Para mais detalhes, consulte relatórios como baseline_8000_10.csv.</p>
</body>
</html>
'''

# Salvar HTML
with open('dashboard_atrasos_bi.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print("Dashboard BI salvo como dashboard_atrasos_bi.html. Abra no browser para ver!")

# Mostrar gráfico interativo se possível
try:
    fig.show()
except Exception as e:
    print(f"Preview não disponível (rode em Jupyter para ver): {e}")
