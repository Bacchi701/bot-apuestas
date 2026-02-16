import requests
import os
from datetime import datetime
import pytz

# --- CONFIGURACIÓN DE SECRETOS ---
DISCORD_WEBHOOK = os.environ['DISCORD_WEBHOOK']
ODDS_API_KEY = os.environ['ODDS_API_KEY']
PANDASCORE_KEY = os.environ.get('PANDASCORE_KEY')

# --- CONFIGURACIÓN ---
# Usamos The Odds API para Fútbol (Funciona bien)
ODDS_URL = "https://api.the-odds-api.com/v4/sports/{}/odds/?apiKey={}&regions=us,eu,uk&markets=h2h&oddsFormat=decimal"
DEPORTES_FUTBOL = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league',
    'soccer_argentina_primera_division',
    'soccer_spain_la_liga'
]

# Usamos PandaScore para eSports (Funciona siempre)
PANDA_URL = "https://api.pandascore.co/{}/matches/upcoming?sort=begin_at&token={}"
DEPORTES_ESPORTS = [
    'valorant',
    'csgo', 
    'league-of-legends',
    'rocket-league'
]

def obtener_hora_chile(fecha_iso):
    try:
        # Limpieza de formato de fecha
        fecha_limpia = fecha_iso.replace("Z", "+00:00")
        if not "+" in fecha_limpia: fecha_limpia += "+00:00"
        
        fecha_dt = datetime.fromisoformat(fecha_limpia)
        tz_chile = pytz.timezone('America/Santiago')
        fecha_chile = fecha_dt.astimezone(tz_chile)
        return fecha_chile.strftime("%H:%M")
    except Exception as e:
        return "Pronto"

def enviar_discord(titulo, color, campos):
    if not campos: return
    
    # Bloques de 10 para no saturar
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
        try:
            requests.post(DISCORD_WEBHOOK, json=embed)
        except:
            pass

def procesar_futbol():
    print("--- ⚽ BUSCANDO FÚTBOL (THE ODDS API) ---")
    campos = []
    
    for deporte in DEPORTES_FUTBOL:
        try:
            url = ODDS_URL.format(deporte, ODDS_API_KEY)
            res = requests.get(url)
            if res.status_code != 200: continue
            
            data = res.json()
            for evento in data[:5]:
                equipos = f"{evento['home_team']} vs {evento['away_team']}"
                hora = obtener_hora_chile(evento['commence_time'])
                
                cuotas_txt = "Cuotas no disponibles"
                if evento['bookmakers']:
                    casa = evento['bookmakers'][0]
                    mercado = casa['markets'][0]['outcomes']
                    c1 = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                    c2 = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                    cuotas_txt = f"🏠 {c1} | ✈️ {c2} ({casa['title']})"

                campos.append({
                    "name": f"⏰ {hora} | {deporte.replace('soccer_','').title()}",
                    "value": f"**{equipos}**\n{cuotas_txt}",
                    "inline": False
                })
        except Exception as e:
            print(f"Error fútbol: {e}")
            
    enviar_discord("⚽ Alertas de Fútbol", 5763719, campos)

def procesar_esports():
    print("--- 🎮 BUSCANDO ESPORTS (PANDASCORE) ---")
    if not PANDASCORE_KEY:
        print("⚠️ Falta PANDASCORE_KEY en Secrets.")
        return

    campos = []
    for juego in DEPORTES_ESPORTS:
        try:
            url = PANDA_URL.format(juego, PANDASCORE_KEY) + "&page[size]=5"
            res = requests.get(url)
            
            if res.status_code != 200:
                print(f"Error PandaScore {juego}: {res.status_code}")
                continue
                
            match_data = res.json()
            
            for match in match_data:
                if not match['opponents']: continue
                
                eq1 = match['opponents'][0]['opponent']['name']
                eq2 = match['opponents'][1]['opponent']['name']
                hora = obtener_hora_chile(match['begin_at'])
                torneo = match['league']['name']
                
                campos.append({
                    "name": f"⏰ {hora} | {juego.upper()}",
                    "value": f"🎮 **{eq1} vs {eq2}**\n🏆 {torneo}",
                    "inline": False
                })
                
        except Exception as e:
            print(f"Error eSports {juego}: {e}")

    enviar_discord("👾 Alertas de eSports (Oficial)", 10181046, campos)

if __name__ == "__main__":
    procesar_futbol()
    procesar_esports()