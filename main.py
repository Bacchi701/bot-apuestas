import requests
import os
from datetime import datetime
import pytz

# --- TUS SECRETOS ---
DISCORD_WEBHOOK = os.environ['DISCORD_WEBHOOK']
ODDS_API_KEY = os.environ['ODDS_API_KEY']
PANDASCORE_KEY = os.environ.get('PANDASCORE_KEY')

# --- CONFIGURACIÓN DE PRIORIDAD ---
BOOKIES_VIP = ['coolbet', 'betano', '1xbet', 'ggbet', 'bet365']

# --- ENLACES DIRECTOS (Diccionario Maestro) ---
LINKS_MAESTROS = {
    'coolbet': 'https://www.coolbet.com/cl/deportes',
    'betano': 'https://www.betano.com/',
    '1xbet': 'https://cl.1xbet.com/',
    'ggbet': 'https://gg.bet/es/sports',
    'bet365': 'https://www.bet365.com/'
}

# Configuración Ligas Fútbol
CONFIG_FUTBOL = {
    'soccer_chile_campeonato': {'titulo': '🇨🇱 Chile - Primera División', 'color': 13632027},
    'soccer_argentina_primera_division': {'titulo': '🇦🇷 Argentina - Liga Profesional', 'color': 7506394},
    'soccer_brazil_campeonato': {'titulo': '🇧🇷 Brasil - Brasileirao', 'color': 48340},
    'soccer_uefa_champs_league': {'titulo': '🇪🇺 UEFA Champions League', 'color': 3092790},
    'soccer_spain_la_liga': {'titulo': '🇪🇸 España - La Liga', 'color': 16761095}
}

# Configuración eSports
CONFIG_ESPORTS = {
    'valorant': {'titulo': '✨ VALORANT', 'color': 16724530},
    'csgo': {'titulo': '🔫 COUNTER STRIKE 2', 'color': 15844367},
    'league-of-legends': {'titulo': '🛡️ LEAGUE OF LEGENDS', 'color': 3447003},
    'rocket-league': {'titulo': '🚗 ROCKET LEAGUE', 'color': 3066993}
}

def obtener_fecha_chile(fecha_iso):
    """Convierte fecha a formato: Lun 12/02 14:30"""
    try:
        fecha_limpia = fecha_iso.replace("Z", "+00:00")
        if "+" not in fecha_limpia: fecha_limpia += "+00:00"
        
        fecha_dt = datetime.fromisoformat(fecha_limpia)
        tz_chile = pytz.timezone('America/Santiago')
        fecha_cl = fecha_dt.astimezone(tz_chile)
        
        dias = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
        dia_nombre = dias[fecha_cl.weekday()]
        
        return f"{dia_nombre} {fecha_cl.day}/{fecha_cl.month} {fecha_cl.strftime('%H:%M')}"
    except:
        return "Fecha desconocida"

def obtener_link_casa(nombre_casa):
    """Devuelve el nombre con link si existe en nuestro diccionario"""
    key = nombre_casa.lower()
    # Buscamos coincidencias parciales (ej: 'bet365' dentro de 'bet365 (us)')
    for k, url in LINKS_MAESTROS.items():
        if k in key:
            return f"[{nombre_casa}]({url})"
    return nombre_casa # Si no hay link, devuelve solo texto

def enviar_embed_agrupado(titulo, color, lista_partidos, footer_text):
    if not lista_partidos: return
    
    # Discord tiene limite de 25 campos por embed. Si hay más, cortamos en 25.
    embed = {
        "embeds": [{
            "title": titulo,
            "color": color,
            "fields": lista_partidos[:25], 
            "footer": {"text": footer_text}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=embed)
    except:
        pass

def procesar_futbol():
    print("--- ⚽ FÚTBOL ---")
    base_url = "https://api.the-odds-api.com/v4/sports/{}/odds/?apiKey={}&regions=us,eu,uk,au&markets=h2h&oddsFormat=decimal"

    for liga_key, config in CONFIG_FUTBOL.items():
        try:
            url = base_url.format(liga_key, ODDS_API_KEY)
            res = requests.get(url)
            if res.status_code != 200: continue
            
            data = res.json()
            campos_liga = []
            
            for evento in data[:8]:
                equipos = f"{evento['home_team']} 🆚 {evento['away_team']}"
                fecha_str = obtener_fecha_chile(evento['commence_time'])
                
                # BUSCADOR DE CUOTAS
                cuota_info = "⚠️ Cuotas pendientes"
                bookie_obj = None
                
                if evento['bookmakers']:
                    # Mapa de casas disponibles
                    disponibles = {b['title'].lower(): b for b in evento['bookmakers']}
                    
                    # 1. Buscar VIP
                    for vip in BOOKIES_VIP:
                        for k in disponibles:
                            if vip in k:
                                bookie_obj = disponibles[k]
                                break
                        if bookie_obj: break
                    
                    # 2. Respaldo
                    if not bookie_obj: bookie_obj = evento['bookmakers'][0]

                    if bookie_obj:
                        mercado = bookie_obj['markets'][0]['outcomes']
                        c1 = next((x['price'] for x in mercado if x['name'] == evento['home_team']), '-')
                        c2 = next((x['price'] for x in mercado if x['name'] == evento['away_team']), '-')
                        empate = next((x['price'] for x in mercado if x['name'] == 'Draw'), '-')
                        
                        # AQUÍ LA MAGIA: Convertimos el nombre en LINK
                        nombre_con_link = obtener_link_casa(bookie_obj['title'])
                        
                        cuota_info = f"Local: **{c1}** | Empate: {empate} | Visita: **{c2}**\n🔗 Vía: {nombre_con_link}"

                campos_liga.append({
                    "name": f"🗓️ {fecha_str} | {equipos}",
                    "value": cuota_info,
                    "inline": False
                })

            if campos_liga:
                enviar_embed_agrupado(config['titulo'], config['color'], campos_liga, "Bot Híbrido v5.0")
                
        except Exception as e:
            print(f"Error liga {liga_key}: {e}")

def procesar_esports():
    print("--- 🎮 ESPORTS ---")
    if not PANDASCORE_KEY: return

    base_url = "https://api.pandascore.co/{}/matches/upcoming?sort=begin_at&token={}&page[size]=5"
    
    # Link genérico para eSports
    link_esports = f"[Coolbet]({LINKS_MAESTROS['coolbet']}) | [Betano]({LINKS_MAESTROS['betano']}) | [GGBet]({LINKS_MAESTROS['ggbet']})"

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
                fecha_str = obtener_fecha_chile(m['begin_at'])
                torneo = m['league']['name']
                
                campos_juego.append({
                    "name": f"🗓️ {fecha_str} | {eq1} vs {eq2}",
                    "value": f"🏆 {torneo}\n🔗 {link_esports}",
                    "inline": False
                })
            
            if campos_juego:
                enviar_embed_agrupado(config['titulo'], config['color'], campos_juego, "Bot Híbrido v5.0")

        except Exception as e:
            print(f"Error juego {juego_key}: {e}")

if __name__ == "__main__":
    procesar_futbol()
    procesar_esports()