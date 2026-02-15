import requests
import os

# --- CONFIGURACIÓN ---
API_KEY = os.environ['ODDS_API_KEY']
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
REGIONS = 'us,eu,uk,au'
MARKETS = 'h2h'

# Diccionario para que los títulos se vean bonitos en Discord
NOMBRES_TORNEOS = {
    'soccer_chile_campeonato': '🇨🇱 Chile - Primera División',
    'soccer_uefa_champs_league': '🇪🇺 UEFA Champions League',
    'esports_csgo': '🔫 Counter Strike 2',
    'esports_valorant': '✨ Valorant',
    'esports_league_of_legends': '🛡️ League of Legends',
    'esports_rocket_league': '🚗 Rocket League'
}

# Diccionario de enlaces a las casas de apuestas (Puedes agregar más)
LINKS_CASAS = {
    'Coolbet': 'https://www.coolbet.com/cl/deportes',
    'Betano': 'https://www.betano.com/',
    'Betsson': 'https://www.betsson.com/cl',
    '1xBet': 'https://cl.1xbet.com/',
    'Marathon Bet': 'https://www.marathonbet.com/',
    'Unibet': 'https://www.unibet.com/',
    'Betway': 'https://betway.com/',
    'Pinnacle': 'https://www.pinnacle.com/',
    'Winamax': 'https://www.winamax.es/'
}

# Lista de deportes a buscar
SPORTS = [
    'soccer_chile_campeonato',
    'soccer_uefa_champs_league',
    'esports_csgo',
    'esports_valorant',
    'esports_league_of_legends'
]

def obtener_link(nombre_casa):
    # Si la casa está en nuestra lista, devolvemos el link formateado para Discord
    # Si no, devolvemos solo el nombre
    url = LINKS_CASAS.get(nombre_casa)
    if url:
        return f"[{nombre_casa}]({url})" # Formato Markdown de Discord: [Texto](URL)
    return nombre_casa

def enviar_resumen_discord(titulo, partidos, color):
    if not partidos:
        return

    # Estructura del Embed agrupado
    mensaje = {
        "embeds": [{
            "title": titulo,
            "color": color,
            "fields": partidos, # Aquí pegamos la lista de partidos procesados
            "footer": {"text": "📊 Bot de Apuestas | Cuotas pueden variar"}
        }]
    }
    
    try:
        requests.post(WEBHOOK_URL, json=mensaje)
    except Exception as e:
        print(f"Error enviando a Discord: {e}")

def buscar_apuestas():
    print("--- 🔄 INICIANDO RESUMEN DE APUESTAS ---")
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal'
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"⚠️ Salto {sport}: API respondió {response.status_code}")
                continue

            data = response.json()
            if not data:
                print(f"ℹ️ {sport}: Sin eventos hoy.")
                continue

            # --- PROCESAMIENTO AGRUPADO ---
            print(f"✅ Procesando {len(data)} partidos de {sport}...")
            
            lista_campos_discord = []
            
            # Definimos color según deporte
            color_embed = 5763719 # Verde default
            if "esports" in sport: color_embed = 10181046 # Morado gamer
            if "chile" in sport: color_embed = 13632027 # Rojo chileno

            # Recorremos los eventos (Máximo 10 para no romper el límite de Discord)
            for evento in data[:10]:
                titulo_partido = f"{evento['home_team']} 🆚 {evento['away_team']}"
                
                # Buscamos la mejor casa (o la primera disponible)
                mejor_opcion = "No disponible"
                
                if evento['bookmakers']:
                    bookie = evento['bookmakers'][0] # Tomamos la primera casa que nos da la API
                    nombre_casa = bookie['title']
                    link_casa = obtener_link(nombre_casa)
                    
                    mercado = bookie['markets'][0]['outcomes']
                    c_local = next((x['price'] for x in mercado if x['name'] == evento['home_team']), 0)
                    c_visita = next((x['price'] for x in mercado if x['name'] == evento['away_team']), 0)
                    c_empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), 0)
                    
                    # Formato del texto dentro del campo
                    detalle = (f"🏠 **{c_local}** | 🤝 {c_empate} | ✈️ **{c_visita}**\n"
                               f"🔗 Vía: {link_casa}")
                else:
                    detalle = "Cuotas no publicadas aún."

                # Agregamos este partido a la lista del torneo
                lista_campos_discord.append({
                    "name": titulo_partido,
                    "value": detalle,
                    "inline": False # False para que queden uno debajo del otro (lista)
                })

            # ENVIAR EL PAQUETE COMPLETO
            nombre_bonito = NOMBRES_TORNEOS.get(sport, sport.replace('_', ' ').title())
            enviar_resumen_discord(nombre_bonito, lista_campos_discord, color_embed)

        except Exception as e:
            print(f"❌ Error crítico en {sport}: {str(e)}")

if __name__ == "__main__":
    buscar_apuestas()