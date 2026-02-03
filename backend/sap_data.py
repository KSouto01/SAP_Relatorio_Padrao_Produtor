# VERSÃO: 12.1 - Cache em Disco (Resolvido o problema de recarga por usuário)
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib3

# Desativa avisos de certificado (SSL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# Caminho do arquivo de cache (na raiz do projeto ou backend)
CACHE_FILE = "cache_fornecedores.pkl"

class SAPConnector:
    def __init__(self):
        self.auth = (os.getenv("SAP_USER"), os.getenv("SAP_PASS"))
        
        # URLs Base
        self.url_romaneio = os.getenv("API_ROMANEIO_URL")
        self.url_fatura = os.getenv("API_FATURA_URL")
        self.url_fornecedores = "https://faz.sap.fazendaoto.com.br/sap/opu/odata/sap/FAP_DISPLAY_SUPPLIER_LIST"

    def _fetch_full_odata(self, base_url, entity_set, params):
        """MOTOR ODATA: Baixa dados com paginação (Loop __next)"""
        all_records = []
        
        if base_url.endswith('/'):
            url = f"{base_url}{entity_set}"
        else:
            url = f"{base_url}/{entity_set}"
        
        session = requests.Session()
        session.auth = self.auth
        session.verify = False
        session.headers.update({"Prefer": "odata.maxpagesize=50000", "Accept": "application/json"})

        if "$top" not in params: params["$top"] = "999999"

        page_counter = 1
        print(f"   [SAP] Acessando: {url}")

        while url:
            try:
                if page_counter == 1:
                    r = session.get(url, params=params, timeout=120)
                else:
                    r = session.get(url, timeout=120)
                
                if r.status_code != 200:
                    print(f"   [ERRO] HTTP {r.status_code} na pág {page_counter}")
                    break

                data = r.json()
                d = data.get('d', {})
                results = d.get('results', [])
                
                if not results: break
                
                all_records.extend(results)
                # print(f"   -> Pág {page_counter}: +{len(results)} linhas") # Comentei para limpar o log
                
                url = d.get('__next') 
                if url: page_counter += 1
                else: break
                    
            except Exception as e:
                print(f"   [ERRO CRÍTICO] {e}")
                break
        
        session.close()
        
        df = pd.DataFrame(all_records)
        if '__metadata' in df.columns: df.drop(columns=['__metadata'], inplace=True)
        return df

    def buscar_fornecedores(self, tipo_taxa_filtro):
        """
        FONTE 3: Cache Baseado em Arquivo (Disco).
        Compartilhado entre todos os usuários e workers.
        """
        agora = datetime.now()
        usar_cache = False
        df_completo = pd.DataFrame()

        # 1. VERIFICA SE O ARQUIVO EXISTE E É RECENTE (< 59 MIN)
        if os.path.exists(CACHE_FILE):
            mod_timestamp = os.path.getmtime(CACHE_FILE)
            mod_time = datetime.fromtimestamp(mod_timestamp)
            
            if (agora - mod_time) < timedelta(minutes=59):
                print(f"[{agora.strftime('%H:%M:%S')}] LENDO CACHE DO DISCO (Arquivo de {mod_time.strftime('%H:%M')})")
                try:
                    df_completo = pd.read_pickle(CACHE_FILE)
                    usar_cache = True
                except Exception as e:
                    print(f"   [AVISO] Cache corrompido, baixando novamente. Erro: {e}")

        # 2. SE NÃO TEM CACHE VÁLIDO, BAIXA DO SAP
        if not usar_cache:
            print(f"[{agora.strftime('%H:%M:%S')}] CACHE EXPIRADO OU INEXISTENTE. BAIXANDO DO SAP...")
            
            f_odata = "(TaxTypeName eq 'Brazil: CNPJ Number' or TaxTypeName eq 'Brazil: CPF Number')"
            cols_odata = "Supplier,SupplierName,BPTaxNumber,TaxTypeName"
            params = {"$filter": f_odata, "$select": cols_odata, "$format": "json"}
            
            df_completo = self._fetch_full_odata(self.url_fornecedores, "C_Supplier", params)
            
            if not df_completo.empty:
                # Tratamento
                df_completo = df_completo.drop_duplicates(subset=['Supplier', 'BPTaxNumber'])
                df_completo = df_completo.sort_values(by='SupplierName')
                
                # SALVA NO DISCO
                try:
                    df_completo.to_pickle(CACHE_FILE)
                    print(f"   -> Arquivo de cache salvo com sucesso: {len(df_completo)} registros.")
                except Exception as e:
                    print(f"   [ERRO] Não foi possível salvar o cache em disco: {e}")
        
        # 3. FILTRA PARA O RETORNO (CPF ou CNPJ)
        if df_completo.empty: return pd.DataFrame()
        
        filtro_txt = "Brazil: CPF Number" if tipo_taxa_filtro == 'cpf' else "Brazil: CNPJ Number"
        return df_completo[df_completo['TaxTypeName'] == filtro_txt].copy()

    def buscar_dados_por_periodo(self, data_inicio_str, data_fim_str, parceiro_id=None):
        try:
            d_ini = datetime.strptime(data_inicio_str, '%Y-%m-%d').strftime('%Y%m%d')
            d_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').strftime('%Y%m%d')
            print(f"--- BUSCANDO MOVIMENTOS: {d_ini} a {d_fim} (ID: {parceiro_id}) ---")
        except: return pd.DataFrame()

        # Tratamento ID (Zeros à esquerda)
        pid_padded = None
        if parceiro_id:
            pid_padded = str(parceiro_id).strip().zfill(10)

        # --- FONTE 1: ROMANEIOS ---
        f_rom = (
            "(Instr_EDC eq '07' or Instr_EDC eq '03' or Instr_EDC eq '35') and "
            "(Tipo_Contrato eq 'AC3P' or Tipo_Contrato eq 'ZFIX' or Tipo_Contrato eq '') and "
            f"(data_edc ge '{d_ini}' and data_edc le '{d_fim}')"
        )
        if pid_padded: f_rom += f" and (Parceiro eq '{pid_padded}')"
        
        cols_rom = ["Parceiro", "Parceiro_T", "Instr_EDC", "contrato", "Num_Pesagem", "data_edc", "Material", "NomeMaterial", "NomeSafra", "NomeLocal_Evento", "Placa", "NFe", "TextoTransgenia_Descarga", "Peso_Bruto_Descarga", "Tara_Descarga", "Peso_Liquido_Descarga", "Qtd_Aplicada", "Peso_Total", "Umidade_Descarga", "Peso_umidade", "Impurezas_Descarga", "Peso_Impurezas", "Ardidos_Descarga", "Peso_Ardidos", "Avariados_Descarga", "Peso_Avariados", "Esverdeados_Descarga", "Peso_Esverdeados", "Quebrados_Descarga", "Peso_Quebrados", "Queimados_Descarga", "Peso_Queimados", "Doc_Aplicacao", "Tipo_Contrato"]
        params_rom = {"$filter": f_rom, "$select": ",".join(cols_rom), "$format": "json"}
        
        df_rom = self._fetch_full_odata(self.url_romaneio, "ZC_ACM_LISTA_ROMANEIO_Q001", params_rom)
        
        if df_rom.empty: 
            print("   [AVISO] Fonte 1 vazia.")
            return pd.DataFrame()

        # --- FONTE 2: FATURAS ---
        f_fat = f"(pstdat ge '{d_ini}' and pstdat le '{d_fim}') and (nftype eq 'YI')"
        if pid_padded: f_fat += f" and (Parceiro_LF eq '{pid_padded}')"
        
        cols_fat = ["Aplicacao", "nfenum", "pstdat", "nftype", "Parceiro_LF"]
        params_fat = {"$filter": f_fat, "$select": ",".join(cols_fat), "$format": "json"}
        
        df_fat = self._fetch_full_odata(self.url_fatura, "ZC_FI_ENTRADAFATURA_Q001", params_fat)

        # --- JOIN ---
        df_rom['key_join'] = df_rom['Doc_Aplicacao'].astype(str).str.strip().str.lstrip('0')
        if not df_fat.empty:
            df_fat['key_join'] = df_fat['Aplicacao'].astype(str).str.strip().str.lstrip('0')
            df_final = pd.merge(df_rom, df_fat, on='key_join', how='left', suffixes=('', '_fat'))
            df_final.drop(columns=['key_join'], inplace=True)
        else:
            df_final = df_rom
            for c in cols_fat: df_final[c] = None

        # --- TRATAMENTO ---
        if 'data_edc' in df_final.columns:
            df_final['data_edc'] = pd.to_datetime(df_final['data_edc'], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y')
        
        rename_map = {"Doc_Aplicacao": "ID.apl", "Parceiro": "Cod. Parceiro", "Parceiro_T": "Razão Social", "Instr_EDC": "Instr. EDC", "Num_Pesagem": "Romaneio", "NomeLocal_Evento": "Unidade", "NFe": "Nota Produtor", "NomeMaterial": "NomeMaterial", "TextoTransgenia_Descarga": "Transgenia", "Peso_Bruto_Descarga": "Peso Bruto (Kg)", "Tara_Descarga": "Peso Tara (Kg)", "Peso_Liquido_Descarga": "Peso liquido (Kg)", "Qtd_Aplicada": "Qtd Aplicada (Kg)", "Peso_Total": "Descontos (Kg)", "Umidade_Descarga": "% Umidade", "Peso_umidade": "Desconto Umidade (Kg)", "Impurezas_Descarga": "% Impurezas", "Peso_Impurezas": "Desconto Impureza (Kg)", "Ardidos_Descarga": "% Ardido", "Peso_Ardidos": "Desconto Ardidos (Kg)", "Avariados_Descarga": "% Avariados", "Peso_Avariados": "Desconto Avariados (Kg)", "Esverdeados_Descarga": "% Esverdeados", "Peso_Esverdeados": "Desconto Esverdeados (Kg)", "Quebrados_Descarga": "% Quebrados", "Peso_Quebrados": "Desconto Quebrados (Kg)", "Queimados_Descarga": "% Queimados", "Peso_Queimados": "Desconto Queimados (Kg)", "data_edc": "Data do edc", "nfenum": "Nota SAP"}
        df_final.rename(columns=rename_map, inplace=True)
        
        for c in ["docnum", "itmnum", "Aplicacao", "nftype", "pstdat", "Tipo_Contrato", "Parceiro_LF"]:
            if c in df_final.columns: df_final.drop(columns=[c], inplace=True)
            
        cols_num = [c for c in df_final.columns if "(Kg)" in c or "%" in c or c == "Romaneio"]
        for col in cols_num: df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
        
        ordem = ["ID.apl", "Cod. Parceiro", "Razão Social", "contrato", "Instr. EDC", "Romaneio", "Data do edc", "Material", "NomeMaterial", "NomeSafra", "Unidade", "Placa", "Nota Produtor", "Nota SAP", "Transgenia", "Peso Bruto (Kg)", "Peso Tara (Kg)", "Peso liquido (Kg)", "Qtd Aplicada (Kg)", "Descontos (Kg)", "% Umidade", "Desconto Umidade (Kg)", "% Impurezas", "Desconto Impureza (Kg)", "Desconto Ardidos (Kg)", "Desconto Avariados (Kg)", "Desconto Esverdeados (Kg)", "Desconto Quebrados (Kg)", "Desconto Queimados (Kg)"]
        cols_finais = [c for c in ordem if c in df_final.columns] + [c for c in df_final.columns if c not in ordem]
        return df_final[cols_finais]