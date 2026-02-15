import requests
import os
import json

# --- CONFIGURACIÓN ---
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']

# Usamos todas las regiones para intentar encontrar a Betano
REGIONS = 'us,eu,uk,au' 
MARKETS = 'h2h' 

# LISTA MAESTRA DE DEPORTES
# Aunque hoy no funcionen, dejamos las llaves listas para cuando activen los torneos.
SPORTS = [
    'soccer_chile_campeonato',      # Chile Primera
    'soccer_uefa_champs_league',    # Champions
    'esports_csgo',                 # Counter Strike 2 (Suele usar esta key)
    'esports_league_of_legends',    # LoL
    'esports_valorant',             # Valorant
    'esports_rocket_league',        # Rocket League
    'esports_dota_2'                # Dota 2 (Por si acaso)
]

def enviar_discord(partido, casa, cuota_local, cuota_empate, cuota_visita, deporte):
    # Diferenciamos con emojis
    if "soccer" in deporte:
        emoji = "⚽"
    elif "csgo" in deporte:
        emoji = "🔫 CS2"
    elif "valorant" in deporte:
        emoji = "✨ VAL"
    elif "league" in deporte and "legends" in deporte:
        emoji = "🛡️ LOL"
    else:
        emoji = "🎮"
    
    embed_color = 5763719 # Verde básico
    
    # Destacar si es una cuota alta (mayor a 2.5)
    try:
        if float(cuota_local) > 2.5 or float(cuota_visita) > 2.5:
            embed_color = 15158332 # Rojo llamativo
    except:
        pass

    mensaje = {
        "embeds": [{
            "title": f"{emoji} {partido}",
            "color": embed_color,
            "fields": [
                {"name": "Torneo", "value": deporte, "inline": False},
                {"name": "Casa de Apuesta", "value": casa, "inline": True},
                {"name": "Local (1)", "value": str(cuota_local), "inline": True},
                {"name": "Visita (2)", "value": str(cuota_visita), "inline": True},
                {"name": "Empate (X)", "value": str(cuota_empate), "inline": True}
            ],
            "footer": {"text": "Bot de Apuestas - Vigilando 24/7"}
        }]
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def buscar_apuestas():
    print("--- 🤖 INICIANDO BARRIDO DE APUESTAS ---")
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal'
        response = requests.get(url)
        
        if response.status_code != 200:
            # Si da error, solo lo registramos y seguimos con el siguiente deporte
            # (Es normal que los eSports den error si no hay torneo activo)
            print(f"⚠️ {sport}: No disponible o inactivo por ahora.")
            continue

        data = response.json()
        
        if not data:
            print(f"ℹ️ {sport}: Activo, pero sin partidos hoy.")
            continue
            
        print(f"✅ {sport}: ¡{len(data)} eventos encontrados!")

        # Procesamos los eventos
        for evento in data: # Quitamos el límite para que revise TODO
            teams = f"{evento['home_team']} vs {evento['away_team']}"
            
            # Buscamos la mejor cuota disponible
            for bookmaker in evento['bookmakers']:
                nombre_casa = bookmaker['title']
                
                # FILTRO DE CASAS DE APUESTAS
                # Si quieres reducir el spam, descomenta las líneas de abajo:
                # casas_interes = ['Coolbet', 'Betsson', 'Betano', '1xBet', 'Marathon Bet']
                # if nombre_casa not in casas_interes: continue

                mercado = bookmaker['markets'][0]['outcomes']
                
                # Obtener cuotas con seguridad (si no existen pone 0)
                c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), 0)
                c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), 0)
                c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), 0)

                # FILTRO DE VALOR
                # Solo notificar si alguna cuota vale la pena (ej: mayor a 1.6)
                if c_local > 1.6 or c_visita > 1.6:
                    enviar_discord(teams, nombre_casa, c_local, c_empate, c_visita, sport)
                    
                # Break para no repetir el mismo partido 20 veces con distintas casas
                # (Solo enviamos la primera casa que cumpla la condición)
                break 

if __name__ == "__main__":
    buscar_apuestas()