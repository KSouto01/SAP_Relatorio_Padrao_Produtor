# VERSÃO: 10.9 (Total Geral na Última Página)
from xhtml2pdf import pisa
from io import BytesIO
import pandas as pd
from datetime import datetime
import os
import numpy as np

def formatar_numero(valor):
    """Formata float para string BR (1.000,00) ou retorna vazio se zero/nulo"""
    try:
        if pd.isnull(valor) or valor == 0: return "0,00"
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def gerar_pdf_oficial(df_filtrado, parceiro_info, material_info, periodo_texto):
    """
    Gera PDF com Paginação Manual e TOTAL GERAL apenas no final.
    """
    
    # 1. Configurações
    ROWS_PER_PAGE = 5  
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, 'assets', 'logo.png')
    img_tag = f'<img src="{logo_path}" height="50px">' if os.path.exists(logo_path) else ''

    # 2. Tratamento de Dados
    cols_drop = ["Cod. Parceiro", "Razão Social", "Material", "NomeMaterial"]
    df = df_filtrado.drop(columns=[c for c in cols_drop if c in df_filtrado.columns], errors='ignore')

    # Colunas para totalizar
    cols_totais = [
        "Peso Bruto (Kg)", 
        "Peso Tara (Kg)", 
        "Peso liquido (Kg)", 
        "Qtd Aplicada (Kg)", 
        "Descontos (Kg)"
    ]

    # Cálculo dos Totais Gerais (Do relatório inteiro)
    totais_gerais = {col: df[col].sum() for col in cols_totais if col in df.columns}

    # 3. Geração das Páginas
    pages_html = ""
    total_records = len(df)
    
    # Divide em páginas
    chunks = [df[i:i + ROWS_PER_PAGE] for i in range(0, total_records, ROWS_PER_PAGE)]
    
    for i, chunk in enumerate(chunks):
        rows_html = ""
        
        for _, row in chunk.iterrows():
            # Linha 1
            r1 = f"""
            <tr class="row-main">
                <td><b>ID:</b> {row.get('ID.apl', '')}</td>
                <td><b>Contrato:</b> {row.get('contrato', '')}</td>
                <td><b>Instr:</b> {row.get('Instr. EDC', '')}</td>
                <td><b>Romaneio:</b> {row.get('Romaneio', '')}</td>
                <td><b>Data:</b> {row.get('Data do edc', '')}</td>
                <td><b>Placa:</b> {row.get('Placa', '')}</td>
                <td><b>NF Prod:</b> {row.get('Nota Produtor', '')}</td>
                <td><b>NF SAP:</b> {row.get('Nota SAP', '')}</td>
                <td colspan="2"><b>Unidade:</b> {row.get('Unidade', '')}</td>
            </tr>
            """
            # Linha 2
            r2 = f"""
            <tr class="row-sec">
                <td><b>Transg:</b> {row.get('Transgenia', '')}</td>
                <td><b>P. Bruto:</b> {formatar_numero(row.get('Peso Bruto (Kg)'))}</td>
                <td><b>Tara:</b> {formatar_numero(row.get('Peso Tara (Kg)'))}</td>
                <td><b>Líquido:</b> {formatar_numero(row.get('Peso liquido (Kg)'))}</td>
                <td><b>Qtd Apl:</b> {formatar_numero(row.get('Qtd Aplicada (Kg)'))}</td>
                <td colspan="5"><b>Total Desc:</b> {formatar_numero(row.get('Descontos (Kg)'))}</td>
            </tr>
            """
            # Linha 3
            r3 = f"""
            <tr class="row-det">
                <td>Umid: {formatar_numero(row.get('% Umidade'))}% / {formatar_numero(row.get('Desconto Umidade (Kg)'))}</td>
                <td>Imp: {formatar_numero(row.get('% Impurezas'))}% / {formatar_numero(row.get('Desconto Impureza (Kg)'))}</td>
                <td>Ard: {formatar_numero(row.get('% Ardido'))}% / {formatar_numero(row.get('Desconto Ardidos (Kg)'))}</td>
                <td>Ava: {formatar_numero(row.get('% Avariados'))}% / {formatar_numero(row.get('Desconto Avariados (Kg)'))}</td>
                <td>Esv: {formatar_numero(row.get('% Esverdeados'))}% / {formatar_numero(row.get('Desconto Esverdeados (Kg)'))}</td>
                <td>Que: {formatar_numero(row.get('% Quebrados'))}% / {formatar_numero(row.get('Desconto Quebrados (Kg)'))}</td>
                <td colspan="4">Quei: {formatar_numero(row.get('% Queimados'))}% / {formatar_numero(row.get('Desconto Queimados (Kg)'))}</td>
            </tr>
            """
            rows_html += r1 + r2 + r3 + '<tr><td colspan="10" class="separator"></td></tr>'

        # LÓGICA DO TOTAL GERAL (Apenas na última página)
        if i == len(chunks) - 1:
            row_total = f"""
            <tr class="row-total">
                <td><b>TOTAL GERAL:</b></td>
                <td><b>Bruto:</b> {formatar_numero(totais_gerais.get('Peso Bruto (Kg)', 0))}</td>
                <td><b>Tara:</b> {formatar_numero(totais_gerais.get('Peso Tara (Kg)', 0))}</td>
                <td><b>Líquido:</b> {formatar_numero(totais_gerais.get('Peso liquido (Kg)', 0))}</td>
                <td><b>Qtd Apl:</b> {formatar_numero(totais_gerais.get('Qtd Aplicada (Kg)', 0))}</td>
                <td colspan="5"><b>Desc:</b> {formatar_numero(totais_gerais.get('Descontos (Kg)', 0))}</td>
            </tr>
            """
            rows_html += row_total

        # Quebra de página
        page_break = '<div style="page-break-after: always;"></div>' if i < len(chunks) - 1 else ''

        pages_html += f"""
        <div class="page-container">
            <table class="header-table">
                <tr>
                    <td width="25%">{img_tag}</td>
                    <td width="50%" class="title">Relatório Padrão Produtor</td>
                    <td width="25%" class="meta">
                        Período: {periodo_texto}<br>
                        Emissão: {datetime.now().strftime('%d/%m/%Y')}<br>
                        Página: {i+1}/{len(chunks)}
                    </td>
                </tr>
            </table>

            <div class="info-box">
                <b>PARCEIRO:</b> {parceiro_info['codigo']} - {parceiro_info['nome']} <br>
                <b>PRODUTO:</b> {material_info['codigo']} - {material_info['nome']}
            </div>

            <table class="data-table">
                {rows_html}
            </table>
        </div>
        {page_break}
        """

    # 4. CSS
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ 
                size: A4 landscape; 
                margin: 1cm; 
                margin-bottom: 0.5cm; 
            }}
            body {{ font-family: 'Tahoma', sans-serif; color: #333; font-size: 10px; }}
            
            .title, .meta, .header-table, .info-box {{ font-family: 'Arial', sans-serif; }}
            
            .header-table {{ width: 100%; border-bottom: 3px solid #0C5959; margin-bottom: 15px; border-collapse: collapse; }}
            .header-table td {{ padding-bottom: 10px; vertical-align: middle; }}
            
            .title {{ font-size: 18px; font-weight: bold; text-align: center; text-transform: uppercase; }}
            .meta {{ font-size: 10px; text-align: right; }}
            
            .info-box {{ width: 100%; background-color: #eee; padding: 10px; margin-bottom: 10px; font-size: 11px; }}
            
            .data-table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
            
            .row-main td {{ padding-top: 6px; font-size: 10px; color: #000; }}
            .row-sec td {{ padding-top: 1px; color: #333; }}
            .row-det td {{ padding-top: 1px; padding-bottom: 6px; font-size: 8px; color: #555; }}
            .separator {{ border-bottom: 1px solid #ccc; }}
            
            /* Estilo Total Geral (Destacado) */
            .row-total td {{ 
                background-color: #EF6100; 
                color: white; 
                font-weight: bold; 
                padding: 4px 5px; 
                border-top: 2px solid #333;
                font-size: 10px;
                vertical-align: middle;
            }}
            
            .page-container {{ page-break-inside: avoid; }}
        </style>
    </head>
    <body>
        {pages_html}
    </body>
    </html>
    """

    buffer = BytesIO()
    try:
        pisa_status = pisa.CreatePDF(html_content, dest=buffer)
        if pisa_status.err: return None
    except: return None
    
    buffer.seek(0)
    return buffer