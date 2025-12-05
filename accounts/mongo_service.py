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

def buscar_usuario_por_documento(tipo_ident: str, numero_ident: str):
    col = get_usuarios_collection()
    return col.find_one({
        "tipoIdentificacion": tipo_ident,
        "numeroIdentificacion": numero_ident
    })

def obtener_usuario_por_id(id_str: str):
    """
    Devuelve el documento de usuario dado su _id en formato string.
    """
    usuarios = get_usuarios_collection()
    try:
        oid = ObjectId(id_str)
    except Exception:
        return None
    return usuarios.find_one({"_id": oid})


def actualizar_usuario(usuario_id: str, campos: dict):
    """
    Actualiza los campos indicados en el usuario con ese _id.
    """
    usuarios = get_usuarios_collection()
    oid = ObjectId(usuario_id)
    return usuarios.update_one({"_id": oid}, {"$set": campos})


def marcar_usuario_eliminado(usuario_id: str):
    """
    Marca la cuenta como 'eliminado' en estadoCuenta.
    (Para proyecto educativo es mejor que borrar físicamente).
    """
    return actualizar_usuario(usuario_id, {"estadoCuenta": "eliminado"})