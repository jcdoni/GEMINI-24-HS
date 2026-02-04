import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# Configurações de Identidade
GENERATOR_NAME = "Gemini-EPG-Miner"
FILE_NAME = "epg-gemini.xml"

# Mapeamento de Canais (Exemplos principais - o script tentará mapear o resto automaticamente)
# Você pode adicionar mais aqui seguindo o padrão: "Nome no Mi.tv": "ID.BR"
MAPA_CANAIS = {
    "Globo": "GLOBO.BR",
    "SBT": "SBT.BR",
    "Record": "RECORD.BR",
    "Band": "BAND.BR",
    "SporTV": "SPORTV.BR",
    "SporTV 2": "SPORTV2.BR",
    "SporTV 3": "SPORTV3.BR",
    "ESPN": "ESPN.BR",
    "ESPN 2": "ESPN2.BR",
    "ESPN 4": "ESPN4.BR",
    "Discovery Channel": "DISCOVERY.BR",
    "Discovery Kids": "DISCOVERYKIDS.BR",
    "Disney Channel": "DISNEY.BR",
    "Cartoon Network": "CARTOON.BR",
    "HBO": "HBO.BR",
    "HBO 2": "HBO2.BR",
    "Warner Channel": "WARNER.BR",
    "AXN": "AXN.BR",
    "Universal TV": "UNIVERSAL.BR",
    "Telecine Premium": "TCPREMIUM.BR",
    "Telecine Action": "TCACTION.BR"
}

def limpar_nome_id(nome):
    """Gera um ID padrão NOME.BR para canais não mapeados manualmente"""
    n = str(nome).upper()
    n = re.sub(r' HD| SD| 4K| BRASIL| LATAM', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    return f"{n}.BR"

def minerar_mitv():
    print(f"Iniciando mineração no Mi.tv às {datetime.now()}...")
    
    root = ET.Element("tv", {"generator-info-name": GENERATOR_NAME})
    canais_processados = set()
    
    # Vamos minerar Hoje (day=0) e Amanhã (day=1)
    for day in range(2):
        data_alvo = (datetime.now() - timedelta(hours=3) + timedelta(days=day)).strftime('%Y-%m-%d')
        url = f"https://mi.tv/br/guia-tv/channels?day={day}"
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"Erro ao acessar dia {day}: Status {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            canais_html = soup.find_all('li', class_='channel')
            
            for canal in canais_html:
                nome_canal = canal.find('h2').text.strip()
                id_final = MAPA_CANAIS.get(nome_canal, limpar_nome_id(nome_canal))
                
                # 1. Criar tag do Canal (apenas uma vez)
                if id_final not in canais_processados:
                    c_tag = ET.SubElement(root, "channel", id=id_final)
                    ET.SubElement(c_tag, "display-name").text = nome_canal
                    canais_processados.add(id_final)
                
                # 2. Pegar Programas
                programas = canal.find_all('a', class_='program')
                for prog in programas:
                    titulo = prog.find('h3').text.strip() if prog.find('h3') else "Sem Título"
                    horario_str = prog.find('span', class_='time').text.strip() # Ex: "22:30"
                    
                    # Converter horário para formato XMLTV (YYYYMMDDHHMMSS +0000)
                    # Nota: O Mi.tv exibe no horário de Brasília (-0300)
                    hora, minuto = horario_str.split(':')
                    dt_prog = datetime.strptime(f"{data_alvo} {hora}:{minuto}", "%Y-%m-%d %H:%M")
                    start_xml = dt_prog.strftime("%Y%m%d%H%M%S -0300")
                    
                    p_tag = ET.SubElement(root, "programme", start=start_xml, channel=id_final)
                    ET.SubElement(p_tag, "title", lang="pt").text = titulo
                    
        except Exception as e:
            print(f"Falha na mineração do dia {day}: {e}")

    # Salvar Arquivo
    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    with open(FILE_NAME, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8")
    
    print(f"Sucesso! {len(canais_processados)} canais minerados e salvos em {FILE_NAME}.")

if __name__ == "__main__":
    minerar_mitv()
