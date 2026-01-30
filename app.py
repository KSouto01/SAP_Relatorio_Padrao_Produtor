# VERSÃO DO ARQUIVO: 10.12
import dash
from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
from datetime import date, datetime
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Group
from backend.sap_data import SAPConnector
from backend.pdf_generator import gerar_pdf_oficial

sap = SAPConnector()

app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
app.title = "Relatório Padrão Produtor"

# --- LAYOUT ---
app.layout = dbc.Container([
    dcc.Store(id="store-dados-brutos"),

    # 1. NAVBAR (Com Créditos à Direita)
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                # Lado Esquerdo: Logo + Título
                dbc.Col([
                    html.Div([
                        html.Img(src="/assets/logo.png", height="40px", className="me-3"),
                        html.Span("Relatório Padrão Produtor", style={"fontWeight": "bold", "fontSize": "1.4rem", "color": "white", "fontFamily": "Arial"})
                    ], className="d-flex align-items-center")
                ], width="auto"),
                
                # Lado Direito: Créditos
                dbc.Col([
                    html.Div([
                        html.Span("Equipe: T.I Fazendão", className="d-block", style={"fontSize": "11px", "color": "white", "textAlign": "right", "fontFamily": "Arial"}),
                        html.Span("Dev: Klaus Maya Souto", className="d-block", style={"fontSize": "11px", "color": "white", "textAlign": "right", "fontFamily": "Arial", "fontWeight": "bold"})
                    ])
                ], width="auto", className="d-flex align-items-center")
                
            ], className="w-100 justify-content-between align-items-center") # Distribui itens nas pontas
        ], fluid=True),
        color="#0C5959", dark=True, className="mb-3 shadow-sm"
    ),

    # 2. PAINEL DE CONTROLE
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Data Inicial", className="fw-bold text-secondary small mb-1", style={"fontFamily": "Arial"}),
                    dbc.Input(id="dt-inicio", type="date", value=date.today().replace(day=1), size="sm")
                ], width=3),
                dbc.Col([
                    dbc.Label("Data Final", className="fw-bold text-secondary small mb-1", style={"fontFamily": "Arial"}),
                    dbc.Input(id="dt-fim", type="date", value=date.today(), size="sm")
                ], width=3),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Carregar Dados"],
                        id="btn-carregar", color="success", size="sm", className="w-100 fw-bold",
                        style={"backgroundColor": "#0C5959", "fontFamily": "Arial"}
                    )
                ], width=2, className="d-flex align-items-end"), 
                dbc.Col([
                    html.Span("⚠️ Máx. 3 meses", className="text-muted small mb-1", style={"fontFamily": "Arial"})
                ], width=4, className="d-flex align-items-end")
            ], className="g-2")
        ], style={"padding": "15px"})
    ], className="mb-3 border-0 shadow-sm mx-3"), # mx-3 adiciona margem lateral ao card também

    # 3. FILTROS E EXPORTAÇÃO
    dbc.Collapse(
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Filtrar Parceiro", className="fw-bold text-success small mb-1", style={"fontFamily": "Arial"}),
                        dcc.Dropdown(id="dd-parceiro", placeholder="Selecione...", className="small-dropdown")
                    ], md=5),
                    dbc.Col([
                        dbc.Label("Filtrar Material", className="fw-bold text-success small mb-1", style={"fontFamily": "Arial"}),
                        dcc.Dropdown(id="dd-material", placeholder="Selecione...", className="small-dropdown")
                    ], md=5),
                    dbc.Col([
                        dbc.Label("Ações", className="text-white small d-block mb-1"), 
                        dbc.ButtonGroup([
                            dbc.Button([html.I(className="bi bi-file-earmark-excel me-1"), "Excel"], id="btn-excel", color="success", outline=True, size="sm", style={"fontFamily": "Arial"}),
                            dbc.Button([html.I(className="bi bi-file-earmark-pdf me-1"), "PDF Oficial"], id="btn-pdf", color="danger", outline=True, size="sm", style={"fontFamily": "Arial"})
                        ], className="d-flex w-100")
                    ], md=2, className="d-flex align-items-end")
                ])
            ])
        ], className="mb-2 border-0 shadow-sm mx-3"),
        id="collapse-filtros", is_open=False
    ),

    # 4. BARRA DE TOTAIS
    html.Div(id="barra-totais", className="mb-2 mx-3"), # mx-3 alinha com a tabela

    # 5. TABELA (Com Borda Arredondada e Espaçamento)
    dcc.Loading(
        id="loading", type="default", color="#0C5959",
        children=html.Div(
            id="area-tabela", 
            style={
                'height': 'calc(100vh - 380px)', 
                'backgroundColor': 'white', 
                'borderRadius': '20px', 
                'border': '1px solid #e0e0e0',
                'overflow': 'hidden',
                # AQUI ESTÁ O ESPAÇAMENTO DA BORDA DA TELA
                'margin': '0 15px 15px 15px' 
            }
        )
    ),
    
    dcc.Download(id="download-excel"),
    dcc.Download(id="download-pdf")

], fluid=True, className="vh-100 d-flex flex-column bg-light p-0")

