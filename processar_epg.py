import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import time

# Configurações de Identidade
GENERATOR_NAME = "Gemini-Pro-Miner"
FILE_NAME = "epg-gemini.xml"
BASE_URL = "https://mi.tv"
GUIDE_URL = "https://mi.tv/br/guia-tv"

def limpar_id(nome):
    """Transforma 'Globo SP' em 'GLOBO.BR'"""
    n = str(nome).upper()
    n = re.sub(r' HD| SD| 4K| BRASIL| SUDOESTE| PAULISTA', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    return f"{n}.BR"

def minerar_guia():
    print(f"🚀 Iniciando Mineração Profissional Mi.tv...")
    root = ET.Element("tv", {"generator-info-name": GENERATOR_NAME})
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9'
    }

    try:
        # 1. Acessa a página principal do guia
        response = requests.get(GUIDE_URL, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ Erro ao acessar portal: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'lxml')
        canais_html = soup.find_all('li', class_='channel')
        
        print(f"📺 Canais encontrados: {len(canais_html)}")

        for canal in canais_html:
            nome_canal = canal.find('h2').text.strip()
            id_final = limpar_id(nome_canal)
            
            # Criar Tag do Canal
            c_tag = ET.SubElement(root, "channel", id=id_final)
            ET.SubElement(c_tag, "display-name").text = nome_canal
            
            # 2. Processar programas do canal
            programas = canal.find_all('a', class_='program')
            for prog in programas:
                titulo = prog.find('h3').text.strip() if prog.find('h3') else "Sem Título"
                horario_str = prog.find('span', class_='time').text.strip() # Ex: "20:30"
                
                # Pegar link da imagem e descrição (se disponível na grade)
                # O Mi.tv costuma colocar a imagem no estilo background-image ou tag img
                img_tag = prog.find('img')
                img_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ""
                
                # Sinopse resumida (o que aparece no hover/card)
                sinopse = prog.find('p', class_='synopsis')
                descricao = sinopse.text.strip() if sinopse else "Programação atualizada via Gemini Miner."

                # Tratar Horário (Brasília -0300)
                agora = datetime.now()
                hora, minuto = horario_str.split(':')
                dt_prog = agora.replace(hour=int(hora), minute=int(minuto), second=0, microsecond=0)
                
                # Ajuste simples: se a hora for menor que a atual, pode ser do dia seguinte
                if dt_prog < agora - timedelta(hours=6):
                    dt_prog += timedelta(days=1)

                start_xml = dt_prog.strftime("%Y%m%d%H%M%S -0300")
                stop_xml = (dt_prog + timedelta(hours=1)).strftime("%Y%m%d%H%M%S -0300") # Estimativa de 1h

                # Criar Tag do Programa
                p_tag = ET.SubElement(root, "programme", start=start_xml, stop=stop_xml, channel=id_final)
                ET.SubElement(p_tag, "title", lang="pt").text = titulo
                ET.SubElement(p_tag, "desc", lang="pt").text = descricao
                
                if img_url:
                    if not img_url.startswith('http'):
                        img_url = "https:" + img_url
                    ET.SubElement(p_tag, "icon", src=img_url)

                # Categoria
                cat = prog.find('span', class_='category')
                if cat:
                    ET.SubElement(p_tag, "category", lang="pt").text = cat.text.strip()

        # Salvar o arquivo
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"✅ Sucesso! Arquivo {FILE_NAME} gerado com descrições e imagens.")

    except Exception as e:
        print(f"💥 Erro crítico na mineração: {e}")

if __name__ == "__main__":
    minerar_guia()
