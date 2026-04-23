from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os, uuid, requests as req

app = Flask(__name__)
CORS(app)

ADMIN_KEY   = os.environ.get("ADMIN_KEY", "karla2024secreto")
BIN_ID      = os.environ.get("BIN_ID", "69ea6912856a682189664be2")
JSONBIN_KEY = os.environ.get("JSONBIN_KEY", "$2a$10$0WPuZE9MulMJTzYsSSIUXuuZrl7cpF6d9SAD85dSMF5buus/s3nk2")
BIN_URL     = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS     = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}

def cargar_db():
    try:
        r = req.get(BIN_URL + "/latest", headers=HEADERS, timeout=10)
        return r.json().get("record", {"licencias": {}})
    except:
        return {"licencias": {}}

def guardar_db(db):
    try:
        req.put(BIN_URL, json=db, headers=HEADERS, timeout=10)
    except:
        pass

def ok_admin():
    return request.headers.get("X-Admin-Key") == ADMIN_KEY

# ══ PÚBLICO ═══════════════════════════════════════════════
@app.route("/verificar", methods=["POST","OPTIONS"])
def verificar():
    if request.method == "OPTIONS": return jsonify({}), 200
    data  = request.json or {}
    clave = data.get("clave","").strip()
    if not clave: return jsonify({"activa":False,"mensaje":"Clave requerida"}), 400
    db  = cargar_db()
    lic = db["licencias"].get(clave)
    if not lic: return jsonify({"activa":False,"mensaje":"Licencia no encontrada"}), 404
    hoy   = datetime.now().date()
    vence = datetime.strptime(lic["vence"],"%Y-%m-%d").date()
    dias  = (vence - hoy).days
    if hoy > vence:
        return jsonify({"activa":False,"mensaje":"Licencia vencida","vencio":lic["vence"],"tienda":lic["tienda"]})
    return jsonify({"activa":True,"tienda":lic["tienda"],"vence":lic["vence"],"dias_restantes":dias})

# ══ ADMIN ══════════════════════════════════════════════════
@app.route("/admin/licencias", methods=["GET","OPTIONS"])
def listar():
    if request.method == "OPTIONS": return jsonify({}), 200
    if not ok_admin(): return jsonify({"error":"No autorizado"}), 401
    db  = cargar_db()
    hoy = datetime.now().date()
    res = []
    for clave, lic in db["licencias"].items():
        vence = datetime.strptime(lic["vence"],"%Y-%m-%d").date()
        dias  = (vence - hoy).days
        res.append({"clave":clave,"tienda":lic["tienda"],"email":lic.get("email",""),
                    "vence":lic["vence"],"dias_restantes":dias,"activa":dias>=0})
    res.sort(key=lambda x: x["dias_restantes"])
    return jsonify({"total":len(res),"licencias":res})

@app.route("/admin/crear", methods=["POST","OPTIONS"])
def crear():
    if request.method == "OPTIONS": return jsonify({}), 200
    if not ok_admin(): return jsonify({"error":"No autorizado"}), 401
    data   = request.json or {}
    tienda = data.get("tienda","").strip()
    email  = data.get("email","").strip()
    meses  = int(data.get("meses",1))
    if not tienda: return jsonify({"error":"Nombre requerido"}), 400
    clave = "KPV-" + uuid.uuid4().hex[:8].upper()
    vence = (datetime.now() + timedelta(days=30*meses)).strftime("%Y-%m-%d")
    db    = cargar_db()
    db["licencias"][clave] = {"tienda":tienda,"email":email,"vence":vence,
                               "creada":datetime.now().strftime("%Y-%m-%d"),"meses":meses}
    guardar_db(db)
    return jsonify({"ok":True,"clave":clave,"tienda":tienda,"vence":vence})

@app.route("/admin/extender", methods=["POST","OPTIONS"])
def extender():
    if request.method == "OPTIONS": return jsonify({}), 200
    if not ok_admin(): return jsonify({"error":"No autorizado"}), 401
    data  = request.json or {}
    clave = data.get("clave","").strip()
    meses = int(data.get("meses",1))
    db    = cargar_db()
    lic   = db["licencias"].get(clave)
    if not lic: return jsonify({"error":"No encontrada"}), 404
    hoy   = datetime.now().date()
    vence = datetime.strptime(lic["vence"],"%Y-%m-%d").date()
    base  = vence if vence > hoy else hoy
    lic["vence"] = (base + timedelta(days=30*meses)).strftime("%Y-%m-%d")
    guardar_db(db)
    return jsonify({"ok":True,"clave":clave,"nueva_fecha":lic["vence"],"tienda":lic["tienda"]})

@app.route("/admin/bloquear", methods=["POST","OPTIONS"])
def bloquear():
    if request.method == "OPTIONS": return jsonify({}), 200
    if not ok_admin(): return jsonify({"error":"No autorizado"}), 401
    clave = (request.json or {}).get("clave","").strip()
    db    = cargar_db()
    if clave not in db["licencias"]: return jsonify({"error":"No encontrada"}), 404
    db["licencias"][clave]["vence"] = "2000-01-01"
    guardar_db(db)
    return jsonify({"ok":True})

@app.route("/admin/eliminar", methods=["POST","OPTIONS"])
def eliminar():
    if request.method == "OPTIONS": return jsonify({}), 200
    if not ok_admin(): return jsonify({"error":"No autorizado"}), 401
    clave = (request.json or {}).get("clave","").strip()
    db    = cargar_db()
    if clave not in db["licencias"]: return jsonify({"error":"No encontrada"}), 404
    del db["licencias"][clave]
    guardar_db(db)
    return jsonify({"ok":True})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status":"ok","sistema":"Karla PDV Licencias"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
