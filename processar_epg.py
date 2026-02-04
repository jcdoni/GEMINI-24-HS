import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# Configurações de Identidade
GENERATOR_NAME = "Gemini-Elite-Miner"
FILE_NAME = "epg-gemini.xml"
SOURCE_URL = "https://meuguia.tv/programacao/categoria/Todos"

def limpar_id(nome):
    """Transforma 'Discovery Channel HD' em 'DISCOVERY.BR'"""
    n = str(nome).upper()
    n = re.sub(r' HD| SD| 4K| BRASIL| SUDOESTE| PAULISTA| RJ| SP', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    if not n: return "CANAL.BR"
    return f"{n}.BR"

def minerar_meuguia():
    print(f"🚀 Iniciando Mineração no MeuGuia.tv às {datetime.now()}...")
    
    root = ET.Element("tv", {"generator-info-name": GENERATOR_NAME})
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        response = requests.get(SOURCE_URL, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ Erro ao acessar fonte: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'lxml')
        # No MeuGuia, os canais ficam em listas dento de <ul> ou direto nas <li>
        canais_html = soup.find_all('li', class_='channel-container') or soup.find_all('li')
        
        canais_contados = 0
        
        for canal in canais_html:
            nome_tag = canal.find('h2') or canal.find('span', class_='channel-name')
            if not nome_tag: continue
            
            nome_canal = nome_tag.text.strip()
            id_final = limpar_id(nome_canal)
            
            # 1. Criar tag do Canal
            c_tag = ET.SubElement(root, "channel", id=id_final)
            ET.SubElement(c_tag, "display-name").text = nome_canal
            canais_contados += 1

            # 2. Pegar Programas do Canal
            programas = canal.find_all('a')
            for prog in programas:
                # Extrair Título
                t_tag = prog.find('h3') or prog.find('span', class_='program-title')
                if not t_tag: continue
                titulo = t_tag.text.strip()

                # Extrair Horário
                h_tag = prog.find('span', class_='time')
                if not h_tag: continue
                horario_str = h_tag.text.strip() # Ex: "21:00"

                # Extrair Imagem (Thumbnail)
                img_tag = prog.find('img')
                img_url = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""

                # Extrair Descrição (Sinopse)
                # Geralmente no title do link ou em uma div escondida
                desc_text = prog.get('title') or "Programação atualizada via Gemini Miner."

                # Tratar Data/Hora (Assume hoje)
                agora = datetime.now()
                try:
                    h, m = horario_str.split(':')
                    dt_prog = agora.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                    
                    # Se o horário já passou muito, provavelmente é de amanhã
                    if dt_prog < agora - timedelta(hours=5):
                        dt_prog += timedelta(days=1)
                except:
                    continue

                start_xml = dt_prog.strftime("%Y%m%d%H%M%S -0300")
                stop_xml = (dt_prog + timedelta(hours=1)).strftime("%Y%m%d%H%M%S -0300")

                # Montar o XML do programa
                p_tag = ET.SubElement(root, "programme", start=start_xml, stop=stop_xml, channel=id_final)
                ET.SubElement(p_tag, "title", lang="pt").text = titulo
                ET.SubElement(p_tag, "desc", lang="pt").text = desc_text
                
                if img_url:
                    if img_url.startswith('//'): img_url = "https:" + img_url
                    ET.SubElement(p_tag, "icon", src=img_url)

        # Salvar Arquivo
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"✅ Sucesso! {canais_contados} canais minerados em {FILE_NAME}.")

    except Exception as e:
        print(f"💥 Erro na mineração: {e}")

if __name__ == "__main__":
    minerar_meuguia()
