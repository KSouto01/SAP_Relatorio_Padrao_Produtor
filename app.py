# VERSÃO: 13.3 - Nome Oficial: Relatório Padrão Produtor (R.P.P)
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
# MUDANÇA: Título da Aba do Navegador
app.title = "R.P.P - Relatório Padrão"
server = app.server

BADGE_STYLE = {
    "backgroundColor": "#EF6100", "color": "white", "fontSize": "0.85rem",
    "padding": "4px 8px", "marginRight": "5px", "borderRadius": "4px",
    "fontWeight": "bold", "display": "inline-block"
}

ORDEM_COLUNAS = [
    "ID.apl", "Razão Social", "contrato", "Instr. EDC", "Romaneio", 
    "Data do edc", "Material", "NomeMaterial", "NomeSafra", "Unidade", "Placa", 
    "Nota Produtor", "Nota Fazendao", 
    "Transgenia", "Peso Bruto (Kg)", "Peso Tara (Kg)", "Peso liquido (Kg)", 
    "Qtd Aplicada (Kg)", "Descontos (Kg)", "% Umidade", "Desconto Umidade (Kg)", 
    "% Impurezas", "Desconto Impureza (Kg)"
]

app.layout = dbc.Container([
    dcc.Store(id="store-dados"),
    dcc.Store(id="store-lista-fornecedores"),
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([html.Img(src="/assets/logo.png", height="30px", className="me-2"), 
                         # MUDANÇA: Título da Navbar
                         html.Span("Relatório Padrão Produtor", style={"color": "white", "fontWeight": "bold", "fontSize": "1.1rem"})], className="d-flex align-items-center"),
                dbc.Col([html.Div([html.Span("T.I Fazendão | Klaus Maya Souto", className="d-block text-white small text-end fw-bold")])])
            ], className="w-100 justify-content-between")
        ], fluid=True), color="#0C5959", dark=True, className="py-1 flex-shrink-0"
    ),
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Base", className="fw-bold small mb-0"),
                    dbc.RadioItems(id="radio-taxa", options=[{"label": "CPF", "value": "cpf"}, {"label": "CNPJ", "value": "cnpj"}], value="cpf", inline=True, style={"fontSize": "0.8rem"})
                ], width=2, className="border-end"),
                dbc.Col([dbc.Label("Nome", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-nome", placeholder="Nome...", className="small-dropdown-sm")], width=4),
                dbc.Col([dbc.Label("Cód. SAP", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-codigo", placeholder="Cód...", className="small-dropdown-sm")], width=2),
                dbc.Col([dbc.Label("Documento", className="small fw-bold mb-0"), dcc.Dropdown(id="dd-doc", placeholder="Doc...", className="small-dropdown-sm")], width=4),
            ], className="mb-2 g-1 align-items-end"),
            dbc.Row([
                dbc.Col([dbc.Label("Início", className="small mb-0"), dbc.Input(id="dt-inicio", type="date", value=date.today().replace(day=1), size="sm")], width=2),
                dbc.Col([dbc.Label("Fim", className="small mb-0"), dbc.Input(id="dt-fim", type="date", value=date.today(), size="sm")], width=2),
                dbc.Col([dbc.Label("Material", className="small mb-0 fw-bold text-primary"), dcc.Dropdown(id="dd-material", placeholder="Todos", clearable=True, className="small-dropdown-sm")], width=2),
                dbc.Col([dbc.Label("Safra", className="small mb-0 fw-bold text-success"), dcc.Dropdown(id="dd-safra", placeholder="Todas", clearable=True, className="small-dropdown-sm")], width=2),
                dbc.Col([dbc.Label("Ação", className="small mb-0 text-white"), dbc.Button([html.I(className="bi bi-search me-1"), "Buscar"], id="btn-carregar", color="success", size="sm", className="w-100 fw-bold")], width=2),
                dbc.Col([dbc.Label("Exportar", className="small mb-0 text-secondary"), dbc.ButtonGroup([dbc.Button(html.I(className="bi bi-file-earmark-excel"), id="btn-excel", color="success", outline=True, size="sm", title="Excel"), dbc.Button(html.I(className="bi bi-file-text"), id="btn-pdf-resumido", color="danger", outline=True, size="sm", title="PDF Resumido"), dbc.Button(html.I(className="bi bi-file-earmark-pdf-fill"), id="btn-pdf-detalhado", color="danger", size="sm", title="PDF Detalhado")], className="w-100")], width=2)
            ], className="g-1 align-items-end")
        ], className="p-2")
    ], className="mb-2 shadow-sm mx-2 flex-shrink-0"),
    html.Div(id="barra-totais", className="mb-1 mx-2 d-flex flex-wrap gap-2 flex-shrink-0"),
    html.Div(
        className="flex-grow-1 mx-2 mb-0 border rounded overflow-hidden bg-white d-flex flex-column",
        style={"minHeight": "0"}, 
        children=[dcc.Loading(id="loading-wrapper", color="#EF6100", parent_style={"flex": "1", "display": "flex", "flexDirection": "column", "overflow": "hidden"}, children=[html.Div(id="area-tabela", style={"flex": "1", "display": "flex", "flexDirection": "column", "overflow": "hidden"})])]
    ),
    dcc.Download(id="download-files")
], fluid=True, className="vh-100 d-flex flex-column bg-light p-0 overflow-hidden")

@app.callback(Output("store-lista-fornecedores", "data"), Input("radio-taxa", "value"))
def carregar_base_local(tipo):
    df = sap.buscar_fornecedores(tipo)
    return df.to_dict('records') if not df.empty else []

