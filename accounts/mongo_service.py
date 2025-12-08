# accounts/mongo_service.py
from django.conf import settings
from pymongo import MongoClient, errors
from pymongo.errors import PyMongoError
from bson import ObjectId
import bcrypt
from datetime import datetime, timezone

_client = None
_db = None

def get_db():
    global _client, _db

    if _db is not None:
        return _db

    # 1. Intentar Atlas
    try:
        uri = settings.MONGO_URI_ATLAS
        if uri:
            client = MongoClient(uri)
            client.admin.command("ping")
            print("🔗 Usando MongoDB Atlas")
            _client = client
            _db = client[settings.MONGO_DB_NAME]
            return _db
    except PyMongoError as e:
        print("⚠️ No se pudo conectar a Atlas:", e)

    # 2. Fallback a local
    try:
        client = MongoClient(settings.MONGO_URI_LOCAL)
        client.admin.command("ping")
        print("💻 Usando MongoDB Local")
        _client = client
        _db = client[settings.MONGO_DB_NAME]
        return _db
    except PyMongoError as e:
        print("❌ No se pudo conectar ni a Atlas ni a Local:", e)
        raise

db = get_db()

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
    return usuarios.find_one({"correoElectronico": correo.lower()})

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

def marcar_usuario_eliminado(usuario_id: str):
    """
    Marca la cuenta como 'eliminado' en estadoCuenta.
    (Para proyecto educativo es mejor que borrar físicamente).
    """
    return actualizar_usuario(usuario_id, {"estadoCuenta": "eliminado"})


def actualizar_usuario(usuario_id: str, campos: dict) -> bool:
    """
    Actualiza los campos indicados para el usuario.
    Retorna True si modificó algún documento.
    """
    col = get_usuarios_collection()
    try:
        oid = ObjectId(usuario_id)
    except Exception:
        return False

    result = col.update_one({"_id": oid}, {"$set": campos})
    return result.modified_count > 0


def marcar_usuario_para_eliminacion(usuario_id: str) -> bool:
    """
    Marca el usuario como pendiente de eliminación.
    No borra físicamente el registro.
    """
    col = get_usuarios_collection()
    try:
        oid = ObjectId(usuario_id)
    except Exception:
        return False

    result = col.update_one(
        {"_id": oid},
        {
            "$set": {
                "estadoCuenta": "pendiente_eliminacion",
                "fechaSolicitudEliminacion": datetime.now(timezone.utc),
            }
        },
    )
    return result.modified_count > 0

def get_mongo():
    # 1. Intentar Atlas
    try:
        client = MongoClient(
            settings.MONGO_URI_ATLAS,
            serverSelectionTimeoutMS=3000
        )
        client.admin.command("ping")
        print("🔗 Usando MongoDB Atlas")
        return client[settings.MONGO_DB_NAME]

    except Exception as e:
        print("⚠️ Atlas no disponible:", e)

        # 2. Intentar conexión local
        client = MongoClient(settings.MONGO_URI_LOCAL)
        print("💻 Usando MongoDB Local")
        return client[settings.MONGO_DB_NAME]

db = get_mongo()

def actualizar_password_por_correo(correo: str, nueva_password_plana: str) -> bool:
    """
    Actualiza la contraseña de un usuario identificado por su correo.
    Retorna True si se modificó algún documento.
    """
    col = get_usuarios_collection()
    hash_nuevo = hash_password(nueva_password_plana)

    result = col.update_one(
        {"correoElectronico": correo},
        {"$set": {"contraseñaHash": hash_nuevo}}
    )
    return result.modified_count > 0
