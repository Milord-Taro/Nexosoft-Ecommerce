# accounts/mongo_service.py
from django.conf import settings
from pymongo import MongoClient, errors
from bson import ObjectId
import bcrypt

_client = None
_db = None

def get_db():
    """
    Devuelve la instancia de base de datos MongoDB usando
    la URI y el nombre configurados en settings.py
    """
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGO_URI)
        _db = _client[settings.MONGO_DB_NAME]
    return _db

def get_usuarios_collection():
    db = get_db()
    # Ajusta el nombre si tu colección se llama "Usuarios"
    return db["Usuarios"]

def get_roles_collection():
    db = get_db()
    # Ajusta el nombre si tu colección se llama "Roles"
    return db["Rol"]

# ─────────────────────────────────────────────
# ROLES
# ─────────────────────────────────────────────

def obtener_id_rol(nombre_rol: str) -> ObjectId | None:
    """
    Busca el rol por nombre (Cliente, Vendedor, Admin)
    y devuelve su ObjectId o None si no existe.
    """
    roles = get_roles_collection()
    rol = roles.find_one({"nombreDeRol": nombre_rol, "estado": "activo"})
    print("DEBUG ROL ENCONTRADO →", rol)
    return rol["_id"] if rol else None

# ─────────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────────

def buscar_usuario_por_correo(correo: str):
    usuarios = get_usuarios_collection()
    return usuarios.find_one({"correoElectronico": correo})

def crear_usuario(datos: dict):
    """
    Inserta un usuario respetando el schema de Mongo.
    Lanza DuplicateKeyError si correo o doc están repetidos.
    """
    usuarios = get_usuarios_collection()
    return usuarios.insert_one(datos)

def verificar_password(password_plana: str, hash_guardado: str) -> bool:
    """
    Compara la contraseña plana con el hash almacenado (bcrypt).
    """
    try:
        return bcrypt.checkpw(
            password_plana.encode("utf-8"),
            hash_guardado.encode("utf-8")
        )
    except Exception:
        return False

def hash_password(password_plana: str) -> str:
    """
    Genera hash bcrypt para almacenar en 'contraseñaHash'.
    """
    salt = bcrypt.gensalt(rounds=12)
    pwd_hash = bcrypt.hashpw(password_plana.encode("utf-8"), salt)
    return pwd_hash.decode("utf-8")