@app.callback([Output("dd-nome", "options"), Output("dd-codigo", "options"), Output("dd-doc", "options")], Input("store-lista-fornecedores", "data"))
def popular_opcoes(data):
    if not data: return [], [], []
    opts_nome = sorted([{'label': d['SupplierName'], 'value': d['SupplierName']} for d in data], key=lambda x: x['label'])
    opts_cod = sorted([{'label': f"{d['Supplier']}", 'value': d['Supplier']} for d in data], key=lambda x: x['label'])
    opts_doc = sorted([{'label': d['BPTaxNumber'], 'value': d['BPTaxNumber']} for d in data], key=lambda x: x['label'])
    return opts_nome, opts_cod, opts_doc

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

@app.callback(Output("store-dados", "data"), Output("dd-material", "options"), Output("dd-material", "value"), Output("dd-safra", "options"), Output("dd-safra", "value"), Input("btn-carregar", "n_clicks"), State("dt-inicio", "value"), State("dt-fim", "value"), State("dd-codigo", "value"), prevent_initial_call=True)
def buscar_dados_sap(n, start, end, parceiro_id):
    if not parceiro_id: return [], [], None, [], None
    df = sap.buscar_dados_por_periodo(start, end, parceiro_id=parceiro_id)
    if df.empty: return [], [], None, [], None
    materiais = sorted(df['NomeMaterial'].astype(str).dropna().unique())
    safras = sorted(df['NomeSafra'].astype(str).dropna().unique())
    return df.to_dict('records'), [{'label': m, 'value': m} for m in materiais], None, [{'label': s, 'value': s} for s in safras], None

@app.callback(Output("area-tabela", "children"), Output("barra-totais", "children"), Input("store-dados", "data"), Input("dd-material", "value"), Input("dd-safra", "value"))
def atualizar_tabela_totais(data, material_sel, safra_sel):
    if not data: return dbc.Alert("Aguardando busca...", color="light", className="text-center small m-5"), []
    df = pd.DataFrame(data)
    if material_sel: df = df[df['NomeMaterial'] == material_sel]
    if safra_sel: df = df[df['NomeSafra'] == safra_sel]
    if df.empty: return dbc.Alert("Sem dados.", color="warning", className="m-5"), []
    
    totais = {"Bruto": df["Peso Bruto (Kg)"].sum(), "Tara": df["Peso Tara (Kg)"].sum(), "Líquido": df["Peso liquido (Kg)"].sum(), "Aplicada": df["Qtd Aplicada (Kg)"].sum(), "Descontos": df["Descontos (Kg)"].sum()}
    badges = [html.Span([f"{k}: ", html.B(f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))], style=BADGE_STYLE) for k, v in totais.items()]
    
    cols_extras = [c for c in df.columns if c not in ORDEM_COLUNAS and c not in ["Cod. Parceiro", "DataLancamento", "Cancelado"]]
    cols_final = [c for c in ORDEM_COLUNAS if c in df.columns] + cols_extras

    cols = [{"name": c, "id": c, "type": 'numeric' if "(Kg)" in c or "%" in c else 'text', "format": Format(precision=2, scheme=Scheme.fixed, group=Group.yes, group_delimiter='.', decimal_delimiter=',') if "(Kg)" in c or "%" in c else None} for c in cols_final]

    tabela = dash_table.DataTable(
        data=df.to_dict('records'), columns=cols, fixed_rows={'headers': True},
        style_table={'height': '100%', 'maxHeight': '100%', 'overflowY': 'auto'},
        page_action="none", virtualization=True, filter_action="native", sort_action="native",
        style_header={'backgroundColor': '#0C5959', 'color': 'white', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_cell={'fontSize': '10px', 'textAlign': 'left', 'padding': '2px 5px', 'minWidth': '80px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
    )
    return tabela, badges

@app.callback(Output("download-files", "data"), Input("btn-excel", "n_clicks"), Input("btn-pdf-resumido", "n_clicks"), Input("btn-pdf-detalhado", "n_clicks"), State("store-dados", "data"), State("dt-inicio", "value"), State("dt-fim", "value"), State("dd-nome", "value"), State("dd-codigo", "value"), State("dd-material", "value"), State("dd-safra", "value"), prevent_initial_call=True)
def exportar(n_ex, n_res, n_det, data, start, end, nome_p, cod_p, material_sel, safra_sel):
    if not data: return no_update
    ctx_id = ctx.triggered_id
    df = pd.DataFrame(data)
    if material_sel: df = df[df['NomeMaterial'] == material_sel]
    if safra_sel: df = df[df['NomeSafra'] == safra_sel]
    periodo = f"{datetime.strptime(start, '%Y-%m-%d').strftime('%d/%m/%Y')} a {datetime.strptime(end, '%Y-%m-%d').strftime('%d/%m/%Y')}"
    parceiro_label = f"{nome_p} ({cod_p})" if nome_p else cod_p
    safra_label = safra_sel if safra_sel else "TODAS AS SAFRAS"
    material_label = material_sel if material_sel else "TODOS OS MATERIAIS"

    if ctx_id == "btn-excel": return dcc.send_data_frame(df.to_excel, f"Relatorio_{cod_p}.xlsx", index=False)
    elif ctx_id == "btn-pdf-resumido": return dcc.send_bytes(gerar_pdf_resumido(df, parceiro_label, material_label, safra_label, periodo).getvalue(), f"Resumido_{cod_p}.pdf")
    elif ctx_id == "btn-pdf-detalhado": return dcc.send_bytes(gerar_pdf_detalhado(df, parceiro_label, material_label, safra_label, periodo).getvalue(), f"Detalhado_{cod_p}.pdf")
    return no_update

if __name__ == "__main__":
    app.run(debug=False, port=8052, host='0.0.0.0')