from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json, os, uuid, hashlib

app = Flask(__name__)

# Archivo donde se guardan las licencias
DB_FILE = "licencias.json"
# Clave secreta de admin (cámbiala por una tuya)
ADMIN_KEY = "karla-admin-2024-secreto"

def cargar_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"licencias": {}}

def guardar_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# ══ RUTAS PÚBLICAS (el PDV las usa) ══════════════════════

@app.route("/verificar", methods=["POST"])
def verificar():
    data = request.json or {}
    clave = data.get("clave", "").strip()
    if not clave:
        return jsonify({"activa": False, "mensaje": "Clave requerida"}), 400

    db = cargar_db()
    lic = db["licencias"].get(clave)

    if not lic:
        return jsonify({"activa": False, "mensaje": "Licencia no encontrada"}), 404

    hoy = datetime.now().date()
    vence = datetime.strptime(lic["vence"], "%Y-%m-%d").date()
    dias_restantes = (vence - hoy).days

    if hoy > vence:
        return jsonify({
            "activa": False,
            "mensaje": "Licencia vencida",
            "vencio": lic["vence"],
            "tienda": lic["tienda"]
        })

    return jsonify({
        "activa": True,
        "tienda": lic["tienda"],
        "vence": lic["vence"],
        "dias_restantes": dias_restantes,
        "mensaje": f"Licencia activa — vence en {dias_restantes} días"
    })

# ══ RUTAS DE ADMIN (solo tú las usas) ════════════════════

def verificar_admin(req):
    return req.headers.get("X-Admin-Key") == ADMIN_KEY

@app.route("/admin/licencias", methods=["GET"])
def listar_licencias():
    if not verificar_admin(request):
        return jsonify({"error": "No autorizado"}), 401
    db = cargar_db()
    hoy = datetime.now().date()
    resultado = []
    for clave, lic in db["licencias"].items():
        vence = datetime.strptime(lic["vence"], "%Y-%m-%d").date()
        dias = (vence - hoy).days
        resultado.append({
            "clave": clave,
            "tienda": lic["tienda"],
            "email": lic.get("email", ""),
            "vence": lic["vence"],
            "dias_restantes": dias,
            "activa": dias >= 0
        })
    resultado.sort(key=lambda x: x["dias_restantes"])
    return jsonify({"total": len(resultado), "licencias": resultado})

@app.route("/admin/crear", methods=["POST"])
def crear_licencia():
    if not verificar_admin(request):
        return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    tienda = data.get("tienda", "").strip()
    email  = data.get("email", "").strip()
    meses  = int(data.get("meses", 1))
    if not tienda:
        return jsonify({"error": "Nombre de tienda requerido"}), 400

    clave = "KPV-" + uuid.uuid4().hex[:8].upper()
    vence = (datetime.now() + timedelta(days=30 * meses)).strftime("%Y-%m-%d")

    db = cargar_db()
    db["licencias"][clave] = {
        "tienda": tienda,
        "email": email,
        "vence": vence,
        "creada": datetime.now().strftime("%Y-%m-%d"),
        "meses": meses
    }
    guardar_db(db)
    return jsonify({
        "ok": True,
        "clave": clave,
        "tienda": tienda,
        "vence": vence,
        "mensaje": f"Licencia creada. Clave: {clave}"
    })

@app.route("/admin/extender", methods=["POST"])
def extender_licencia():
    if not verificar_admin(request):
        return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    clave = data.get("clave", "").strip()
    meses = int(data.get("meses", 1))

    db = cargar_db()
    lic = db["licencias"].get(clave)
    if not lic:
        return jsonify({"error": "Licencia no encontrada"}), 404

    hoy   = datetime.now().date()
    vence = datetime.strptime(lic["vence"], "%Y-%m-%d").date()
    base  = vence if vence > hoy else hoy
    nueva_fecha = (base + timedelta(days=30 * meses)).strftime("%Y-%m-%d")
    lic["vence"] = nueva_fecha
    guardar_db(db)
    return jsonify({"ok": True, "clave": clave, "nueva_fecha": nueva_fecha, "tienda": lic["tienda"]})

@app.route("/admin/bloquear", methods=["POST"])
def bloquear_licencia():
    if not verificar_admin(request):
        return jsonify({"error": "No autorizado"}), 401
    data  = request.json or {}
    clave = data.get("clave", "").strip()
    db    = cargar_db()
    if clave not in db["licencias"]:
        return jsonify({"error": "Licencia no encontrada"}), 404
    db["licencias"][clave]["vence"] = "2000-01-01"
    guardar_db(db)
    return jsonify({"ok": True, "mensaje": f"Licencia {clave} bloqueada"})

@app.route("/admin/eliminar", methods=["POST"])
def eliminar_licencia():
    if not verificar_admin(request):
        return jsonify({"error": "No autorizado"}), 401
    data  = request.json or {}
    clave = data.get("clave", "").strip()
    db    = cargar_db()
    if clave not in db["licencias"]:
        return jsonify({"error": "Licencia no encontrada"}), 404
    del db["licencias"][clave]
    guardar_db(db)
    return jsonify({"ok": True, "mensaje": f"Licencia {clave} eliminada"})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "sistema": "Karla PDV Licencias"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
