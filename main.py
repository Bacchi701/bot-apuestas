import os
import time
import cloudscraper # La librería mágica
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import requests

# --- CONFIGURACIÓN ---
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
TARGET_URL = "https://www.betexplorer.com/next/esports/"
COLOR_ESPORTS = 10181046 

def obtener_hora_chile():
    tz_chile = pytz.timezone('America/Santiago')
    return datetime.now(tz_chile).strftime("%H:%M")

def enviar_discord(partidos):
    if not partidos:
        print("⚠️ No se encontraron partidos con cuotas para enviar.")
        return

    # Enviamos en grupos de 10
    chunks = [partidos[i:i + 10] for i in range(0, len(partidos), 10)]

    for chunk in chunks:
        fields = []
        for p in chunk:
            fields.append({
                "name": f"⏰ {p['hora']} | {p['torneo']}",
                "value": f"🎮 **{p['partido']}**\n"
                         f"📊 1: **{p['c1']}** | 2: **{p['c2']}**\n"
                         f"🔗 [Ver Detalles]({p['link']})",
                "inline": False
            })

        embed = {
            "embeds": [{
                "title": "👾 Alerta eSports - BetExplorer",
                "description": "Partidos próximos detectados vía CloudScraper",
                "color": COLOR_ESPORTS,
                "fields": fields,
                "footer": {"text": f"Modo Ligero v3.0 | Hora: {obtener_hora_chile()}"}
            }]
        }
        try:
            requests.post(WEBHOOK_URL, json=embed)
            time.sleep(1)
        except Exception as e:
            print(f"Error enviando a Discord: {e}")

def scrapear_ligero():
    print("--- 🚀 INICIANDO MODO LIGERO (CLOUDSCRAPER) ---")
    
    # Creamos un scraper que simula ser Chrome pero sin abrir Chrome
    scraper = cloudscraper.create_scraper()
    
    try:
        print(f"Consultando: {TARGET_URL}")
        response = scraper.get(TARGET_URL)
        
        if response.status_code != 200:
            print(f"❌ Error al entrar a la página: {response.status_code}")
            return

        print("✅ Página descargada. Analizando HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscamos la tabla principal
        tabla = soup.find("table", class_="table-main")
        if not tabla:
            print("⚠️ No encontré la tabla de partidos. Puede que la página haya cambiado o Cloudflare nos bloqueó.")
            # Debug: imprimir un poco del texto para ver qué pasó
            print(f"Contenido recibido: {response.text[:200]}...")
            return

        filas = tabla.find_all("tr")
        print(f"🔍 Filas detectadas: {len(filas)}")
        
        partidos = []
        torneo_actual = "Torneo General"

        for fila in filas:
            # Detectar Torneo
            if "js-tournament" in fila.get("class", []):
                link_t = fila.find("a")
                if link_t: torneo_actual = link_t.text.strip()
                continue
            
            # Ignorar cabeceras
            if "rt" in fila.get("class", []): continue
            
            cols = fila.find_all("td")
            if len(cols) < 5: continue

            try:
                # Extracción de datos
                nombres = cols[0].text.strip()
                # Limpieza de nombre (a veces tiene basura)
                nombres = " ".join(nombres.split())
                
                link_suffix = cols[0].find("a")['href'] if cols[0].find("a") else ""
                link_full = "https://www.betexplorer.com" + link_suffix if link_suffix else TARGET_URL
                
                hora = cols[1].text.strip()
                if not hora: hora = "Hoy"

                # Cuotas (buscamos atributos data-odd que usa BetExplorer)
                odds = fila.find_all("td", attrs={"data-odd": True})
                
                c1, c2 = "-", "-"
                if len(odds) >= 2:
                    c1 = odds[0].text.strip()
                    c2 = odds[1].text.strip()
                
                # Solo guardamos si hay cuotas válidas (distinto de guión o vacío)
                if c1 and c2 and c1 != "-" and c2 != "-":
                    partidos.append({
                        "torneo": torneo_actual,
                        "partido": nombres,
                        "hora": hora,
                        "c1": c1,
                        "c2": c2,
                        "link": link_full
                    })
            except Exception as e:
                continue

        print(f"✅ Partidos válidos extraídos: {len(partidos)}")
        enviar_discord(partidos)

    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    scrapear_ligero()