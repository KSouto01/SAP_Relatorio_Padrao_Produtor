# VERSÃO: 12.8 - Renomeado para Peso LDC (35) e Atualização de Saldo
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "cache_fornecedores.pkl")

class SAPConnector:
    def __init__(self):
        self.auth = (os.getenv("SAP_USER"), os.getenv("SAP_PASS"))
        self.url_romaneio = os.getenv("API_ROMANEIO_URL")
        self.url_fatura = os.getenv("API_FATURA_URL") 
        self.url_fornecedores = "https://faz.sap.fazendaoto.com.br/sap/opu/odata/sap/FAP_DISPLAY_SUPPLIER_LIST"

    def _fetch_full_odata(self, base_url, entity_set, params):
        all_records = []
        if base_url.endswith('/'): url = f"{base_url}{entity_set}"
        else: url = f"{base_url}/{entity_set}"
        
        session = requests.Session()
        session.auth = self.auth
        session.verify = False
        session.headers.update({"Prefer": "odata.maxpagesize=50000", "Accept": "application/json"})

        if "$top" not in params: params["$top"] = "999999"

        page_counter = 1
        logger.info(f"[SAP] Iniciando Download: {url}")

        while url:
            try:
                if page_counter == 1:
                    r = session.get(url, params=params, timeout=120)
                else:
                    r = session.get(url, timeout=120)
                
                if r.status_code != 200:
                    logger.error(f"[SAP ERRO] HTTP {r.status_code}")
                    break

                data = r.json()
                d = data.get('d', {})
                results = d.get('results', [])
                
                if not results: break
                
                all_records.extend(results)
                url = d.get('__next') 
                if url: page_counter += 1
                else: break
                    
            except Exception as e:
                logger.error(f"[ERRO CRÍTICO CONEXÃO] {e}")
                break
        
        session.close()
        df = pd.DataFrame(all_records)
        if '__metadata' in df.columns: df.drop(columns=['__metadata'], inplace=True)
        return df

    def buscar_fornecedores(self, tipo_taxa_filtro):
        agora = datetime.now()
        usar_cache = False
        df_completo = pd.DataFrame()

        if os.path.exists(CACHE_FILE):
            mod_timestamp = os.path.getmtime(CACHE_FILE)
            mod_time = datetime.fromtimestamp(mod_timestamp)
            if (agora - mod_time) < timedelta(minutes=59):
                try:
                    df_completo = pd.read_pickle(CACHE_FILE)
                    if df_completo.empty: usar_cache = False
                    else: usar_cache = True
                except: usar_cache = False

        if not usar_cache:
            f_odata = "(TaxTypeName eq 'Brazil: CNPJ Number' or TaxTypeName eq 'Brazil: CPF Number')"
            cols_odata = "Supplier,SupplierName,BPTaxNumber,TaxTypeName"
            params = {"$filter": f_odata, "$select": cols_odata, "$format": "json"}
            df_completo = self._fetch_full_odata(self.url_fornecedores, "C_Supplier", params)
            
            if not df_completo.empty:
                df_completo = df_completo.drop_duplicates(subset=['Supplier', 'BPTaxNumber'])
                df_completo = df_completo.sort_values(by='SupplierName')
                try: df_completo.to_pickle(CACHE_FILE)
                except: pass
        
        if df_completo.empty: return pd.DataFrame()
        filtro_txt = "Brazil: CPF Number" if tipo_taxa_filtro == 'cpf' else "Brazil: CNPJ Number"
        return df_completo[df_completo['TaxTypeName'] == filtro_txt].copy()

    def buscar_dados_por_periodo(self, data_inicio_str, data_fim_str, parceiro_id=None):
        try:
            d_ini = datetime.strptime(data_inicio_str, '%Y-%m-%d').strftime('%Y%m%d')
            d_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').strftime('%Y%m%d')
        except: return pd.DataFrame()

        pid_padded = None
        if parceiro_id: pid_padded = str(parceiro_id).strip().zfill(10)

        f_rom =  (
            "(Instr_EDC eq '07' or Instr_EDC eq '03' or Instr_EDC eq '35') and "
            "(Tipo_Contrato eq 'AC3P' or Tipo_Contrato eq 'ZFIX' or Tipo_Contrato eq '') and "
            f"(data_edc ge '{d_ini}' and data_edc le '{d_fim}') and (stat eq 'I7U07') and (ID_Safra ne '200') and (InscricaoEstadual ne '')"
        )
        if pid_padded: f_rom += f" and (Parceiro eq '{pid_padded}')"
        
        cols_rom = [
            "Parceiro", "Parceiro_T", "Instr_EDC", "contrato", "Num_Pesagem", "data_edc", 
            "Material", "NomeMaterial", "NomeSafra", "NomeLocal_Evento", "Placa", 
            "TextoTransgenia_Descarga", "Peso_Bruto_Descarga", "Tara_Descarga", 
            "Peso_Liquido_Descarga", "Peso_Liquido_Carga", "Qtd_Aplicada", "Qtd_Devolvida", "Peso_Total", "Umidade_Descarga", 
            "Peso_umidade", "Impurezas_Descarga", "Peso_Impurezas", "Ardidos_Descarga", 
            "Peso_Ardidos", "Avariados_Descarga", "Peso_Avariados", "Esverdeados_Descarga", 
            "Peso_Esverdeados", "Quebrados_Descarga", "Peso_Quebrados", "Queimados_Descarga", 
            "Peso_Queimados", "Doc_Aplicacao", "Tipo_Contrato", 
            "ChaveNFeContraNota", "ChaveNFeReferenciada"
        ]
        
        params_rom = {"$filter": f_rom, "$select": ",".join(cols_rom), "$format": "json"}
        df_final = self._fetch_full_odata(self.url_romaneio, "ZC_ACM_LISTA_ROMANEIO_Q001", params_rom)
        
        if df_final.empty: return pd.DataFrame()

        def extrair_nota(chave):
            if pd.isna(chave): return ''
            chave = str(chave).strip()
            if len(chave) == 44:
                nota = chave[25:34].lstrip('0')
                return nota if nota else '0'
            return ''
            
        df_final['Nota Produtor'] = df_final['ChaveNFeReferenciada'].apply(extrair_nota)
        df_final['Nota Fazendao'] = df_final['ChaveNFeContraNota'].apply(extrair_nota)

        df_final['Qtd_Aplicada'] = pd.to_numeric(df_final.get('Qtd_Aplicada', 0), errors='coerce').fillna(0)
        df_final['Qtd_Devolvida'] = pd.to_numeric(df_final.get('Qtd_Devolvida', 0), errors='coerce').fillna(0)
        df_final['Peso_Liquido_Carga'] = pd.to_numeric(df_final.get('Peso_Liquido_Carga', 0), errors='coerce').fillna(0)

        def rule_peso_carga(row):
            if str(row.get('Instr_EDC')).strip() == '35':
                return -abs(float(row.get('Peso_Liquido_Carga', 0))) 
            return 0.0

        df_final['Peso_Liquido_Carga'] = df_final.apply(rule_peso_carga, axis=1)

        if 'data_edc' in df_final.columns:
            df_final['data_edc'] = pd.to_datetime(df_final['data_edc'], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y')
        
        # MUDANÇA: Renomeado para Peso LDC (35)
        rename_map = {"Doc_Aplicacao": "ID.apl", "Parceiro": "Cod. Parceiro", "Parceiro_T": "Razão Social", "Instr_EDC": "Instr. EDC", "Num_Pesagem": "Romaneio", "NomeLocal_Evento": "Unidade", "NomeMaterial": "NomeMaterial", "TextoTransgenia_Descarga": "Transgenia", "Peso_Bruto_Descarga": "Peso Bruto (Kg)", "Tara_Descarga": "Peso Tara (Kg)", "Peso_Liquido_Descarga": "Peso liquido (Kg)", "Qtd_Aplicada": "Qtd Aplicada (Kg)", "Qtd_Devolvida": "Qtd Devolvida (Kg)", "Peso_Liquido_Carga": "Peso LDC (35) (Kg)", "Peso_Total": "Descontos (Kg)", "Umidade_Descarga": "% Umidade", "Peso_umidade": "Desconto Umidade (Kg)", "Impurezas_Descarga": "% Impurezas", "Peso_Impurezas": "Desconto Impureza (Kg)", "Ardidos_Descarga": "% Ardido", "Peso_Ardidos": "Desconto Ardidos (Kg)", "Avariados_Descarga": "% Avariados", "Peso_Avariados": "Desconto Avariados (Kg)", "Esverdeados_Descarga": "% Esverdeados", "Peso_Esverdeados": "Desconto Esverdeados (Kg)", "Quebrados_Descarga": "% Quebrados", "Peso_Quebrados": "Desconto Quebrados (Kg)", "Queimados_Descarga": "% Queimados", "Peso_Queimados": "Desconto Queimados (Kg)", "data_edc": "Data do edc"}
        df_final.rename(columns=rename_map, inplace=True)
        
        for c in ["Tipo_Contrato", "ChaveNFeContraNota", "ChaveNFeReferenciada"]:
            if c in df_final.columns: df_final.drop(columns=[c], inplace=True)
            
        cols_num = [c for c in df_final.columns if "(Kg)" in c or "%" in c or c == "Romaneio"]
        for col in cols_num: df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
        
        # MUDANÇA: Cálculo referenciando o novo nome "Peso LDC (35) (Kg)"
        df_final['Saldo (Kg)'] = df_final['Qtd Aplicada (Kg)'] - df_final['Qtd Devolvida (Kg)'] - df_final['Peso LDC (35) (Kg)'].abs()

        return df_final