import requests
import os
from datetime import datetime
import pytz
from collections import defaultdict

# --- TUS SECRETOS ---
DISCORD_WEBHOOK = os.environ['DISCORD_WEBHOOK']
ODDS_API_KEY = os.environ['ODDS_API_KEY']
PANDASCORE_KEY = os.environ.get('PANDASCORE_KEY')

# --- CONFIGURACIÓN DE CASAS FAVORITAS (Whitelisting) ---
# El bot buscará cuotas en este orden de prioridad
BOOKIES_VIP = ['coolbet', 'betano', '1xbet', 'ggbet', 'bet365', 'betsson']

# Diccionario de enlaces directos para los eSports
LINKS_RAPIDOS = {
    'Coolbet': 'https://www.coolbet.com/cl/deportes/esports',
    'Betano': 'https://www.betano.com/sport/esports/',
    '1xBet': 'https://cl.1xbet.com/line/esports',
    'GGBet': 'https://gg.bet/es/esports',
    'bet365': 'https://www.bet365.com/#/AS/B151/'
}

# --- CONFIGURACIÓN DE LIGAS FÚTBOL ---
CONFIG_FUTBOL = {
    'soccer_chile_campeonato': {'titulo': '🇨🇱 Chile - Primera División', 'color': 13632027},
    'soccer_argentina_primera_division': {'titulo': '🇦🇷 Argentina - Liga Profesional', 'color': 7506394},
    'soccer_brazil_campeonato': {'titulo': '🇧🇷 Brasil - Brasileirao', 'color': 48340},
    'soccer_uefa_champs_league': {'titulo': '🇪🇺 UEFA Champions League', 'color': 3092790}
}

# --- CONFIGURACIÓN DE JUEGOS ESPORTS ---
CONFIG_ESPORTS = {
    'valorant': {'titulo': '✨ VALORANT', 'color': 16724530},
    'csgo': {'titulo': '🔫 COUNTER STRIKE 2', 'color': 15844367},
    'league-of-legends': {'titulo': '🛡️ LEAGUE OF LEGENDS', 'color': 3447003},
    'rocket-league': {'titulo': '🚗 ROCKET LEAGUE', 'color': 3066993}
}

def obtener_hora_chile(fecha_iso):
    try:
        # Limpieza y conversión a Hora Chile
        fecha_limpia = fecha_iso.replace("Z", "+00:00")
        if "+" not in fecha_limpia: fecha_limpia += "+00:00"
        fecha_dt = datetime.fromisoformat(fecha_limpia)
        tz_chile = pytz.timezone('America/Santiago')
        return fecha_dt.astimezone(tz_chile).strftime("%H:%M") # Solo hora
    except:
        return "--:--"

def enviar_embed_agrupado(titulo, color, lista_partidos, footer_text):
    if not lista_partidos: return

    # Creamos un solo Embed con todos los partidos de esa liga
    embed = {
        "embeds": [{
            "title": titulo,
            "color": color,
            "fields": lista_partidos,
            "footer": {"text": footer_text}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=embed)
    except Exception as e:
        print(f"Error enviando Discord: {e}")

def procesar_futbol():
    print("--- ⚽ ANALIZANDO FÚTBOL ---")
    
    # URL base de Odds API
    base_url = "https://api.the-odds-api.com/v4/sports/{}/odds/?apiKey={}&regions=us,eu,uk,au&markets=h2h&oddsFormat=decimal"

    for liga_key, config in CONFIG_FUTBOL.items():
        try:
            url = base_url.format(liga_key, ODDS_API_KEY)
            res = requests.get(url)
            if res.status_code != 200: continue
            
            data = res.json()
            campos_liga = [] # Aquí juntaremos los partidos de ESTA liga
            
            for evento in data[:8]: # Top 8 partidos próximos
                equipos = f"{evento['home_team']} 🆚 {evento['away_team']}"
                hora = obtener_hora_chile(evento['commence_time'])
                
                # --- BUSCADOR DE CUOTAS VIP ---
                cuota_info = "⚠️ Cuotas no publicadas aún"
                bookie_encontrada = None
                
                if evento['bookmakers']:
                    # Mapeamos las bookies disponibles en el evento
                    disponibles = {b['title'].lower(): b for b in evento['bookmakers']}
                    
                    # Buscamos en orden de tu lista VIP
                    for vip in BOOKIES_VIP:
                        # Buscamos coincidencias parciales (ej: 'bet365' en 'bet365 (US)')
                        for key_api in disponibles:
                            if vip in key_api:
                                bookie_encontrada = disponibles[key_api]
                                break
                        if bookie_encontrada: break
                    
                    # Si no encontramos ninguna VIP, usamos la primera que haya (Respaldo)
                    if not bookie_encontrada:
                        bookie_encontrada = evento['bookmakers'][0]

                    # Formateamos la cuota
                    if bookie_encontrada:
                        mercado = bookie_encontrada['markets'][0]['outcomes']
                        c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                        c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                        c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), '-')
                        
                        cuota_info = f"🏠 **{c_local}** | 🤝 {c_empate} | ✈️ **{c_visita}**\n🏦 *{bookie_encontrada['title']}*"

                campos_liga.append({
                    "name": f"⏰ {hora} | {equipos}",
                    "value": cuota_info,
                    "inline": False
                })

            # Enviamos el paquete de esta liga
            if campos_liga:
                enviar_embed_agrupado(config['titulo'], config['color'], campos_liga, "⚽ Odds API | Hora Chile")
                
        except Exception as e:
            print(f"Error en {liga_key}: {e}")

def procesar_esports():
    print("--- 🎮 ANALIZANDO ESPORTS ---")
    if not PANDASCORE_KEY: return

    base_url = "https://api.pandascore.co/{}/matches/upcoming?sort=begin_at&token={}&page[size]=5"

    for juego_key, config in CONFIG_ESPORTS.items():
        try:
            url = base_url.format(juego_key, PANDASCORE_KEY)
            res = requests.get(url)
            if res.status_code != 200: continue
            
            matches = res.json()
            campos_juego = []
            
            for m in matches:
                if len(m['opponents']) < 2: continue
                
                eq1 = m['opponents'][0]['opponent']['name']
                eq2 = m['opponents'][1]['opponent']['name']
                hora = obtener_hora_chile(m['begin_at'])
                torneo = m['league']['name']
                
                # Como PandaScore Free no da cuotas directas de Betano/Coolbet,
                # ponemos enlaces directos para apostar rápido.
                campos_juego.append({
                    "name": f"⏰ {hora} | {eq1} vs {eq2}",
                    "value": f"🏆 {torneo}\n🔗 [Coolbet]({LINKS_RAPIDOS['Coolbet']}) | [Betano]({LINKS_RAPIDOS['Betano']}) | [GGBet]({LINKS_RAPIDOS['GGBet']})",
                    "inline": False
                })
            
            if campos_juego:
                enviar_embed_agrupado(config['titulo'], config['color'], campos_juego, "👾 PandaScore Oficial | eSports")

        except Exception as e:
            print(f"Error en {juego_key}: {e}")

if __name__ == "__main__":
    procesar_futbol()
    procesar_esports()