import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import time

GENERATOR_NAME = "Gemini-Deep-Miner"
FILE_NAME = "epg-gemini.xml"
BASE_URL = "https://meuguia.tv"

def limpar_id(nome):
    n = str(nome).upper()
    n = re.sub(r' HD| SD| 4K| BRASIL| SUDOESTE| PAULISTA| RJ| SP', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    return f"{n}.BR" if n else "CANAL.BR"

def minerar_tudo():
    print(f"🚀 Iniciando Mapeamento de URLs no MeuGuia...")
    root = ET.Element("tv", {"generator-info-name": GENERATOR_NAME})
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        # 1. Mapear os canais na página principal
        res = requests.get(f"{BASE_URL}/programacao/categoria/Todos", headers=headers, timeout=30)
        soup = BeautifulSoup(res.text, 'lxml')
        
        # Procura todos os links que levam para a página de um canal específico
        links_canais = soup.find_all('a', href=re.compile(r'/programacao/canal/'))
        
        # Usamos um set para não repetir canal
        urls_unicas = {}
        for l in links_canais:
            nome = l.text.strip()
            if nome:
                urls_unicas[nome] = BASE_URL + l['href']

        print(f"🔍 {len(urls_unicas)} canais únicos encontrados. Iniciando varredura detalhada...")

        count = 0
        for nome_canal, url_canal in urls_unicas.items():
            # Para não ser bloqueado, pegamos os primeiros 50 canais como teste ou todos
            # Se quiser todos, pode deixar rodar. GitHub Actions aguenta.
            count += 1
            id_final = limpar_id(nome_canal)
            print(f"[{count}] Minerando: {nome_canal} ({id_final})")
            
            # Criar tag do Canal
            c_tag = ET.SubElement(root, "channel", id=id_final)
            ET.SubElement(c_tag, "display-name").text = nome_canal

            # 2. Entrar na URL própria do canal
            try:
                res_c = requests.get(url_canal, headers=headers, timeout=20)
                soup_c = BeautifulSoup(res_c.text, 'lxml')
                
                # No MeuGuia, cada programa na página do canal está em uma <li> ou <a>
                programas = soup_c.find_all('li', class_=re.compile(r'program')) or soup_c.find_all('div', class_='program-item')
                
                for p in programas:
                    # Título, Hora, Descrição e Imagem
                    t_tag = p.find('h3') or p.find('span', class_='title')
                    h_tag = p.find('span', class_='time')
                    img_tag = p.find('img')
                    
                    if not t_tag or not h_tag: continue
                    
                    titulo = t_tag.text.strip()
                    horario = h_tag.text.strip()
                    img_url = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
                    # A descrição no MeuGuia costuma estar num atributo 'title' ou parágrafo
                    desc = p.get('title') or (p.find('p').text.strip() if p.find('p') else "Sem descrição disponível.")

                    # Converter Horário
                    agora = datetime.now()
                    h, m = horario.split(':')
                    dt_start = agora.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                    if dt_start < agora - timedelta(hours=8): dt_start += timedelta(days=1)
                    
                    start_xml = dt_start.strftime("%Y%m%d%H%M%S -0300")
                    stop_xml = (dt_start + timedelta(hours=1)).strftime("%Y%m%d%H%M%S -0300")

                    # Criar Programa no XML
                    prog_tag = ET.SubElement(root, "programme", start=start_xml, stop=stop_xml, channel=id_final)
                    ET.SubElement(prog_tag, "title", lang="pt").text = titulo
                    ET.SubElement(prog_tag, "desc", lang="pt").text = desc
                    if img_url:
                        if img_url.startswith('//'): img_url = "https:" + img_url
                        ET.SubElement(prog_tag, "icon", src=img_url)
                
                # Pequena pausa para o site não nos expulsar
                time.sleep(0.5)

            except Exception as e:
                print(f"   ⚠️ Falha ao ler {nome_canal}: {e}")

        # Salvar final
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"✅ Finalizado! Arquivo {FILE_NAME} gerado com sucesso.")

    except Exception as e:
        print(f"💥 Erro Geral: {e}")

if __name__ == "__main__":
    minerar_tudo()
