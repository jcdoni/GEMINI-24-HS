# ====================================================================
# 🧬 DNA - PROTOCOLO DE INTEGRIDADE GEMINI (PYTHON)
# ====================================================================
# 1. ESTADO: [ATIVO] - VERSÃO 1.2 (ULTRA-ALPHA)
# 2. FUNÇÕES VITAIS: gerar_id_limpo, baixar_e_processar
# 3. SINCRONIA: Sufixo .BRASIL | Ordenação A-Z Real (Sem erro de acento)
# 4. PROIBIÇÃO: Apagar filtros de limpeza ou mudar sufixo .BRASIL
# ====================================================================

import requests
import gzip
import xml.etree.ElementTree as ET
import re
import io
import unicodedata

# --- Configurações ---
SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BR2.xml.gz"
]
FILE_NAME = "epg-gemini.xml"

TERMOS_REMOVER = [
    "SÃO PAULO/SP", "SAO PAULO/SP", "BELO HORIZONTE/MG", "CAMPINAS/SP", 
    "RIO DE JANEIRO/RJ", "CURITIBA/PR", "BRASÍLIA/DF", "PORTO ALEGRE/RS",
    "NET", "CLARO", "VIVO", "OI", "SKY", "PAMPA", "TV ", "REDE "
]

LIXO_TECNICO = r'\(720P\)|\(1080P\)|\(4K\)|\(FHD\)|\(HD\)|\(SD\)|\[NAO 24\/7\]|\[OFF\]|³|²'

def normalizar_para_sort(texto):
    """Remove acentos e espaços extras apenas para a lógica de ordenação."""
    if not texto: return ""
    texto = texto.strip().upper()
    return "".join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))

def gerar_id_limpo(display_name):
    if not display_name: return "CANALDESCONHECIDO.BRASIL"
    nome = str(display_name).upper()
    for termo in TERMOS_REMOVER:
        nome = nome.replace(termo, "")
    nome = re.sub(LIXO_TECNICO, '', nome)
    nome = re.sub(r'[^A-Z0-9]', '', nome).strip()
    return f"{nome}.BRASIL" if nome else "CANALDESCONHECIDO.BRASIL"

def baixar_e_processar():
    new_root = ET.Element("tv", {"generator-info-name": "Gemini-DNA-UltraAlpha"})
    lista_canais = []
    lista_programas = []
    mapa_de_ids = {} 
    ids_ja_criados = set()
    programas_adicionados = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for url in SOURCES:
        try:
            print(f"📡 Baixando: {url}")
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code != 200: continue
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
                xml_content = f.read()
            old_root = ET.fromstring(xml_content)

            for channel in old_root.findall('channel'):
                original_id = channel.get('id')
                d_name_elem = channel.find('display-name')
                if d_name_elem is None: continue
                display_name = d_name_elem.text
                
                # Filtro VOD
                if any(ext in display_name.lower() for ext in ['.mp4', '.mkv', 'temporada', 's01']):
                    continue

                novo_id = gerar_id_limpo(display_name)
                mapa_de_ids[original_id] = novo_id

                if novo_id not in ids_ja_criados:
                    ids_ja_criados.add(novo_id)
                    nome_visual = re.sub(LIXO_TECNICO, '', display_name).strip()
                    icon_src = ""
                    icon = channel.find('icon')
                    if icon is not None: icon_src = icon.get('src')
                    
                    lista_canais.append({
                        'id': novo_id,
                        'name': nome_visual,
                        'sort_key': normalizar_para_sort(nome_visual),
                        'icon': icon_src
                    })

            for prog in old_root.findall('programme'):
                old_chan = prog.get('channel')
                if old_chan in mapa_de_ids:
                    new_chan = mapa_de_ids[old_chan]
                    start = prog.get('start')
                    chave_prog = f"{new_chan}_{start}"
                    if chave_prog not in programas_adicionados:
                        programas_adicionados.add(chave_prog)
                        prog.set('channel', new_chan)
                        lista_programas.append(prog)
        except Exception as e:
            print(f"⚠️ Erro: {e}")

    # --- [DNA] ORDENAÇÃO ULTRA-ALPHA ---
    print("🔤 Aplicando Ordenação DNA (A-Z)...")
    lista_canais.sort(key=lambda x: x['sort_key'])

    for c in lista_canais:
        c_tag = ET.SubElement(new_root, "channel", id=c['id'])
        ET.SubElement(c_tag, "display-name").text = c['name']
        if c['icon']: ET.SubElement(c_tag, "icon", src=c['icon'])

    for p in lista_programas:
        new_root.append(p)

    tree = ET.ElementTree(new_root)
    ET.indent(tree, space="\t", level=0)
    with open(FILE_NAME, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8")
    
    print(f"💾 Sucesso! {len(lista_canais)} Canais em Ordem Alfabética.")

if __name__ == "__main__":
    baixar_e_processar()
