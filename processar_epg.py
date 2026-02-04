import requests
import gzip
import xml.etree.ElementTree as ET
import re
import io

# Configurações
SOURCE_URL = "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz"
FILE_NAME = "epg-gemini.xml"

def limpar_id(nome):
    """Padroniza os IDs para o formato NOME.BR"""
    n = str(nome).upper()
    # Remove termos comuns que sujam o ID
    n = re.sub(r' HD| SD| 4K| BRASIL| SUDOESTE| PAULISTA| RJ| SP| BR', '', n)
    # Remove caracteres especiais
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    return f"{n}.BR" if n else "CANAL.BR"

def baixar_e_processar():
    print(f"📡 Baixando EPG Premium de: {SOURCE_URL}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # 1. Baixar o arquivo compactado
        response = requests.get(SOURCE_URL, headers=headers, timeout=60)
        if response.status_code != 200:
            print(f"❌ Erro ao baixar arquivo: {response.status_code}")
            return

        # 2. Descompactar o GZ em memória
        print("📦 Descompactando dados...")
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            xml_content = f.read()

        # 3. Analisar o XML
        print("⚙️ Processando e limpando IDs...")
        old_root = ET.fromstring(xml_content)
        new_root = ET.Element("tv", {"generator-info-name": "Gemini-Premium-Integrator"})

        # Mapear canais e programas
        canal_map = {}

        # Processar Canais
        for channel in old_root.findall('channel'):
            display_name = channel.find('display-name').text if channel.find('display-name') is not None else ""
            if not display_name: continue
            
            old_id = channel.get('id')
            new_id = limpar_id(display_name)
            canal_map[old_id] = new_id

            c_tag = ET.SubElement(new_root, "channel", id=new_id)
            ET.SubElement(c_tag, "display-name").text = display_name
            
            # Manter ícone do canal se existir
            icon = channel.find('icon')
            if icon is not None:
                ET.SubElement(c_tag, "icon", src=icon.get('src'))

        # Processar Programas
        print("🎬 Vinculando programas, imagens e sinopses...")
        for prog in old_root.findall('programme'):
            old_chan_id = prog.get('channel')
            if old_chan_id in canal_map:
                new_chan_id = canal_map[old_chan_id]
                
                # Criar nova tag de programa com o ID limpo
                p_tag = ET.SubElement(new_root, "programme", {
                    "start": prog.get('start'),
                    "stop": prog.get('stop'),
                    "channel": new_chan_id
                })
                
                # Copiar Título, Descrição, Categoria e Ícone (Imagem do Programa)
                for elem in prog:
                    new_elem = ET.SubElement(p_tag, elem.tag, elem.attrib)
                    new_elem.text = elem.text

        # 4. Salvar o novo arquivo XML
        tree = ET.ElementTree(new_root)
        ET.indent(tree, space="\t", level=0)
        
        print(f"💾 Salvando arquivo final: {FILE_NAME}")
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"✅ Sucesso! EPG gerado com dados de hoje ({len(canal_map)} canais).")

    except Exception as e:
        print(f"💥 Erro no processamento: {e}")

if __name__ == "__main__":
    baixar_e_processar()
