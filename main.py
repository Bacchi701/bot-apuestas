import requests
import os
from datetime import datetime
import pytz

# --- CONFIGURACIÓN DE SECRETOS ---
DISCORD_WEBHOOK = os.environ['DISCORD_WEBHOOK']
ODDS_API_KEY = os.environ['ODDS_API_KEY']
PANDASCORE_KEY = os.environ.get('PANDASCORE_KEY') # Usamos .get por si se te olvida ponerla

# --- CONFIGURACIÓN DE APUESTAS (FÚTBOL) ---
ODDS_URL = "https://api.the-odds-api.com/v4/sports/{}/odds/?apiKey={}&regions=us,eu,uk&markets=h2h&oddsFormat=decimal"
DEPORTES_FUTBOL = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league',
    'soccer_argentina_primera_division',
    'soccer_spain_la_liga'
]

# --- CONFIGURACIÓN DE ESPORTS (PANDASCORE) ---
# PandaScore cubre: csgo, dota2, lol, valorant, overwatch, rocket-league
PANDA_URL = "https://api.pandascore.co/{}/matches/upcoming?sort=begin_at&token={}"
DEPORTES_ESPORTS = [
    'valorant',
    'csgo', # Counter Strike 2
    'league-of-legends',
    'rocket-league'
]

def obtener_hora_chile(fecha_iso):
    try:
        # Intentamos parsear formato ISO estándar
        if 'T' in fecha_iso:
            fecha_dt = datetime.strptime(fecha_iso.split('+')[0], "%Y-%m-%dT%H:%M:%SZ")
        else:
            fecha_dt = datetime.strptime(fecha_iso, "%Y-%m-%d %H:%M:%S")
            
        fecha_dt = fecha_dt.replace(tzinfo=pytz.utc)
        tz_chile = pytz.timezone('America/Santiago')
        fecha_chile = fecha_dt.astimezone(tz_chile)
        return fecha_chile.strftime("%H:%M")
    except:
        return "Pronto"

def enviar_discord(titulo, color, campos):
    if not campos: return
    
    # Enviamos en bloques para no romper Discord
    chunks = [campos[i:i+10] for i in range(0, len(campos), 10)]
    
    for chunk in chunks:
        embed = {
            "embeds": [{
                "title": titulo,
                "color": color,
                "fields": chunk,
                "footer": {"text": "Bot Híbrido: OddsAPI + PandaScore"}
            }]
        }
        requests.post(DISCORD_WEBHOOK, json=embed)

def procesar_futbol():
    print("--- ⚽ BUSCANDO FÚTBOL (THE ODDS API) ---")
    campos = []
    
    for deporte in DEPORTES_FUTBOL:
        try:
            url = ODDS_URL.format(deporte, ODDS_API_KEY)
            res = requests.get(url)
            if res.status_code != 200: continue
            
            data = res.json()
            for evento in data[:5]: # Top 5 por liga
                equipos = f"{evento['home_team']} vs {evento['away_team']}"
                hora = obtener_hora_chile(evento['commence_time'])
                
                # Buscamos cuotas
                cuotas_txt = "Cuotas no disponibles"
                if evento['bookmakers']:
                    # Prioridad a casas conocidas
                    casa = evento['bookmakers'][0]
                    for b in evento['bookmakers']:
                        if b['title'] in ['Coolbet', 'Betano', 'Bet365', '1xBet']:
                            casa = b
                            break
                    
                    mercado = casa['markets'][0]['outcomes']
                    c1 = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                    c2 = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                    cuotas_txt = f"🏠 {c1} | ✈️ {c2} ({casa['title']})"

                campos.append({
                    "name": f"⏰ {hora} | {deporte.replace('soccer_','').replace('_',' ').title()}",
                    "value": f"**{equipos}**\n{cuotas_txt}",
                    "inline": False
                })
        except Exception as e:
            print(f"Error en fútbol: {e}")
            
    enviar_discord("⚽ Alertas de Fútbol", 5763719, campos)

def procesar_esports():
    print("--- 🎮 BUSCANDO ESPORTS (PANDASCORE) ---")
    if not PANDASCORE_KEY:
        print("⚠️ Falta la PANDASCORE_KEY en GitHub Secrets.")
        return

    campos = []
    for juego in DEPORTES_ESPORTS:
        try:
            # Pedimos los próximos 5 partidos de cada juego
            url = PANDA_URL.format(juego, PANDASCORE_KEY) + "&page[size]=5"
            res = requests.get(url)
            
            if res.status_code != 200:
                print(f"Error PandaScore {juego}: {res.status_code}")
                continue
                
            match_data = res.json()
            
            for match in match_data:
                if not match['opponents']: continue # Si no hay equipos definidos, saltar
                
                eq1 = match['opponents'][0]['opponent']['name']
                eq2 = match['opponents'][1]['opponent']['name']
                hora = obtener_hora_chile(match['begin_at'])
                torneo = match['league']['name']
                
                # PandaScore Free no siempre da cuotas, pero avisamos del partido
                detalle = f"🏆 {torneo}\n⚠️ Revisar casas para cuotas"
                
                campos.append({
                    "name": f"⏰ {hora} | {juego.upper()}",
                    "value": f"🎮 **{eq1} vs {eq2}**\n{detalle}",
                    "inline": False
                })
                
        except Exception as e:
            print(f"Error en eSports {juego}: {e}")

    enviar_discord("👾 Alertas de eSports (Oficial)", 10181046, campos)

if __name__ == "__main__":
    procesar_futbol()
    procesar_esports()