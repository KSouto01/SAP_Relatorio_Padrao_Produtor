import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

# Configurações
USER = os.getenv("SAP_USER")
PASS = os.getenv("SAP_PASS")
URL_BASE = os.getenv("API_ROMANEIO_URL") # URL do Romaneio

def diagnosticar():
    print(f"--- INICIANDO DIAGNÓSTICO J.A.R.V.I.S ---")
    print(f"Alvo: {URL_BASE}")
    
    # 1. Tenta pegar o $metadata
    url_meta = f"{URL_BASE}/$metadata"
    print(f"\n1. Consultando Metadados: {url_meta}")
    
    try:
        r = requests.get(url_meta, auth=(USER, PASS), timeout=30)
        r.raise_for_status()
        print("   [OK] Metadados recebidos.")
        
        # Parse XML para achar nomes reais
        root = ET.fromstring(r.content)
        
        # Namespaces comuns do OData
        ns = {
            'edm': 'http://schemas.microsoft.com/ado/2008/09/edm',
            'atom': 'http://www.w3.org/2005/Atom',
            'app': 'http://www.w3.org/2007/app'
        }
        
        # Tenta achar EntitySets (Nome da Tabela na URL)
        print("\n2. EntitySets Disponíveis (Use um destes na URL):")
        # Busca genérica por tags que contenham EntitySet
        found_sets = []
        for elem in root.iter():
            if 'EntitySet' in elem.tag:
                name = elem.get('Name')
                if name:
                    print(f"   -> Nome: {name}")
                    found_sets.append(name)
        
        # Tenta achar Propriedades (Nomes das Colunas e Tipos)
        print("\n3. Propriedades e Tipos (Verifique o campo de data):")
        for elem in root.iter():
            if 'Property' in elem.tag:
                name = elem.get('Name')
                type_ = elem.get('Type')
                if name and ('data' in name.lower() or 'date' in name.lower() or 'edc' in name.lower()):
                    print(f"   -> Campo: {name} | Tipo: {type_}")

    except Exception as e:
        print(f"   [ERRO] Falha ao ler metadata: {e}")
        print(f"   Conteúdo (se houver): {r.text[:200]}")

if __name__ == "__main__":
    diagnosticar()