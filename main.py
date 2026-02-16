import os
import time
import requests
import re
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# Librerías de Navegador
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent

# --- CONFIGURACIÓN ---
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']

# Usamos BetExplorer (Más fácil de leer)
TARGET_URL = "https://www.betexplorer.com/next/esports/"

COLOR_ESPORTS = 10181046 # Morado

def obtener_hora_chile():
    tz_chile = pytz.timezone('America/Santiago')
    return datetime.now(tz_chile).strftime("%H:%M")

def configurar_driver():
    ua = UserAgent()
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f'user-agent={ua.random}')
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def enviar_discord(partidos):
    if not partidos: return

    # Dividimos en bloques de 10
    chunks = [partidos[i:i + 10] for i in range(0, len(partidos), 10)]

    for chunk in chunks:
        fields = []
        for p in chunk:
            fields.append({
                "name": f"⏰ {p['hora']} | {p['torneo']}",
                "value": f"🎮 **{p['partido']}**\n"
                         f"📊 1: **{p['c1']}** | 2: **{p['c2']}**\n"
                         f"🔗 [Ver en BetExplorer]({p['link']})",
                "inline": False
            })

        embed = {
            "embeds": [{
                "title": "👾 Alerta eSports - BetExplorer",
                "color": COLOR_ESPORTS,
                "fields": fields,
                "footer": {"text": f"Scraper v2.0 | Hora Actual: {obtener_hora_chile()}"}
            }]
        }
        requests.post(WEBHOOK_URL, json=embed)
        time.sleep(1) 

def limpiar_texto(texto):
    """Elimina espacios extra y saltos de línea"""
    return " ".join(texto.split())

def scrapear_betexplorer():
    print("--- 🕵️ INICIANDO RASTREO EN BETEXPLORER ---")
    driver = configurar_driver()
    
    try:
        print(f"Navegando a: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # Esperamos a que aparezca la tabla de partidos (clase 'table-main')
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "table-main"))
        )
        print("✅ Tabla detectada. Analizando datos...")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tabla = soup.find("table", class_="table-main")
        filas = tabla.find_all("tr")
        
        print(f"🔍 Filas totales encontradas: {len(filas)}")
        
        partidos = []
        torneo_actual = "Torneo General" # Guardamos el último torneo visto (filas header)

        for fila in filas:
            # 1. ¿Es un título de torneo? (Suelen tener links a la liga)
            if "js-tournament" in fila.get("class", []):
                link_torneo = fila.find("a")
                if link_torneo:
                    torneo_actual = link_torneo.text.strip()
                continue
            
            # 2. ¿Es un partido? (No debe tener la clase 'rt' que es header de tabla)
            if "rt" in fila.get("class", []):
                continue
                
            cols = fila.find_all("td")
            if len(cols) < 5: continue # Si no tiene suficientes columnas, no sirve

            try:
                # Extracción Robusta
                nombre_partido = limpiar_texto(cols[0].text)
                link_partido = "https://www.betexplorer.com" + cols[0].find("a")['href'] if cols[0].find("a") else TARGET_URL
                
                # La hora suele estar en la columna 1 o dentro del texto
                hora = limpiar_texto(cols[1].text)
                if not hora: hora = "Hoy"
                
                # Cuotas (Suelen estar al final)
                # Buscamos columnas con atributos data-odd
                odds = fila.find_all("td", attrs={"data-odd": True})
                
                c1 = "-"
                c2 = "-"
                
                if len(odds) >= 2:
                    c1 = odds[0].text.strip()
                    c2 = odds[1].text.strip()
                
                # Filtro: Si no hay cuotas reales, saltamos
                if c1 == "" or c2 == "": continue

                partidos.append({
                    "torneo": torneo_actual,
                    "partido": nombre_partido,
                    "hora": hora,
                    "c1": c1,
                    "c2": c2,
                    "link": link_partido
                })
                
            except Exception as e:
                # Si una fila falla, no rompemos todo
                continue

        print(f"✅ Extracción exitosa: {len(partidos)} eventos listos.")
        enviar_discord(partidos)

    except Exception as e:
        print(f"❌ Error crítico: {e}")
        # Tip de debug: Si falla, imprime el HTML para ver qué pasó
        # print(driver.page_source[:500]) 
    finally:
        driver.quit()
        print("--- 🏁 PROCESO TERMINADO ---")

if __name__ == "__main__":
    scrapear_betexplorer()