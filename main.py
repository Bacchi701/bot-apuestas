import os
import time
import requests
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# Librerías de Scraping (Navegador)
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

# URL Objetivo: OddsPortal Próximos Partidos de eSports
TARGET_URL = "https://www.oddsportal.com/matches/esports/"

# Configuración de colores para Discord
COLOR_ESPORTS = 10181046 # Morado

def obtener_hora_chile():
    tz_chile = pytz.timezone('America/Santiago')
    return datetime.now(tz_chile).strftime("%H:%M")

def configurar_driver():
    """Configura un navegador Chrome indetectable (headless)"""
    ua = UserAgent()
    user_agent = ua.random

    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Sin interfaz gráfica
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Ocultar que es un bot
    
    # Instalamos el driver automáticamente
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def enviar_discord(partidos):
    if not partidos:
        print("No hay partidos para enviar.")
        return

    # Dividimos en bloques de 10 para no saturar el mensaje
    chunks = [partidos[i:i + 10] for i in range(0, len(partidos), 10)]

    for chunk in chunks:
        fields = []
        for p in chunk:
            fields.append({
                "name": f"{p['hora']} | {p['torneo']}",
                "value": f"🎮 **{p['equipo1']}** vs **{p['equipo2']}**\n"
                         f"💰 1: **{p['cuota1']}** | 2: **{p['cuota2']}**\n"
                         f"🔗 [Ver en OddsPortal]({p['link']})",
                "inline": False
            })

        embed = {
            "embeds": [{
                "title": "👾 Alerta eSports - OddsPortal",
                "description": "Mejores cuotas detectadas en el mercado.",
                "color": COLOR_ESPORTS,
                "fields": fields,
                "footer": {"text": f"Scraper v1.0 | Hora Actual: {obtener_hora_chile()}"}
            }]
        }
        requests.post(WEBHOOK_URL, json=embed)
        time.sleep(1) # Pausa pequeña para no spamear

def scrapear_oddsportal():
    print("--- 🕷️ INICIANDO SCRAPER DE ODDSPORTAL ---")
    driver = configurar_driver()
    
    try:
        print(f"Navegando a: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # Esperamos hasta 15 segundos a que aparezca la tabla de partidos
        # Buscamos un elemento común en OddsPortal (suelen cambiar clases, buscamos algo genérico)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='eventRow']"))
        )
        print("✅ Página cargada. Extrayendo HTML...")
        
        # Pasamos el HTML a BeautifulSoup para procesarlo rápido
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        partidos_encontrados = []
        
        # OddsPortal usa filas con clases dinámicas, pero suelen contener "eventRow"
        # OJO: Esto puede requerir ajustes si cambian el diseño
        filas = soup.select("div[class*='eventRow']")
        
        print(f"🔍 Se detectaron {len(filas)} filas potenciales.")

        for fila in filas[:15]: # Limitamos a los primeros 15 próximos
            try:
                # Extraer Texto del Torneo (A veces está en un header anterior, simplificamos aquí)
                # Intentamos sacar equipos
                textos = list(fila.stripped_strings)
                
                # Lógica heurística: Si tiene menos de 4 elementos, probablemente no es un partido válido
                if len(textos) < 4: continue
                
                # En OddsPortal la estructura suele ser: Hora, Equipo1, Equipo2, Cuota1, Cuota2
                # Esta parte es la más delicada y depende del CSS actual de OddsPortal
                
                # Intentamos buscar los nombres de equipos específicamente
                participantes = fila.select("a[class*='participant-name']")
                if len(participantes) < 2: continue
                
                equipo1 = participantes[0].text.strip()
                equipo2 = participantes[1].text.strip()
                
                # Buscamos cuotas (suelen estar en divs con clase 'odds')
                cuotas = fila.select("div[class*='odds-height']")
                c1 = "-"
                c2 = "-"
                
                if len(cuotas) >= 2:
                    c1 = cuotas[0].text.strip()
                    c2 = cuotas[1].text.strip()
                
                # Link del partido
                link_elem = fila.select_one("a[href^='/esports/']")
                link = "https://www.oddsportal.com" + link_elem['href'] if link_elem else TARGET_URL
                
                # Hora (Suele ser el primer texto)
                hora = textos[0] if textos else "Hoy"

                # Filtro simple: Si no hay cuotas, pasamos
                if c1 == "-" or c2 == "-": continue

                partidos_encontrados.append({
                    "torneo": "eSports General", # Difícil de sacar preciso sin lógica compleja
                    "hora": hora,
                    "equipo1": equipo1,
                    "equipo2": equipo2,
                    "cuota1": c1,
                    "cuota2": c2,
                    "link": link
                })
                
            except Exception as e:
                # Si falla una fila, seguimos con la otra
                continue

        print(f"✅ Extracción finalizada: {len(partidos_encontrados)} partidos válidos.")
        enviar_discord(partidos_encontrados)

    except Exception as e:
        print(f"❌ Error durante el scraping: {e}")
        # Tomar captura de pantalla para debug (opcional, se guarda en el servidor)
        # driver.save_screenshot("error_screenshot.png")
    finally:
        driver.quit()
        print("--- 🏁 DRIVER CERRADO ---")

if __name__ == "__main__":
    scrapear_oddsportal()