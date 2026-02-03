# VERSÃO: 13.1 - Layout Resumido em Blocos (Estilo Detalhado)
from xhtml2pdf import pisa
from io import BytesIO
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def formatar_numero(valor, casas=2):
    """Formata número para padrão PT-BR"""
    try:
        if pd.isnull(valor) or valor == 0 or valor == "": return "0,00" if casas==2 else "0"
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def get_base_html(conteudo_paginas):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4 landscape;
                margin: 1cm;
            }}
            
            body {{ 
                font-family: Helvetica, Arial, sans-serif; 
                color: #000; 
                font-size: 9px;
            }}
            
            /* ESTRUTURA */
            table {{ width: 100%; border-collapse: collapse; }}
            
            /* CABEÇALHO */
            .header-table td {{ border: none; padding: 5px; vertical-align: middle; }}
            .title {{ font-size: 16px; font-weight: bold; text-align: center; color: #0C5959; text-transform: uppercase; }}
            .meta {{ font-size: 9px; text-align: right; color: #333; }}
            
            /* INFO BOX */
            .info-box {{ 
                width: 100%; border: 1px solid #ccc; background-color: #fff;
                padding: 5px; margin-bottom: 10px; font-weight: bold; color: #0C5959; font-size: 10px;
            }}
            
            /* ESTILOS DE LINHA (PROFISSIONAL) */
            /* Linha Principal (Cinza Claro) - Identificadores */
            .row-main td {{ 
                border-top: 1px solid #999; 
                font-weight: bold; 
                background-color: #f2f2f2; 
                padding-top: 4px;
                padding-bottom: 2px;
                color: #333;
            }}
            
            /* Linha Secundária (Branca) - Valores */
            .row-sec td {{ 
                border-bottom: 1px solid #ccc; 
                padding-top: 2px; 
                padding-bottom: 4px;
                background-color: #fff;
                color: #000;
            }}
            
            /* TOTAIS (Laranja) */
            .row-total td {{ 
                background-color: #EF6100; 
                color: white; 
                font-weight: bold; 
                font-size: 10px; 
                border: 1px solid #EF6100;
                padding: 6px;
            }}

            /* ALINHAMENTOS */
            .text-right {{ text-align: right; }}
            .text-center {{ text-align: center; }}
            .text-left {{ text-align: left; }}
            .page-break {{ page-break-after: always; }}
        </style>
    </head>
    <body>{conteudo_paginas}</body>
    </html>
    """

def gerar_pdf_resumido(df, parceiro_info, material_info, periodo_texto):
    """
    Layout Resumido NOVO:
    Usa 2 linhas por registro (igual ao detalhado) para não espremer as colunas.
    """
    try:
        # Menos registros por página pois agora cada um ocupa 2 linhas visuais
        ROWS_PER_PAGE = 10
        
        totais = {
            "Bruto": df["Peso Bruto (Kg)"].sum() if "Peso Bruto (Kg)" in df.columns else 0,
            "Tara": df["Peso Tara (Kg)"].sum() if "Peso Tara (Kg)" in df.columns else 0,
            "Liquido": df["Peso liquido (Kg)"].sum() if "Peso liquido (Kg)" in df.columns else 0
        }

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, 'assets', 'logo.png')
        img_tag = f'<img src="{logo_path}" height="35px">' if os.path.exists(logo_path) else ''

        pages_html = ""
        chunks = [df[i:i + ROWS_PER_PAGE] for i in range(0, len(df), ROWS_PER_PAGE)]

        for i, chunk in enumerate(chunks):
            rows_html = ""
            for _, row in chunk.iterrows():
                # Formatações
                unidade = str(row.get('Unidade', ''))
                avarias = f"Av: {formatar_numero(row.get('% Avariados',0),1)}% | Es: {formatar_numero(row.get('% Esverdeados',0),1)}% | Qu: {formatar_numero(row.get('% Quebrados',0),1)}%"

                # LINHA 1: Identificação (Cinza)
                # Colunas: Data, Romaneio, Contrato, Placa, NF Prod, NF Faz, Local
                r1 = f"""
                <tr class="row-main">
                    <td>Data: {row.get('Data do edc', '')}</td>
                    <td>Romaneio: {row.get('Romaneio', '')}</td>
                    <td>Contr: {row.get('contrato', '')}</td>
                    <td>Placa: {row.get('Placa', '')}</td>
                    <td>NF Prod: {row.get('Nota Produtor', '')}</td>
                    <td>NF Faz: {row.get('Nota SAP', '')}</td>
                    <td colspan="3" class="text-right">Local: {unidade}</td>
                </tr>"""
                
                # LINHA 2: Valores (Branco)
                # Colunas: Bruto, Tara, Líquido, Umidade, Impureza, Avarias
                r2 = f"""
                <tr class="row-sec">
                    <td>Bruto: {formatar_numero(row.get('Peso Bruto (Kg)'))}</td>
                    <td>Tara: {formatar_numero(row.get('Peso Tara (Kg)'))}</td>
                    <td style="font-size:10px;">Líquido: {formatar_numero(row.get('Peso liquido (Kg)'))}</td>
                    <td>Umid: {formatar_numero(row.get('% Umidade'))}%</td>
                    <td>Imp: {formatar_numero(row.get('% Impurezas'))}%</td>
                    <td colspan="4" class="text-right" style="font-style:italic;">{avarias}</td>
                </tr>"""
                
                rows_html += r1 + r2
            
            # Totais na última página
            row_total = ""
            if i == len(chunks) - 1:
                row_total = f"""
                <tr class="row-total">
                    <td>TOTAIS GERAIS:</td>
                    <td>Bruto: {formatar_numero(totais['Bruto'])}</td>
                    <td>Tara: {formatar_numero(totais['Tara'])}</td>
                    <td colspan="6" class="text-left">Líquido: {formatar_numero(totais['Liquido'])}</td>
                </tr>"""
            
            break_page = '<div class="page-break"></div>' if i < len(chunks) - 1 else ''
            
            pages_html += f"""
            <div>
                <table class="header-table">
                    <tr>
                        <td width="20%">{img_tag}</td>
                        <td width="60%" class="title">Relatório Resumido Padrão Produtor</td>
                        <td width="20%" class="meta">{periodo_texto}<br>Pág: {i+1}/{len(chunks)}</td>
                    </tr>
                </table>
                <div class="info-box">PARCEIRO: {parceiro_info}<br>MATERIAL: {material_info}</div>
                <table>{rows_html}{row_total}</table>
            </div>
            {break_page}
            """
        
        buffer = BytesIO()
        pisa.CreatePDF(get_base_html(pages_html), dest=buffer)
        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"ERRO RESUMIDO: {e}")
        buffer = BytesIO()
        pisa.CreatePDF(f"<h1>Erro ao gerar PDF</h1><p>{str(e)}</p>", dest=buffer)
        buffer.seek(0)
        return buffer

def gerar_pdf_detalhado(df, parceiro_info, material_info, periodo_texto):
    """Layout Detalhado (Mantido igual pois estava aprovado)"""
    try:
        ROWS_PER_PAGE = 7
        cols_totais = ["Peso Bruto (Kg)", "Peso Tara (Kg)", "Peso liquido (Kg)", "Qtd Aplicada (Kg)", "Descontos (Kg)"]
        totais_gerais = {}
        for col in cols_totais:
            totais_gerais[col] = df[col].sum() if col in df.columns else 0

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, 'assets', 'logo.png')
        img_tag = f'<img src="{logo_path}" height="35px">' if os.path.exists(logo_path) else ''
        
        pages_html = ""
        chunks = [df[i:i + ROWS_PER_PAGE] for i in range(0, len(df), ROWS_PER_PAGE)]
        
        for i, chunk in enumerate(chunks):
            rows_html = ""
            for _, row in chunk.iterrows():
                r1 = f"""<tr class="row-main"><td>ID: {row.get('ID.apl', '')}</td><td>Contr: {row.get('contrato', '')}</td><td>Instr: {row.get('Instr. EDC', '')}</td><td>Romaneio: {row.get('Romaneio', '')}</td><td>Data: {row.get('Data do edc', '')}</td><td>Placa: {row.get('Placa', '')}</td><td>NF Prod: {row.get('Nota Produtor', '')}</td><td>NF Faz: {row.get('Nota SAP', '')}</td><td colspan="2">Local: {str(row.get('Unidade', ''))[:30]}</td></tr>"""
                r2 = f"""<tr class="row-sec"><td>Transg: {row.get('Transgenia', '')}</td><td>Bruto: {formatar_numero(row.get('Peso Bruto (Kg)'))}</td><td>Tara: {formatar_numero(row.get('Peso Tara (Kg)'))}</td><td>Líquido: {formatar_numero(row.get('Peso liquido (Kg)'))}</td><td>Qtd Apl: {formatar_numero(row.get('Qtd Aplicada (Kg)'))}</td><td colspan="5">Desc: {formatar_numero(row.get('Descontos (Kg)'))}</td></tr>"""
                r3 = f"""<tr class="row-sec" style="font-style:italic; color:#555; border-bottom:1px solid #ccc;"><td>Umid: {formatar_numero(row.get('% Umidade'))}% / {formatar_numero(row.get('Desconto Umidade (Kg)'))}</td><td>Imp: {formatar_numero(row.get('% Impurezas'))}% / {formatar_numero(row.get('Desconto Impureza (Kg)'))}</td><td>Ard: {formatar_numero(row.get('% Ardido'))}% / {formatar_numero(row.get('Desconto Ardidos (Kg)'))}</td><td>Ava: {formatar_numero(row.get('% Avariados'))}% / {formatar_numero(row.get('Desconto Avariados (Kg)'))}</td><td>Esv: {formatar_numero(row.get('% Esverdeados'))}% / {formatar_numero(row.get('Desconto Esverdeados (Kg)'))}</td><td>Que: {formatar_numero(row.get('% Quebrados'))}% / {formatar_numero(row.get('Desconto Quebrados (Kg)'))}</td><td colspan="4">Quei: {formatar_numero(row.get('% Queimados'))}% / {formatar_numero(row.get('Desconto Queimados (Kg)'))}</td></tr>"""
                rows_html += r1 + r2 + r3

            row_total = ""
            if i == len(chunks) - 1:
                row_total = f"""<tr class="row-total"><td>TOTAIS:</td><td>Bruto: {formatar_numero(totais_gerais.get('Peso Bruto (Kg)', 0))}</td><td>Tara: {formatar_numero(totais_gerais.get('Peso Tara (Kg)', 0))}</td><td>Líquido: {formatar_numero(totais_gerais.get('Peso liquido (Kg)', 0))}</td><td>Qtd Apl: {formatar_numero(totais_gerais.get('Qtd Aplicada (Kg)', 0))}</td><td colspan="5">Desc: {formatar_numero(totais_gerais.get('Descontos (Kg)', 0))}</td></tr>"""

            break_page = '<div class="page-break"></div>' if i < len(chunks) - 1 else ''

            pages_html += f"""
            <div>
                <table class="header-table"><tr><td width="20%">{img_tag}</td><td width="60%" class="title">Relatório Detalhado Padrão Produtor</td><td width="20%" class="meta">{periodo_texto}<br>Pág: {i+1}/{len(chunks)}</td></tr></table>
                <div class="info-box">PARCEIRO: {parceiro_info}<br>MATERIAL: {material_info}</div>
                <table>{rows_html}{row_total}</table>
            </div>
            {break_page}
            """

        buffer = BytesIO()
        pisa.CreatePDF(get_base_html(pages_html), dest=buffer)
        buffer.seek(0)
        return buffer
    
    except Exception as e:
        logger.error(f"ERRO DETALHADO: {e}")
        buffer = BytesIO()
        pisa.CreatePDF(f"<h1>Erro ao gerar PDF</h1><p>{str(e)}</p>", dest=buffer)
        buffer.seek(0)
        return buffer