import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import time

# Configurações de Identidade
GENERATOR_NAME = "Gemini-Sinopse-Image-Miner"
FILE_NAME = "epg-gemini.xml"
BASE_URL = "https://meuguia.tv"

def limpar_id(nome):
    """Padroniza para o formato NOME.BR"""
    n = str(nome).upper()
    n = re.sub(r' HD| SD| 4K| BRASIL| SUDOESTE| PAULISTA| RJ| SP', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n).strip()
    return f"{n}.BR" if n else "CANAL.BR"

def minerar_detalhes():
    print(f"🚀 Iniciando Mineração de Elite (Sinopses + Imagens)...")
    root = ET.Element("tv", {"generator-info-name": GENERATOR_NAME})
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 1. Mapeia todos os canais disponíveis na categoria "Todos"
        print("📡 Mapeando lista de canais...")
        response = requests.get(f"{BASE_URL}/programacao/categoria/Todos", headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ Erro ao acessar lista de canais: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'lxml')
        links_canais = soup.find_all('a', href=re.compile(r'/programacao/canal/'))
        
        canais_para_processar = {}
        for l in links_canais:
            nome_c = l.find('h2').text.strip() if l.find('h2') else l.text.strip()
            if nome_c:
                canais_para_processar[nome_c] = BASE_URL + l['href']

        print(f"🔍 {len(canais_para_processar)} canais encontrados. Iniciando extração individual...")

        for nome_canal, url_canal in canais_para_processar.items():
            id_final = limpar_id(nome_canal)
            print(f"📥 Extraindo: {nome_canal} -> {id_final}")
            
            # Tag do Canal
            c_tag = ET.SubElement(root, "channel", id=id_final)
            ET.SubElement(c_tag, "display-name").text = nome_canal

            try:
                # 2. Entra na URL PRÓPRIA do canal para pegar sinopses e imagens
                res_c = requests.get(url_canal, headers=headers, timeout=20)
                soup_c = BeautifulSoup(res_c.text, 'lxml')
                
                # Cada item de programação
                itens = soup_c.find_all('li', class_=re.compile(r'program'))
                
                for item in itens:
                    t_tag = item.find('h3') or item.find('span', class_='title')
                    h_tag = item.find('span', class_='time')
                    if not t_tag or not h_tag: continue

                    titulo = t_tag.text.strip()
                    horario = h_tag.text.strip()
                    
                    # EXTRAÇÃO DE IMAGEM
                    img_tag = item.find('img')
                    img_url = ""
                    if img_tag:
                        img_url = img_tag.get('src') or img_tag.get('data-src') or ""
                        if img_url.startswith('//'): img_url = "https:" + img_url

                    # EXTRAÇÃO DE SINOPSE
                    # No detalhe do canal, a sinopse costuma estar no atributo 'title' do link ou numa div
                    sinopse = item.get('title') or "Sem sinopse detalhada disponível no momento."
                    
                    # Tratar Horário
                    agora = datetime.now()
                    try:
                        h, m = horario.split(':')
                        dt_start = agora.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                        if dt_start < agora - timedelta(hours=8): dt_start += timedelta(days=1)
                        
                        start_xml = dt_start.strftime("%Y%m%d%H%M%S -0300")
                        stop_xml = (dt_start + timedelta(hours=1)).strftime("%Y%m%d%H%M%S -0300")
                        
                        # Montar Programa no XML
                        p_tag = ET.SubElement(root, "programme", start=start_xml, stop=stop_xml, channel=id_final)
                        ET.SubElement(p_tag, "title", lang="pt").text = titulo
                        ET.SubElement(p_tag, "desc", lang="pt").text = sinopse
                        if img_url:
                            ET.SubElement(p_tag, "icon", src=img_url)
                    except:
                        continue

                # Delay curto para evitar bloqueio por excesso de requisições
                time.sleep(0.3)

            except Exception as e:
                print(f"   ⚠️ Erro ao processar canal {nome_canal}: {e}")

        # 3. Salva o arquivo final
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        with open(FILE_NAME, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8")
        
        print(f"✅ Sucesso absoluto! {FILE_NAME} gerado com imagens e sinopses.")

    except Exception as e:
        print(f"💥 Falha Geral: {e}")

if __name__ == "__main__":
    minerar_detalhes()
