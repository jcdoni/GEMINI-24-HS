import requests
import re
import xml.etree.ElementTree as ET

# Fontes de Elite que conversamos
FONTES_XML = [
    "https://iptv-org.github.io/epg/guides/br/mi.tv.xml",
    "https://raw.githubusercontent.com/DeivisonNunes/EPG/main/claro.xml",
    "https://raw.githubusercontent.com/LuanElias/EPG/master/guide.xml"
]

def limpar_id(nome):
    if not nome: return ""
    # Remove lixos e padroniza para NOME.BR
    n = nome.upper()
    n = re.sub(r'PLUTO TV|SAMSUNG TV PLUS|CLARO|VIVO|SKY|NET|[\(\[].*?[\)\]]| HD| SD| 4K| FHD| LEG| DUB| 24H| 24HS| PREMIUM| TV', '', n)
    n = re.sub(r'[^A-Z0-9]', '', n)
    return n + ".BR"

def processar():
    canais_acumulados = {}
    programas_acumulados = []

    for url in FONTES_XML:
        try:
            print(f"Baixando: {url}")
            response = requests.get(url, timeout=30)
            tree = ET.fromstring(response.content)

            # Processa Canais
            for channel in tree.findall('channel'):
                display_name = channel.find('display-name').text
                novo_id = limpar_id(display_name)
                if novo_id not in canais_acumulados:
                    channel.set('id', novo_id)
                    canais_acumulados[novo_id] = channel

            # Processa Programação
            for programme in tree.findall('programme'):
                old_id = programme.get('channel')
                # Tenta achar o nome do canal original para traduzir o ID do programa
                for c in tree.findall(f"channel[@id='{old_id}']"):
                    dn = c.find('display-name').text
                    programme.set('channel', limpar_id(dn))
                    programas_acumulados.append(programme)
        except Exception as e:
            print(f"Erro na fonte {url}: {e}")

    # Criar novo XML final
    root = ET.Element("tv")
    for c in canais_acumulados.values(): root.append(c)
    for p in programas_acumulados: root.append(p)

    tree_final = ET.ElementTree(root)
    tree_final.write("epg-gemini.xml", encoding="utf-8", xml_declaration=True)
    print("Arquivo epg-gemini.xml gerado com sucesso!")

if __name__ == "__main__":
    processar()