# --- CALLBACKS ---

@app.callback(
    Output("store-dados-brutos", "data"),
    Output("collapse-filtros", "is_open"),
    Output("dd-parceiro", "options"),
    Output("dd-material", "options"),
    Output("loading", "children"),
    Input("btn-carregar", "n_clicks"),
    State("dt-inicio", "value"),
    State("dt-fim", "value"),
    prevent_initial_call=True
)
def carregar(n, start, end):
    if not start or not end: return no_update, False, [], [], no_update
    d1 = datetime.strptime(start, '%Y-%m-%d')
    d2 = datetime.strptime(end, '%Y-%m-%d')
    if (d2 - d1).days > 95: return [], False, [], [], dbc.Alert("Período > 3 meses.", color="danger")

    df = sap.buscar_dados_por_periodo(start, end)
    if df.empty: return [], False, [], [], dbc.Alert("Nenhum dado encontrado.", color="warning")

    df['Filtro_Parceiro'] = df['Cod. Parceiro'].astype(str) + " - " + df['Razão Social'].astype(str)
    df['Filtro_Material'] = df['Material'].astype(str) + " - " + df['NomeMaterial'].astype(str)
    
    opts_p = [{'label': i, 'value': i} for i in sorted(df['Filtro_Parceiro'].unique())]
    opts_m = [{'label': i, 'value': i} for i in sorted(df['Filtro_Material'].unique())]

    return df.to_dict('records'), True, opts_p, opts_m, no_update

