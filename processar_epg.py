import requests
import gzip
import xml.etree.ElementTree as ET
import re
import io

# --- Configurações ---
SOURCE_URL = "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz"
FILE_NAME = "epg-gemini.xml"
# Lista de termos para remover do nome visual (para limpar o ID)
TERMOS_REMOVER = [
    "SÃO PAULO/SP", "SAO PAULO/SP", "BELO HORIZONTE/MG", "CAMPINAS/SP", 
    "RIO DE JANEIRO/RJ", "CURITIBA/PR", "BRASÍLIA/DF", "PORTO ALEGRE/RS",
    "NET", "CLARO", "VIVO", "OI", "SKY"
]

def gerar_id_limpo(display_name):
    """
    Transforma 'São Paulo/SP  Premiere 4' em 'PREMIERE4.BR'
    """
    nome = str(display_name).upper()
    
    # 1. Tentar separar por duplo espaço (comum nesse arquivo: "Cidade  Canal")
    if "  " in nome:
        nome = nome.split("  ")[-1] # Pega tudo depois do espaço duplo
    
    # 2. Remover nomes de cidades caso não tenha separado pelo espaço
    for termo in TERMOS_REMOVER:
        nome = nome.replace(termo, "")

    # 3. Limpeza final de sufixos e caracteres especiais
    nome = re.sub(r' HD| SD| 4K| FHD| ³| ²', '', nome) # Remove qualidades e lixo
    nome = re.sub(r'[^A-Z0-9]', '', nome).strip()      # Mantém apenas letras e números
    
    if not nome:
        return "CANALDESCONHECIDO.BR"
        
    return f"{nome}.BR"

def baixar_e_processar():
    print(f"📡 Baixando EPG Bruto de: {SOURCE_URL}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        # Download
        response = requests.get(SOURCE_URL, headers=headers, timeout=60)
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            return

        # Descompactar
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            xml_content = f.read()

        print("⚙️ Higienizando IDs para padrão GEMINI TV...")
        old_root = ET.fromstring(xml_content)
        new_root = ET.Element("tv", {"generator-info-name": "Gemini-Sheet-Cleaner"})

        # Mapas para controle
        mapa_de_ids = {} # ID Antigo -> ID Novo
        ids_ja_criados = set() # Para não criar canais duplicados (ex: Globo SP e Globo RJ viram só GLOBO.BR)

        # 1. Processar CANAIS
        count_canais = 0
        for channel in old_root.findall('channel'):
            original_id = channel.get('id')
            display_name = channel.find('display-name').text
            
            if not display_name: continue

            # Gera o ID Limpo (ex: SPORTV.BR)
            novo_id = gerar_id_limpo(display_name)
            mapa_de_ids[original_id] = novo_id

            # Se esse canal já foi criado (ex: já pegamos a Globo de outra cidade), pulamos a recriação da tag
            if novo_id in ids_ja_criados:
                continue
            
            ids_ja_criados.add(novo_id)
            count_canais += 1

            # Cria tag no novo XML
            c_tag = ET.SubElement(new_root, "channel", id=novo_id)
            # Limpa o Display Name também para ficar bonito na TV
            nome_visual = display_name.split("  ")[-1] if "  " in display_name else display_name
            nome_visual = re.sub(r' ³| ²', '', nome_visual).strip()
            
            ET.SubElement(c_tag, "display-name").text = nome_visual
            
            # Mantém ícone
            icon = channel.find('icon')
            if icon is not None:
                ET.SubElement(c_tag, "icon", src=icon.get('src'))

        print(f"✅ {count_canais} canais únicos consolidados (IDs limpos).")

        # 2. Processar PROGRAMAS
        print("🎬 Processando grade de programação...")
        count_progs = 0
        programas_adicionados = set() # Evitar duplicidade exata de programas

        for prog in old_root.findall('programme'):
            old_chan = prog.get('channel')
            if old_chan in mapa_de_ids:
                new_chan = mapa_de_ids[old_chan]
                
                start = prog.get('start')
                
                # Chave única para evitar duplicar o mesmo programa no mesmo horário no mesmo canal
                # (Isso resolve o problema de ter Globo SP e Globo RJ com a mesma grade)
                chave_prog = f"{new_chan}_{start}"
                if chave_prog in programas_adicionados:
                    continue
                
                programas_adicionados.add(chave_prog)
                count_progs += 1

                # Criar nova tag
                p_tag = ET.SubElement(new_root, "programme", {
                    "start": start, 
                    "stop": prog.get('stop'), 
                    "channel": new_chan
                })
                
                # Copiar dados
                for child in prog:
                    # Copia Titulo, Descrição, Categoria, Icone
                    elem = ET.SubElement(p_tag, child.tag, child.attrib)
                    elem.text = child.text

        # 3. Salvar
        tree = ET.ElementTree(new_root)
        ET.indent(tree, space="\t", level=0)
        
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"💾 Arquivo final gerado: {FILE_NAME}")
        print(f"📊 Resumo: {count_canais} Canais | {count_progs} Programas.")

    except Exception as e:
        print(f"💥 Erro Fatal: {e}")

if __name__ == "__main__":
    baixar_e_processar()
