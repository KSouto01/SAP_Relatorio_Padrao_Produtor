# VERSÃO: 12.3 - Layout Single Screen (Sem Scroll da Página)
import dash
from dash import dcc, html, Input, Output, State, dash_table, no_update, ctx
import dash_bootstrap_components as dbc
from datetime import date, datetime
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Group
from backend.sap_data import SAPConnector
from backend.pdf_generator import gerar_pdf_detalhado, gerar_pdf_resumido

sap = SAPConnector()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])
app.title = "Relatório Produtor v12.3"
server = app.server

# --- ESTILOS COMPACTOS ---
BADGE_STYLE = {
    "backgroundColor": "#EF6100", 
    "color": "white", 
    "fontSize": "0.85rem", # Fonte menor
    "padding": "4px 8px", 
    "marginRight": "5px",
    "borderRadius": "4px",
    "fontWeight": "bold",
    "display": "inline-block"
}

# Estilo para forçar a tabela a caber na tela sem scroll da página
TABELA_STYLE = {
    'height': 'calc(100vh - 260px)', # Calcula altura restante (100% da tela menos o cabeçalho)
    'overflowY': 'auto'
}

app.layout = dbc.Container([
    dcc.Store(id="store-dados"),
    dcc.Store(id="store-lista-fornecedores"),

    # --- NAVBAR (Compacta: py-1) ---
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([html.Img(src="/assets/logo.png", height="30px", className="me-2"), html.Span("Relatório Produtor", style={"color": "white", "fontWeight": "bold", "fontSize": "1.1rem"})], className="d-flex align-items-center"),
                dbc.Col([html.Div([html.Span("T.I Fazendão | Klaus Maya Souto", className="d-block text-white small text-end")])])
            ], className="w-100 justify-content-between")
        ], fluid=True), color="#0C5959", dark=True, className="mb-2 py-1"
    ),

    # --- SUPER CARD DE FILTROS (Tudo em um lugar) ---
    dbc.Card([
        dbc.CardBody([
            # LINHA 1: Tipo + Identificação do Parceiro
            dbc.Row([
                # Coluna Tipo (Compacta)
                dbc.Col([
                    dbc.Label("Base", className="fw-bold small mb-0"),
                    dbc.RadioItems(
                        id="radio-taxa",
                        options=[{"label": "CPF", "value": "cpf"}, {"label": "CNPJ", "value": "cnpj"}],
                        value="cpf",
                        inline=True,
                        style={"fontSize": "0.8rem"}
                    )
                ], width=2, className="border-end"),

                # Colunas de Parceiro
                dbc.Col([dbc.Label("Nome", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-nome", placeholder="Nome...", className="small-dropdown-sm")], width=4),
                dbc.Col([dbc.Label("Cód. SAP", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-codigo", placeholder="Cód...", className="small-dropdown-sm")], width=2),
                dbc.Col([dbc.Label("Documento", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-doc", placeholder="Doc...", className="small-dropdown-sm")], width=4),
            ], className="mb-2 g-1 align-items-end"),

            # LINHA 2: Datas + Material + Botão + Exportação
            dbc.Row([
                # Datas
                dbc.Col([dbc.Label("Início", className="small mb-0"), dbc.Input(id="dt-inicio", type="date", value=date.today().replace(day=1), size="sm")], width=2),
                dbc.Col([dbc.Label("Fim", className="small mb-0"), dbc.Input(id="dt-fim", type="date", value=date.today(), size="sm")], width=2),
                
                # Filtro Material (Agora fixo aqui)
                dbc.Col([
                    dbc.Label("Material", className="small mb-0 fw-bold text-primary"),
                    dcc.Dropdown(id="dd-material", placeholder="Todos", clearable=True, className="small-dropdown-sm")
                ], width=3),

                # Botão Buscar
                dbc.Col([
                    dbc.Label("Ação", className="small mb-0 text-white"),
                    dbc.Button([html.I(className="bi bi-search me-1"), "Buscar"], id="btn-carregar", color="success", size="sm", className="w-100 fw-bold")
                ], width=2),

                # Botões Exportar (Icones apenas para economizar espaço)
                dbc.Col([
                    dbc.Label("Exportar", className="small mb-0 text-secondary"),
                    dbc.ButtonGroup([
                        dbc.Button(html.I(className="bi bi-file-earmark-excel"), id="btn-excel", color="success", outline=True, size="sm", title="Excel"),
                        dbc.Button(html.I(className="bi bi-file-text"), id="btn-pdf-resumido", color="danger", outline=True, size="sm", title="PDF Resumido"),
                        dbc.Button(html.I(className="bi bi-file-earmark-pdf-fill"), id="btn-pdf-detalhado", color="danger", size="sm", title="PDF Detalhado")
                    ], className="w-100")
                ], width=3)
            ], className="g-1 align-items-end")
        ], className="p-2") # Padding interno reduzido
    ], className="mb-2 shadow-sm mx-2"),

    # --- LINHA DE TOTAIS ---
    html.Div(id="barra-totais", className="mb-1 mx-2 d-flex flex-wrap gap-2"),

    # --- TABELA (Com Scroll Interno) ---
    dcc.Loading(
        html.Div(id="area-tabela", style={'margin': '0 10px', 'borderRadius': '5px', 'overflow': 'hidden'}), 
        color="#EF6100"
    ),
    dcc.Download(id="download-files")

], fluid=True, className="vh-100 bg-light p-0 overflow-hidden") # overflow-hidden na pagina principal


# --- CALLBACKS ---

# 1. Carregar Base
@app.callback(Output("store-lista-fornecedores", "data"), Input("radio-taxa", "value"))
def carregar_base_local(tipo):
    df = sap.buscar_fornecedores(tipo)
    return df.to_dict('records') if not df.empty else []

# 2. Popular Dropdowns
@app.callback([Output("dd-nome", "options"), Output("dd-codigo", "options"), Output("dd-doc", "options")], Input("store-lista-fornecedores", "data"))
def popular_opcoes(data):
    if not data: return [], [], []
    opts_nome = sorted([{'label': d['SupplierName'], 'value': d['SupplierName']} for d in data], key=lambda x: x['label'])
    opts_cod = sorted([{'label': f"{d['Supplier']} - {d['SupplierName']}", 'value': d['Supplier']} for d in data], key=lambda x: x['label'])
    opts_doc = sorted([{'label': d['BPTaxNumber'], 'value': d['BPTaxNumber']} for d in data], key=lambda x: x['label'])
    return opts_nome, opts_cod, opts_doc

# 3. Sincronizar
@app.callback([Output("dd-nome", "value"), Output("dd-codigo", "value"), Output("dd-doc", "value")], [Input("dd-nome", "value"), Input("dd-codigo", "value"), Input("dd-doc", "value")], State("store-lista-fornecedores", "data"), prevent_initial_call=True)
def sincronizar_filtros(nome, codigo, doc, data):
    if not data: return no_update, no_update, no_update
    ctx_id = ctx.triggered_id
    df = pd.DataFrame(data)
    row = None
    if ctx_id == "dd-nome" and nome: row = df[df['SupplierName'] == nome]
    elif ctx_id == "dd-codigo" and codigo: row = df[df['Supplier'] == codigo]
    elif ctx_id == "dd-doc" and doc: row = df[df['BPTaxNumber'] == doc]
    
    if row is not None and not row.empty:
        r = row.iloc[0]
        return r['SupplierName'], r['Supplier'], r['BPTaxNumber']
    return no_update, no_update, no_update

# 4. Buscar Dados e Popular Material (Removido collapse output pois agora é fixo)
@app.callback(
    Output("store-dados", "data"),
    Output("dd-material", "options"),
    Output("dd-material", "value"),
    Input("btn-carregar", "n_clicks"),
    State("dt-inicio", "value"),
    State("dt-fim", "value"),
    State("dd-codigo", "value"),
    prevent_initial_call=True
)
def buscar_dados_sap(n, start, end, parceiro_id):
    if not parceiro_id: return [], [], None
    
    df = sap.buscar_dados_por_periodo(start, end, parceiro_id=parceiro_id)
    if df.empty: return [], [], None
    
    materiais = sorted(df['NomeMaterial'].astype(str).dropna().unique())
    opts_mat = [{'label': m, 'value': m} for m in materiais]
    
    return df.to_dict('records'), opts_mat, None

# 5. Tabela e Totais
@app.callback(Output("area-tabela", "children"), Output("barra-totais", "children"), Input("store-dados", "data"), Input("dd-material", "value"))
def atualizar_tabela_totais(data, material_selecionado):
    if not data: return dbc.Alert("Aguardando busca...", color="light", className="text-center small"), []
    df = pd.DataFrame(data)
    
    if material_selecionado:
        df = df[df['NomeMaterial'] == material_selecionado]
        if df.empty: return dbc.Alert("Sem dados para este material.", color="warning"), []
    
    totais = {
        "Bruto": df["Peso Bruto (Kg)"].sum(),
        "Tara": df["Peso Tara (Kg)"].sum(),
        "Líquido": df["Peso liquido (Kg)"].sum(),
        "Aplicada": df["Qtd Aplicada (Kg)"].sum(),
        "Descontos": df["Descontos (Kg)"].sum()
    }
    badges = [html.Span([f"{k}: ", html.B(f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))], style=BADGE_STYLE) for k, v in totais.items()]
    
    cols = []
    formato_num = Format(precision=2, scheme=Scheme.fixed, group=Group.yes, group_delimiter='.', decimal_delimiter=',')
    for c in df.columns:
        if c in ["Cod. Parceiro", "DataLancamento", "Cancelado"]: continue
        tipo = 'numeric' if "(Kg)" in c or "%" in c else 'text'
        cols.append({"name": c, "id": c, "type": tipo, "format": formato_num if tipo=='numeric' else None})

    # Tabela com Altura Fixa (Scroll Interno)
    tabela = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=cols,
        fixed_rows={'headers': True}, # Cabeçalho fixo
        style_table=TABELA_STYLE,    # Altura calculada para tela cheia
        page_action="none",          # Scroll infinito virtual (sem paginação 1,2,3)
        virtualization=True,         # Renderização rápida
        filter_action="native",
        sort_action="native",
        style_header={'backgroundColor': '#0C5959', 'color': 'white', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_cell={'fontSize': '10px', 'textAlign': 'left', 'padding': '2px 5px', 'minWidth': '80px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
    )
    return tabela, badges

# 6. Exportação
@app.callback(Output("download-files", "data"), Input("btn-excel", "n_clicks"), Input("btn-pdf-resumido", "n_clicks"), Input("btn-pdf-detalhado", "n_clicks"), State("store-dados", "data"), State("dt-inicio", "value"), State("dt-fim", "value"), State("dd-nome", "value"), State("dd-codigo", "value"), State("dd-material", "value"), prevent_initial_call=True)
def exportar(n_ex, n_res, n_det, data, start, end, nome_p, cod_p, material_sel):
    if not data: return no_update
    ctx_id = ctx.triggered_id
    df = pd.DataFrame(data)
    
    material_label = material_sel if material_sel else "TODOS OS MATERIAIS"
    if material_sel: df = df[df['NomeMaterial'] == material_sel]
    
    periodo = f"{datetime.strptime(start, '%Y-%m-%d').strftime('%d/%m/%Y')} a {datetime.strptime(end, '%Y-%m-%d').strftime('%d/%m/%Y')}"
    parceiro_label = f"{nome_p} ({cod_p})" if nome_p else cod_p

    if ctx_id == "btn-excel": return dcc.send_data_frame(df.to_excel, f"Relatorio_{cod_p}.xlsx", index=False)
    elif ctx_id == "btn-pdf-resumido": buffer = gerar_pdf_resumido(df, parceiro_label, material_label, periodo); return dcc.send_bytes(buffer.getvalue(), f"Resumido_{cod_p}.pdf")
    elif ctx_id == "btn-pdf-detalhado": buffer = gerar_pdf_detalhado(df, parceiro_label, material_label, periodo); return dcc.send_bytes(buffer.getvalue(), f"Detalhado_{cod_p}.pdf")
    return no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050, host='0.0.0.0')