@app.callback(
    Output("area-tabela", "children"),
    Output("barra-totais", "children"),
    Input("store-dados-brutos", "data"),
    Input("dd-parceiro", "value"),
    Input("dd-material", "value")
)
def renderizar(data, parc, mat):
    if not data: return html.Div(), None
    df = pd.DataFrame(data)
    
    if parc: df = df[df['Filtro_Parceiro'] == parc]
    if mat: df = df[df['Filtro_Material'] == mat]

    # --- BARRA DE TOTAIS ---
    def fmt_num(val): return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    style_box = {
        "backgroundColor": "#EF6100", 
        "color": "white", 
        "borderRadius": "5px", 
        "padding": "8px 18px", 
        "fontSize": "13px",
        "fontWeight": "bold",
        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
        "fontFamily": "Arial",
        "whiteSpace": "nowrap"
    }
    
    if df.empty:
        totais_comp = html.Div("Sem dados para totalizar", style={"color": "gray", "fontSize": "11px"})
    else:
        totais_comp = dbc.Row([
            dbc.Col(html.Div([html.Span("Peso Bruto: "), html.Span(fmt_num(df["Peso Bruto (Kg)"].sum()) + " kg")], style=style_box), width="auto"),
            dbc.Col(html.Div([html.Span("Tara: "), html.Span(fmt_num(df["Peso Tara (Kg)"].sum()) + " kg")], style=style_box), width="auto"),
            dbc.Col(html.Div([html.Span("Líquido: "), html.Span(fmt_num(df["Peso liquido (Kg)"].sum()) + " kg")], style=style_box), width="auto"),
            dbc.Col(html.Div([html.Span("Qtd Aplicada: "), html.Span(fmt_num(df["Qtd Aplicada (Kg)"].sum()) + " kg")], style=style_box), width="auto"),
            dbc.Col(html.Div([html.Span("Descontos: "), html.Span(fmt_num(df["Descontos (Kg)"].sum()) + " kg")], style=style_box), width="auto"),
        ], className="g-2 justify-content-start align-items-center")

    # --- TABELA ---
    cols = []
    formato = Format(precision=2, scheme=Scheme.fixed, group=Group.yes, group_delimiter='.', decimal_delimiter=',')
    for c in df.columns:
        if c in ["Filtro_Parceiro", "Filtro_Material"]: continue
        type_ = "numeric" if "(Kg)" in c or "%" in c else "text"
        fmt = formato if type_ == "numeric" else None
        cols.append({"name": c, "id": c, "type": type_, "format": fmt})

    tabela = dash_table.DataTable(
        id="tabela-principal",
        data=df.to_dict('records'),
        columns=cols,
        virtualization=True,
        page_action='none',
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        fixed_rows={'headers': True},
        style_table={'height': '100%', 'overflowY': 'auto', 'minWidth': '100%'},
        style_header={
            'backgroundColor': '#0C5959', 
            'color': 'white', 
            'fontWeight': 'bold', 
            'textAlign': 'center', 
            'border': '1px solid white',
            'fontFamily': 'Arial',
            'fontSize': '13px'
        },
        style_cell={
            'fontFamily': 'Tahoma',
            'fontSize': '11px', 
            'textAlign': 'left', 
            'padding': '5px', 
            'minWidth': '100px', 
            'maxWidth': '180px', 
            'overflow': 'hidden', 
            'textOverflow': 'ellipsis'
        },
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
    )

    return tabela, totais_comp

@app.callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    State("tabela-principal", "derived_virtual_data"),
    prevent_initial_call=True
)
def baixar_excel(n, rows):
    if not rows: return no_update
    df = pd.DataFrame(rows)
    df.drop(columns=["Filtro_Parceiro", "Filtro_Material"], errors='ignore', inplace=True)
    return dcc.send_data_frame(df.to_excel, "relatorio_sap.xlsx", index=False)

@app.callback(
    Output("download-pdf", "data"),
    Input("btn-pdf", "n_clicks"),
    State("store-dados-brutos", "data"),
    State("dd-parceiro", "value"),
    State("dd-material", "value"),
    State("dt-inicio", "value"),
    State("dt-fim", "value"),
    prevent_initial_call=True
)
def baixar_pdf(n, data, parc, mat, start, end):
    if not data or not parc or not mat: return no_update
    df = pd.DataFrame(data)
    df = df[(df['Filtro_Parceiro'] == parc) & (df['Filtro_Material'] == mat)]
    
    p_cod, p_nome = parc.split(" - ", 1)
    m_cod, m_nome = mat.split(" - ", 1)
    fmt = lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m/%Y')
    
    buffer = gerar_pdf_oficial(
        df, 
        {'codigo': p_cod, 'nome': p_nome},
        {'codigo': m_cod, 'nome': m_nome},
        f"{fmt(start)} a {fmt(end)}"
    )
    if buffer: return dcc.send_bytes(buffer.getvalue(), "relatorio_oficial.pdf")
    return no_update

if __name__ == "__main__":
    app.run(debug=False, port=8052, host='0.0.0.0')