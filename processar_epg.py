import requests
import gzip
import xml.etree.ElementTree as ET
import re
import io

# --- Configurações ---
# Agora com as duas fontes oficiais
SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BR2.xml.gz"
]
FILE_NAME = "epg-gemini.xml"

TERMOS_REMOVER = [
    "SÃO PAULO/SP", "SAO PAULO/SP", "BELO HORIZONTE/MG", "CAMPINAS/SP", 
    "RIO DE JANEIRO/RJ", "CURITIBA/PR", "BRASÍLIA/DF", "PORTO ALEGRE/RS",
    "NET", "CLARO", "VIVO", "OI", "SKY"
]

def gerar_id_limpo(display_name):
    if not display_name: return "CANALDESCONHECIDO.BR"
    nome = str(display_name).upper()
    if "  " in nome:
        nome = nome.split("  ")[-1]
    for termo in TERMOS_REMOVER:
        nome = nome.replace(termo, "")
    nome = re.sub(r' HD| SD| 4K| FHD| ³| ²', '', nome)
    nome = re.sub(r'[^A-Z0-9]', '', nome).strip()
    return f"{nome}.BR" if nome else "CANALDESCONHECIDO.BR"

def baixar_e_processar():
    new_root = ET.Element("tv", {"generator-info-name": "Gemini-Multi-Source-Cleaner"})
    mapa_de_ids = {} 
    ids_ja_criados = set()
    programas_adicionados = set()
    count_canais = 0
    count_progs = 0

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for url in SOURCES:
        try:
            print(f"📡 Baixando: {url}")
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code != 200: continue

            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
                xml_content = f.read()
            
            old_root = ET.fromstring(xml_content)

            # 1. Processar Canais da fonte atual
            for channel in old_root.findall('channel'):
                original_id = channel.get('id')
                d_name_elem = channel.find('display-name')
                if d_name_elem is None: continue
                
                display_name = d_name_elem.text
                novo_id = gerar_id_limpo(display_name)
                mapa_de_ids[original_id] = novo_id

                if novo_id not in ids_ja_criados:
                    ids_ja_criados.add(novo_id)
                    count_canais += 1
                    c_tag = ET.SubElement(new_root, "channel", id=novo_id)
                    nome_visual = display_name.split("  ")[-1] if "  " in display_name else display_name
                    ET.SubElement(c_tag, "display-name").text = re.sub(r' ³| ²', '', nome_visual).strip()
                    icon = channel.find('icon')
                    if icon is not None:
                        ET.SubElement(c_tag, "icon", src=icon.get('src'))

            # 2. Processar Programas da fonte atual
            for prog in old_root.findall('programme'):
                old_chan = prog.get('channel')
                if old_chan in mapa_de_ids:
                    new_chan = mapa_de_ids[old_chan]
                    start = prog.get('start')
                    chave_prog = f"{new_chan}_{start}"
                    
                    if chave_prog not in programas_adicionados:
                        programas_adicionados.add(chave_prog)
                        count_progs += 1
                        p_tag = ET.SubElement(new_root, "programme", {
                            "start": start, 
                            "stop": prog.get('stop'), 
                            "channel": new_chan
                        })
                        for child in prog:
                            elem = ET.SubElement(p_tag, child.tag, child.attrib)
                            elem.text = child.text
        except Exception as e:
            print(f"⚠️ Erro ao processar fonte {url}: {e}")

    # Salvar arquivo final consolidado
    tree = ET.ElementTree(new_root)
    ET.indent(tree, space="\t", level=0)
    with open(FILE_NAME, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8")
    
    print(f"💾 Sucesso! {count_canais} Canais e {count_progs} Programas salvos em {FILE_NAME}")

if __name__ == "__main__":
    baixar_e_processar()
