# VERSÃO: 10.2
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class SAPConnector:
    def __init__(self):
        self.auth = (os.getenv("SAP_USER"), os.getenv("SAP_PASS"))
        self.url_romaneio = os.getenv("API_ROMANEIO_URL")
        self.url_fatura = os.getenv("API_FATURA_URL")

    def buscar_dados_por_periodo(self, data_inicio_str, data_fim_str):
        try:
            d_ini = datetime.strptime(data_inicio_str, '%Y-%m-%d').strftime('%Y%m%d')
            d_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').strftime('%Y%m%d')
            print(f"--- CARREGANDO: {d_ini} a {d_fim} ---")
        except Exception as e:
            print(f"Erro de data: {e}")
            return pd.DataFrame()

        # 1. ROMANEIOS
        cols_rom = [
            "Parceiro", "Parceiro_T", "Instr_EDC", "contrato", "Num_Pesagem", "data_edc", 
            "Material", "NomeMaterial", "NomeSafra", "NomeLocal_Evento", "Placa", "NFe", 
            "TextoTransgenia_Descarga", "Peso_Bruto_Descarga", "Tara_Descarga", 
            "Peso_Liquido_Descarga", "Qtd_Aplicada", "Peso_Total", "Umidade_Descarga", 
            "Peso_umidade", "Impurezas_Descarga", "Peso_Impurezas", "Ardidos_Descarga", 
            "Peso_Ardidos", "Avariados_Descarga", "Peso_Avariados", "Esverdeados_Descarga", 
            "Peso_Esverdeados", "Quebrados_Descarga", "Peso_Quebrados", "Queimados_Descarga", 
            "Peso_Queimados", "Doc_Aplicacao", "Tipo_Contrato"
        ]
        
        f_rom = (
            "(Instr_EDC eq '07' or Instr_EDC eq '03' or Instr_EDC eq '35') and "
            "(Tipo_Contrato eq 'AC3P' or Tipo_Contrato eq 'ZFIX' or Tipo_Contrato eq '') and "
            f"(data_edc ge '{d_ini}' and data_edc le '{d_fim}')"
        )
        
        df_rom = self._fetch_odata(self.url_romaneio, "ZC_ACM_LISTA_ROMANEIO_Q001", f_rom, cols_rom)
        
        if df_rom.empty: return pd.DataFrame()

        # 2. FATURAS
        cols_fat = ["Aplicacao", "nfenum", "pstdat", "nftype"] 
        f_fat = f"(pstdat ge '{d_ini}' and pstdat le '{d_fim}') and (nftype eq 'YI')"
        df_fat = self._fetch_odata(self.url_fatura, "ZC_FI_ENTRADAFATURA_Q001", f_fat, cols_fat)

        # 3. JOIN
        df_rom['key_join'] = df_rom['Doc_Aplicacao'].astype(str).str.strip().str.lstrip('0')
        if not df_fat.empty:
            df_fat['key_join'] = df_fat['Aplicacao'].astype(str).str.strip().str.lstrip('0')
            df_final = pd.merge(df_rom, df_fat, on='key_join', how='left', suffixes=('', '_fat'))
            df_final.drop(columns=['key_join'], inplace=True)
        else:
            df_final = df_rom
            for c in cols_fat: df_final[c] = None

        # --- TRATAMENTO v10.2 ---
        if 'data_edc' in df_final.columns:
            df_final['data_edc'] = pd.to_datetime(df_final['data_edc'], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y')

        # Renomeação Oficial
        rename_map = {
            "Doc_Aplicacao": "ID.apl",
            "Parceiro": "Cod. Parceiro",
            "Parceiro_T": "Razão Social",
            "Instr_EDC": "Instr. EDC",
            "Num_Pesagem": "Romaneio",
            "NomeLocal_Evento": "Unidade",
            "NFe": "Nota Produtor",
            "NomeMaterial": "NomeMaterial", # CAMPO CORRETO MAPEADO
            "TextoTransgenia_Descarga": "Transgenia",
            "Peso_Bruto_Descarga": "Peso Bruto (Kg)",
            "Tara_Descarga": "Peso Tara (Kg)",
            "Peso_Liquido_Descarga": "Peso liquido (Kg)",
            "Qtd_Aplicada": "Qtd Aplicada (Kg)",
            "Peso_Total": "Descontos (Kg)",
            "Umidade_Descarga": "% Umidade",
            "Peso_umidade": "Desconto Umidade (Kg)",
            "Impurezas_Descarga": "% Impurezas",
            "Peso_Impurezas": "Desconto Impureza (Kg)",
            "Ardidos_Descarga": "% Ardido",
            "Peso_Ardidos": "Desconto Ardidos (Kg)",
            "Avariados_Descarga": "% Avariados",
            "Peso_Avariados": "Desconto Avariados (Kg)",
            "Esverdeados_Descarga": "% Esverdeados",
            "Peso_Esverdeados": "Desconto Esverdeados (Kg)",
            "Quebrados_Descarga": "% Quebrados",
            "Peso_Quebrados": "Desconto Quebrados (Kg)",
            "Queimados_Descarga": "% Queimados",
            "Peso_Queimados": "Desconto Queimados (Kg)",
            "data_edc": "Data do edc",
            "nfenum": "Nota SAP"
        }
        df_final.rename(columns=rename_map, inplace=True)

        # Limpeza de colunas
        cols_remove = ["docnum", "itmnum", "Aplicacao", "nftype", "pstdat", "Tipo_Contrato"]
        df_final.drop(columns=[c for c in cols_remove if c in df_final.columns], errors='ignore', inplace=True)

        # Conversão Numérica
        cols_numericas = [c for c in df_final.columns if "(Kg)" in c or "%" in c or c == "Romaneio"]
        for col in cols_numericas:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)

        # Ordenação
        ordem = [
            "ID.apl", "Cod. Parceiro", "Razão Social", "contrato", "Instr. EDC", "Romaneio", "Data do edc",
            "Material", "NomeMaterial", "NomeSafra", "Unidade", "Placa",
            "Nota Produtor", "Nota SAP", "Transgenia", 
            "Peso Bruto (Kg)", "Peso Tara (Kg)", "Peso liquido (Kg)",
            "Qtd Aplicada (Kg)", "Descontos (Kg)", 
            "% Umidade", "Desconto Umidade (Kg)", 
            "% Impurezas", "Desconto Impureza (Kg)",
            "% Ardido", "Desconto Ardidos (Kg)",
            "% Avariados", "Desconto Avariados (Kg)",
            "% Esverdeados", "Desconto Esverdeados (Kg)",
            "% Quebrados", "Desconto Quebrados (Kg)",
            "% Queimados", "Desconto Queimados (Kg)"
        ]
        
        # Intersecção para evitar erro de coluna inexistente
        final_cols = [c for c in ordem if c in df_final.columns]
        restante = [c for c in df_final.columns if c not in final_cols]
        return df_final[final_cols + restante]

    def _fetch_odata(self, base_url, entity_set, filter_str, select_cols):
        params = {"$filter": filter_str, "$select": ",".join(select_cols), "$format": "json", "$top": 20000}
        try:
            r = requests.get(f"{base_url}/{entity_set}", params=params, auth=self.auth, timeout=120)
            if r.status_code != 200: return pd.DataFrame()
            d = r.json().get('d', {}).get('results', [])
            df = pd.DataFrame(d)
            if '__metadata' in df.columns: df.drop(columns=['__metadata'], inplace=True)
            return df
        except: return pd.DataFrame()