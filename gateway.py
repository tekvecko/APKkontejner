import os
import json
import logging
from flask import Flask, jsonify, request
from flask_sock import Sock
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)

COMPONENTS_DIR = 'components'
# Set pro udržení aktivních WS spojení pro broadcast
active_clients = set()

# --- ADMIN REST ENDPOINTY (Pro tvorbu a upload kontejnerů) ---

@app.route('/api/components', methods=['GET'])
def list_components():
    try:
        files = os.listdir(COMPONENTS_DIR)
        components = [f for f in files if f.endswith('.html') or f.endswith('.json')]
        return jsonify({"status": "success", "components": components})
    except Exception as e:
        logger.error(f"Chyba IO: {str(e)}")
        return jsonify({"status": "error", "message": "Nelze načíst komponenty"}), 500

@app.route('/api/components/<filename>', methods=['POST'])
def create_component(filename):
    safe_filename = secure_filename(filename)
    if not safe_filename:
        return jsonify({"status": "error", "message": "Neplatný název"}), 400
        
    filepath = os.path.join(COMPONENTS_DIR, safe_filename)
    content = request.get_data(as_text=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Komponenta zapsána: {filepath}")
        
        # Oznámení připojeným APK klientům, že mají aktualizovat UI
        broadcast_message({
            "command": "COMPONENT_UPDATED",
            "component_name": safe_filename,
            "action": "RELOAD"
        })
        
        return jsonify({"status": "success", "message": f"Uloženo: {safe_filename}"})
    except Exception as e:
        logger.error(f"Zápis selhal: {str(e)}")
        return jsonify({"status": "error", "message": "Chyba zápisu na disk"}), 500

# --- CLIENT REST ENDPOINTY (Pro stahování kontejnerů do APK WebView) ---

@app.route('/app-container/<filename>', methods=['GET'])
def serve_container(filename):
    safe_filename = secure_filename(filename)
    filepath = os.path.join(COMPONENTS_DIR, safe_filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>404 - Komponenta nenalezena</h1>", 404

# --- WEBSOCKET VRSTVA (Obousměrná komunikace) ---

def broadcast_message(message_dict):
    disconnected = set()
    message_json = json.dumps(message_dict)
    for client in active_clients:
        try:
            client.send(message_json)
        except Exception:
            disconnected.add(client)
    active_clients.difference_update(disconnected)

@sock.route('/ws/bridge')
def ws_bridge(ws):
    logger.info("Připojen nový APK klient.")
    active_clients.add(ws)
    try:
        while True:
            raw = ws.receive()
            if raw is None: break
            try:
                msg = json.loads(raw)
                logger.info(f"Klient hlásí: {msg.get('type')} - {msg.get('payload')}")
                if msg.get('type') == 'INIT':
                    ws.send(json.dumps({"command": "ACK", "status": "ready"}))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.error(f"WS chyba: {str(e)}")
    finally:
        active_clients.discard(ws)
        logger.info("Klient odpojen.")

if __name__ == '__main__':
    logger.info("Startuji Gateway Node (CMS & WS) na 127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
