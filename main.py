import requests
import os
import json

# --- CONFIGURACIÓN ---
# Estas variables las guardaremos como "Secretos" en GitHub para seguridad
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']

# Deportes a buscar (Claves de The Odds API)
# 'soccer_chile_campeonato' = Primera División Chile
# 'soccer_uefa_champs_league' = Champions League
# 'esports_csgo' = CS:GO (Counter Strike 2 está aquí generalmente)
SPORTS = ['soccer_chile_campeonato', 'esports_csgo'] 

REGIONS = 'us,eu' # Casas de apuestas de US y Europa (cubre muchas internacionales)
MARKETS = 'h2h' # 'h2h' es Ganador del partido. 

def enviar_discord(partido, casa, cuota_local, cuota_empate, cuota_visita):
    mensaje = {
        "embeds": [{
            "title": f"⚽ {partido}",
            "color": 5763719, # Color verde
            "fields": [
                {"name": "Casa de Apuesta", "value": casa, "inline": True},
                {"name": "Local (1)", "value": str(cuota_local), "inline": True},
                {"name": "Visita (2)", "value": str(cuota_visita), "inline": True},
                {"name": "Empate (X)", "value": str(cuota_empate), "inline": True}
            ],
            "footer": {"text": "Bot de Apuestas - Actualizado"}
        }]
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def buscar_apuestas():
    print("Iniciando búsqueda...")
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal'
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error en API: {response.text}")
            continue

        data = response.json()
        
        # Recorremos los partidos encontrados
        for evento in data[:5]: # Limitamos a 5 partidos por deporte para no saturar Discord
            teams = f"{evento['home_team']} vs {evento['away_team']}"
            
            # Buscamos la mejor cuota (o la primera que aparezca)
            for bookmaker in evento['bookmakers']:
                # Aquí podrías filtrar: if bookmaker['key'] == 'coolbet':
                nombre_casa = bookmaker['title']
                mercado = bookmaker['markets'][0]['outcomes']
                
                # Extraemos las cuotas
                c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), "N/A")
                c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), "N/A")
                c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), "N/A")

                # FILTRO SIMPLE: Solo notificar si alguna cuota es jugosa (ejemplo > 2.0)
                # Puedes quitar este if para ver todo
                if c_local != "N/A" and (c_local > 1.5 or c_visita > 1.5):
                    enviar_discord(teams, nombre_casa, c_local, c_empate, c_visita)
                    break # Solo enviamos una casa de apuestas por partido para no hacer spam

if __name__ == "__main__":
    buscar_apuestas()