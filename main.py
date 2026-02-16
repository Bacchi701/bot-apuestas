import requests
import os
from datetime import datetime
import pytz # Librería para la hora de Chile

# --- CONFIGURACIÓN ---
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
REGIONS = 'us,eu,uk,au'
MARKETS = 'h2h'

CASAS_VIP = [
    'Coolbet', 
    'Betano',
    'GGBET',
    '1xBet',  
    'bet365',
    'Pinnacle' # Agrego Pinnacle porque suele tener buenas cuotas referencia
]

# Diccionario de enlaces
LINKS_CASAS = {
    'Coolbet': 'https://www.coolbetchile.com/cl/deportes/recommendations',
    'Betano': 'https://www.betano.com/',
    'GGBET': 'https://gg.bet/es-es',
    '1xBet': 'https://cl.1xbet.com/',
    'bet365': 'https://www.bet365.com/',
    'Pinnacle': 'https://www.pinnacle.com/'
}

# TÍTULOS BONITOS
NOMBRES_TORNEOS = {
    'soccer_chile_campeonato': '🇨🇱 Chile - Primera División',
    'soccer_uefa_champs_league': '🇪🇺 UEFA Champions League',
    'esports_csgo': 'Counter Strike 2',
    'esports_valorant': 'Valorant',
    'esports_league_of_legends': 'League of Legends',
    'esports_rocket_league': 'Rocket League'
}

# DEPORTES A BUSCAR
SPORTS = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league',
    'esports_csgo',
    'esports_valorant',
    'esports_league_of_legends'
]

# --- FUNCIONES ---

def formatear_hora_chile(fecha_iso):
    """Convierte la hora UTC de la API a Hora Chile"""
    try:
        fecha_utc = datetime.strptime(fecha_iso, "%Y-%m-%dT%H:%M:%SZ")
        fecha_utc = fecha_utc.replace(tzinfo=pytz.utc)
        
        tz_chile = pytz.timezone('America/Santiago')
        fecha_chile = fecha_utc.astimezone(tz_chile)
        
        dias = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
        dia_str = dias[fecha_chile.weekday()]
        return f"{dia_str} {fecha_chile.strftime('%H:%M')}"
    except:
        return "Hora desconocida"

def obtener_link(nombre_casa):
    url = LINKS_CASAS.get(nombre_casa)
    if url:
        return f"[{nombre_casa}]({url})"
    return nombre_casa

def enviar_resumen_discord(titulo, partidos, color):
    if not partidos: return

    mensaje = {
        "embeds": [{
            "title": titulo,
            "color": color,
            "fields": partidos,
            "footer": {"text": "📊 Bot de Apuestas | Hora CLT"}
        }]
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def buscar_apuestas():
    print("--- 🔄 INICIANDO BÚSQUEDA SIN FILTROS ---")
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal'
        
        try:
            response = requests.get(url)
            if response.status_code != 200: continue
            data = response.json()
            if not data: continue

            lista_campos_discord = []
            
            # Color según deporte
            color_embed = 5763719
            if "esports" in sport: color_embed = 10181046
            if "chile" in sport: color_embed = 13632027

            # Procesamos TODOS los eventos (límite 15 para no saturar un solo mensaje)
            for evento in data[:15]:
                titulo_partido = f"{evento['home_team']} 🆚 {evento['away_team']}"
                hora_partido = formatear_hora_chile(evento['commence_time'])
                
                # --- SELECCIÓN DE CASA ---
                mis_bookies = {b['title']: b for b in evento['bookmakers']}
                casa_seleccionada = None
                
                # Buscamos VIP
                for vip in CASAS_VIP:
                    if vip in mis_bookies:
                        casa_seleccionada = mis_bookies[vip]
                        break
                
                # Si no hay VIP, usamos la primera que exista
                if not casa_seleccionada and evento['bookmakers']:
                    casa_seleccionada = evento['bookmakers'][0]
                
                if casa_seleccionada:
                    nombre = casa_seleccionada['title']
                    link = obtener_link(nombre)
                    mercado = casa_seleccionada['markets'][0]['outcomes']
                    
                    c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                    c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                    c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), '-')

                    detalle = (f"Horario: {hora_partido}\n"
                               f"Local **{c_local}** | Empate: {c_empate} | Visita: **{c_visita}**\n"
                               f"🔗 Vía: {link}")
                else:
                    detalle = f"🕒 {hora_partido}\nCuotas no disponibles aún."

                lista_campos_discord.append({
                    "name": titulo_partido,
                    "value": detalle,
                    "inline": False
                })

            nombre_bonito = NOMBRES_TORNEOS.get(sport, sport)
            enviar_resumen_discord(nombre_bonito, lista_campos_discord, color_embed)

        except Exception as e:
            print(f"Error en {sport}: {e}")

if __name__ == "__main__":
    buscar_apuestas()