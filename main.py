import requests
import os
import json

# --- CONFIGURACIÓN ---
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
REGIONS = 'us,eu,uk,au' # Regiones de búsqueda
MARKETS = 'h2h' 

# LISTA TEMPORAL (Solo lo seguro por ahora)
# Dejamos solo fútbol chileno y Champions para que el bot NO falle mientras exploramos.
SPORTS = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league'
]

def enviar_discord(partido, casa, cuota_local, cuota_empate, cuota_visita, deporte):
    # Detectamos si es eSport para poner un emoji diferente
    emoji = "🎮" if "esports" in deporte else "⚽"
    
    mensaje = {
        "embeds": [{
            "title": f"{emoji} {partido}",
            "color": 5763719,
            "fields": [
                {"name": "Torneo", "value": deporte, "inline": False},
                {"name": "Casa", "value": casa, "inline": True},
                {"name": "Local (1)", "value": str(cuota_local), "inline": True},
                {"name": "Visita (2)", "value": str(cuota_visita), "inline": True},
                {"name": "Empate (X)", "value": str(cuota_empate), "inline": True}
            ],
            "footer": {"text": "Bot de Apuestas - v2.0"}
        }]
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def explorar_deportes():
    """Función para descubrir las llaves correctas de eSports"""
    print("--- 🔍 MODO EXPLORADOR: Buscando deportes activos ---")
    url = f'https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            todos_los_deportes = response.json()
            print("Deportes eSports encontrados hoy:")
            encontrados = False
            for d in todos_los_deportes:
                # Filtramos solo los que dicen "esports" o juegos conocidos
                key = d['key']
                if 'esports' in key or 'league' in key or 'csgo' in key:
                    print(f"👉 NOMBRE: {d['title']} | LLAVE: {key}")
                    encontrados = True
            
            if not encontrados:
                print("⚠️ No se encontraron torneos de eSports activos hoy en la API.")
        else:
            print(f"Error al explorar deportes: {response.text}")
    except Exception as e:
        print(f"Error crítico explorando: {str(e)}")
    print("---------------------------------------------------")

def buscar_apuestas():
    # 1. Primero ejecutamos el explorador para ver los nombres en el LOG
    explorar_deportes()

    # 2. Luego buscamos las apuestas de la lista SPORTS definida arriba
    print("Iniciando búsqueda de cuotas...")
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal'
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error en API para {sport}: {response.text}")
            continue

        data = response.json()
        
        if not data:
            continue
            
        print(f"✅ {sport}: {len(data)} eventos.")

        for evento in data[:5]: 
            teams = f"{evento['home_team']} vs {evento['away_team']}"
            
            for bookmaker in evento['bookmakers']:
                nombre_casa = bookmaker['title']
                
                # FILTRO: Si quieres solo Coolbet o Betsson, descomenta esto:
                # if nombre_casa not in ['Coolbet', 'Betsson', '1xBet']: continue

                mercado = bookmaker['markets'][0]['outcomes']
                c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), 0)
                c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), 0)
                c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), 0)

                # Notificar siempre por ahora para probar
                enviar_discord(teams, nombre_casa, c_local, c_empate, c_visita, sport)
                break 

if __name__ == "__main__":
    buscar_apuestas()