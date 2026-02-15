import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
REGIONS = 'us,eu,uk,au' # Buscamos en todo el mundo para encontrar tus casas
MARKETS = 'h2h'

# --- TUS CASAS FAVORITAS (EN ORDEN DE PRIORIDAD) ---
# El bot buscará estas. Si no encuentra ninguna de estas en un partido,
# usará cualquier otra disponible como respaldo (o puedes cambiar eso).
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

# Títulos bonitos para Discord
NOMBRES_TORNEOS = {
    'soccer_chile_campeonato': '🇨🇱 Chile - Primera División',
    'soccer_uefa_champs_league': '🇪🇺 UEFA Champions League',
    'esports_csgo': 'Counter Strike 2',
    'esports_valorant': 'Valorant',
    'esports_league_of_legends': 'League of Legends',
    'esports_rocket_league': 'Rocket League'
}

SPORTS = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league',
    'esports_csgo',
    'esports_valorant',
    'esports_league_of_legends'
]

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
            "footer": {"text": "📊 Bot de Apuestas | Prioridad: VIP"}
        }]
    }
    requests.post(WEBHOOK_URL, json=mensaje)

def buscar_apuestas():
    print("--- 🔄 INICIANDO BÚSQUEDA VIP ---")
    
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

            for evento in data[:10]:
                titulo_partido = f"{evento['home_team']} 🆚 {evento['away_team']}"
                
                # --- LÓGICA DE FILTRO VIP ---
                casa_seleccionada = None
                
                # 1. Primero buscamos si está alguna de tus favoritas
                mis_bookies = {b['title']: b for b in evento['bookmakers']}
                
                for vip in CASAS_VIP:
                    if vip in mis_bookies:
                        casa_seleccionada = mis_bookies[vip]
                        break # ¡Encontramos una favorita! Dejamos de buscar
                
                # 2. Si NO encontramos ninguna VIP, ¿usamos otra o saltamos?
                # AHORA: Usamos la primera que haya como respaldo.
                # Si quieres que SOLO muestre VIPs, cambia la linea de abajo a: if not casa_seleccionada: continue
                if not casa_seleccionada and evento['bookmakers']:
                    casa_seleccionada = evento['bookmakers'][0] 
                
                if casa_seleccionada:
                    nombre = casa_seleccionada['title']
                    link = obtener_link(nombre)
                    mercado = casa_seleccionada['markets'][0]['outcomes']
                    
                    c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                    c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                    c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), '-')

                    detalle = (f"Local: **{c_local}** | Empate: {c_empate} | Visita: **{c_visita}**\n"
                               f"🔗 Vía: {link}")
                else:
                    detalle = "Cuotas no disponibles."

                lista_campos_discord.append({
                    "name": titulo_partido,
                    "value": detalle,
                    "inline": False
                })

            nombre_bonito = NOMBRES_TORNEOS.get(sport, sport)
            enviar_resumen_discord(nombre_bonito, lista_campos_discord, color_embed)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    buscar_apuestas()