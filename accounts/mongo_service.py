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

def get_usuarios_collection():
    db = get_db()
    # Ajusta el nombre si tu colección se llama "Usuarios"
    return db["Usuarios"]

def get_roles_collection():
    db = get_db()
    # Ajusta el nombre si tu colección se llama "Roles"
    return db["Rol"]

def get_direcciones_envio_collection():
    """
    Colección para almacenar las direcciones de envío de los usuarios.
    1 usuario puede tener varias direcciones (idUsuario).
    """
    db = get_db()
    return db["DireccionesEnvio"]

def get_productos_collection():
    """
    Devuelve la colección Productos.
    """
    db = get_db()
    return db["Productos"]

def get_carritos_collection():
    """
    Devuelve la colección Carritos.
    """
    db = get_db()
    return db["Carritos"]

def get_pedidos_collection():
    """
    Devuelve la colección Pedidos.
    """
    db = get_db()
    return db["Pedidos"]




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


def _recalcular_totales_carrito(carrito: dict) -> dict:
    """
    Recalcula subtotalCarritoSnapshot, subtotalSeleccionadoSnapshot
    y totalSeleccionadoSnapshot en el documento de carrito.
    NO guarda en BD, solo modifica el dict en memoria.
    """
    subtotal_total = 0
    subtotal_seleccionado = 0

    for item in carrito.get("itemsCarrito", []):
        subtotal_linea = item.get("subtotalLineaSnapshot", 0)
        subtotal_total += subtotal_linea
        if item.get("seleccionado", True):
            subtotal_seleccionado += subtotal_linea

    carrito["subtotalCarritoSnapshot"] = subtotal_total
    carrito["subtotalSeleccionadoSnapshot"] = subtotal_seleccionado
    # Por ahora el total es igual al subtotal seleccionado
    carrito["totalSeleccionadoSnapshot"] = subtotal_seleccionado

    carrito["fechaActualizacionCarrito"] = datetime.now(timezone.utc)
    return carrito

def obtener_o_crear_carrito_abierto(id_usuario_str: str) -> dict:
    """
    Obtiene el carrito 'abierto' de un usuario.
    Si no existe, crea uno nuevo vacío.
    Devuelve el documento de carrito (dict).
    """
    carritos = get_carritos_collection()

    try:
        id_usuario = ObjectId(id_usuario_str)
    except Exception:
        raise ValueError("id_usuario_str no es un ObjectId válido")

    carrito = carritos.find_one({
        "idUsuarioCliente": id_usuario,
        "estadoCarrito": "abierto"
    })

    if carrito:
        return carrito

    # Crear uno nuevo
    nuevo = {
        "idUsuarioCliente": id_usuario,
        "estadoCarrito": "abierto",
        "fechaCreacionCarrito": datetime.now(timezone.utc),
        "fechaActualizacionCarrito": datetime.now(timezone.utc),
        "itemsCarrito": [],
        "subtotalCarritoSnapshot": 0,
        "subtotalSeleccionadoSnapshot": 0,
        "totalSeleccionadoSnapshot": 0
    }

    result = carritos.insert_one(nuevo)
    nuevo["_id"] = result.inserted_id
    return nuevo

def agregar_o_actualizar_item_carrito(
    id_usuario_str: str,
    id_producto_str: str,
    cantidad: int
) -> dict:
    """
    Agrega un producto al carrito del usuario o actualiza su cantidad.
    - Verifica que el producto exista y esté 'activo'.
    - Verifica que haya stock suficiente (inventario.stockActual).
    - Si el ítem ya existe en el carrito, suma la cantidad.
    - Siempre marca seleccionado=True cuando se agrega/actualiza.
    Devuelve el carrito actualizado.
    Lanza ValueError con mensajes claros si algo falla.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")

    productos = get_productos_collection()
    carritos = get_carritos_collection()

    # Convertir ids
    try:
        id_usuario = ObjectId(id_usuario_str)
        id_producto = ObjectId(id_producto_str)
    except Exception:
        raise ValueError("id_usuario_str o id_producto_str no son ObjectId válidos")

    # 1. Buscar producto
    producto = productos.find_one({"_id": id_producto})
    if not producto:
        raise ValueError("El producto no existe")

    if producto.get("estadoProducto") != "activo":
        raise ValueError("El producto no está activo en el catálogo")

    inventario = producto.get("inventario", {})
    stock_actual = inventario.get("stockActual", 0)

    # 2. Obtener o crear carrito
    carrito = obtener_o_crear_carrito_abierto(id_usuario_str)

    # 3. Buscar si ya existe ítem para ese producto
    items = carrito.get("itemsCarrito", [])
    item_existente = None
    for item in items:
        if item.get("idProducto") == id_producto:
            item_existente = item
            break

    # 4. Calcular nueva cantidad
    if item_existente:
        nueva_cantidad = item_existente["cantidad"] + cantidad
    else:
        nueva_cantidad = cantidad

    if nueva_cantidad > stock_actual:
        raise ValueError(
            f"No hay stock suficiente. Stock disponible: {stock_actual}, "
            f"cantidad solicitada total en carrito: {nueva_cantidad}"
        )

    precio_unitario = inventario.get("precioVenta")
    if precio_unitario is None:
        raise ValueError("El producto no tiene precioVenta definido en inventario")

    subtotal_linea = nueva_cantidad * precio_unitario

    # 5. Actualizar/crear ítem
    if item_existente:
        item_existente["cantidad"] = nueva_cantidad
        item_existente["precioUnitarioSnapshot"] = precio_unitario
        item_existente["subtotalLineaSnapshot"] = subtotal_linea
        item_existente["seleccionado"] = True
    else:
        nuevo_item = {
            "_idItemCarrito": ObjectId(),
            "idProducto": id_producto,
            "nombreProducto": producto.get("nombreProducto", ""),
            "cantidad": nueva_cantidad,
            "precioUnitarioSnapshot": precio_unitario,
            "subtotalLineaSnapshot": subtotal_linea,
            "seleccionado": True
        }
        items.append(nuevo_item)
        carrito["itemsCarrito"] = items

    # 6. Recalcular totales
    carrito = _recalcular_totales_carrito(carrito)

    # 7. Guardar en BD y devolver
    carritos.update_one(
        {"_id": carrito["_id"]},
        {"$set": {
            "itemsCarrito": carrito["itemsCarrito"],
            "subtotalCarritoSnapshot": carrito["subtotalCarritoSnapshot"],
            "subtotalSeleccionadoSnapshot": carrito["subtotalSeleccionadoSnapshot"],
            "totalSeleccionadoSnapshot": carrito["totalSeleccionadoSnapshot"],
            "fechaActualizacionCarrito": carrito["fechaActualizacionCarrito"],
        }}
    )

    return carrito

def actualizar_cantidad_item_carrito(
    id_usuario_str: str,
    id_producto_str: str,
    nueva_cantidad: int
) -> dict:
    """
    Actualiza la cantidad de un producto en el carrito.
    - Si nueva_cantidad == 0 → elimina el ítem del carrito.
    - Verifica stock antes de aplicar cambio.
    Devuelve el carrito actualizado.
    """
    productos = get_productos_collection()
    carritos = get_carritos_collection()

    try:
        id_usuario = ObjectId(id_usuario_str)
        id_producto = ObjectId(id_producto_str)
    except Exception:
        raise ValueError("id_usuario_str o id_producto_str no son ObjectId válidos")

    carrito = carritos.find_one({
        "idUsuarioCliente": id_usuario,
        "estadoCarrito": "abierto"
    })

    if not carrito:
        raise ValueError("El usuario no tiene un carrito abierto")

    items = carrito.get("itemsCarrito", [])
    item_encontrado = None
    for item in items:
        if item.get("idProducto") == id_producto:
            item_encontrado = item
            break

    if not item_encontrado:
        raise ValueError("El producto no está en el carrito")

    if nueva_cantidad == 0:
        # Eliminar ítem
        items = [it for it in items if it.get("idProducto") != id_producto]
        carrito["itemsCarrito"] = items
    else:
        # Verificar stock
        producto = productos.find_one({"_id": id_producto})
        if not producto:
            raise ValueError("El producto no existe")

        inventario = producto.get("inventario", {})
        stock_actual = inventario.get("stockActual", 0)
        if nueva_cantidad > stock_actual:
            raise ValueError(
                f"No hay stock suficiente. Stock disponible: {stock_actual}, "
                f"cantidad solicitada: {nueva_cantidad}"
            )

        precio_unitario = inventario.get("precioVenta")
        if precio_unitario is None:
            raise ValueError("El producto no tiene precioVenta definido en inventario")

        item_encontrado["cantidad"] = nueva_cantidad
        item_encontrado["precioUnitarioSnapshot"] = precio_unitario
        item_encontrado["subtotalLineaSnapshot"] = nueva_cantidad * precio_unitario

    carrito = _recalcular_totales_carrito(carrito)

    carritos.update_one(
        {"_id": carrito["_id"]},
        {"$set": {
            "itemsCarrito": carrito["itemsCarrito"],
            "subtotalCarritoSnapshot": carrito["subtotalCarritoSnapshot"],
            "subtotalSeleccionadoSnapshot": carrito["subtotalSeleccionadoSnapshot"],
            "totalSeleccionadoSnapshot": carrito["totalSeleccionadoSnapshot"],
            "fechaActualizacionCarrito": carrito["fechaActualizacionCarrito"],
        }}
    )

    return carrito

def actualizar_seleccion_item_carrito(
    id_usuario_str: str,
    id_producto_str: str,
    seleccionado: bool
) -> dict:
    """
    Marca un ítem del carrito como seleccionado o no seleccionado.
    Esto afecta subtotalSeleccionadoSnapshot y totalSeleccionadoSnapshot.
    """
    carritos = get_carritos_collection()

    try:
        id_usuario = ObjectId(id_usuario_str)
        id_producto = ObjectId(id_producto_str)
    except Exception:
        raise ValueError("id_usuario_str o id_producto_str no son ObjectId válidos")

    carrito = carritos.find_one({
        "idUsuarioCliente": id_usuario,
        "estadoCarrito": "abierto"
    })

    if not carrito:
        raise ValueError("El usuario no tiene un carrito abierto")

    items = carrito.get("itemsCarrito", [])
    item_encontrado = None
    for item in items:
        if item.get("idProducto") == id_producto:
            item_encontrado = item
            break

    if not item_encontrado:
        raise ValueError("El producto no está en el carrito")

    item_encontrado["seleccionado"] = bool(seleccionado)

    carrito = _recalcular_totales_carrito(carrito)

    carritos.update_one(
        {"_id": carrito["_id"]},
        {"$set": {
            "itemsCarrito": carrito["itemsCarrito"],
            "subtotalCarritoSnapshot": carrito["subtotalCarritoSnapshot"],
            "subtotalSeleccionadoSnapshot": carrito["subtotalSeleccionadoSnapshot"],
            "totalSeleccionadoSnapshot": carrito["totalSeleccionadoSnapshot"],
            "fechaActualizacionCarrito": carrito["fechaActualizacionCarrito"],
        }}
    )

    return carrito

def crear_pedido_desde_carrito(
    id_usuario_str: str,
    metodo_entrega: str,
    metodo_pago: str,
    costo_envio: float = 0.0
) -> dict:
    """
    Crea un Pedido a partir del carrito ABIERTO del usuario.
    - Usa SOLO los items seleccionados (seleccionado=True).
    - Relee productos para usar precioActual (inventario.precioVenta).
    - Verifica stock antes de descontar.
    - Actualiza inventario de Productos.
    - Marca el carrito como 'convertido'.

    Devuelve el documento de Pedido creado.
    Lanza ValueError si:
      - No hay carrito.
      - No hay items seleccionados.
      - Falta stock o producto inactivo.
    """
    from bson import ObjectId
    from datetime import datetime, timezone

    productos_col = get_productos_collection()
    carritos_col = get_carritos_collection()
    pedidos_col = get_pedidos_collection()

    try:
        id_usuario = ObjectId(id_usuario_str)
    except Exception:
        raise ValueError("id_usuario_str no es un ObjectId válido")

    # 1. Obtener carrito ABIERTO
    carrito = carritos_col.find_one({
        "idUsuarioCliente": id_usuario,
        "estadoCarrito": "abierto"
    })

    if not carrito:
        raise ValueError("El usuario no tiene un carrito abierto")

    items_carrito = carrito.get("itemsCarrito", [])

    # 2. Filtrar SOLO items seleccionados y con cantidad > 0
    items_seleccionados = [
        item for item in items_carrito
        if item.get("seleccionado", True) and item.get("cantidad", 0) > 0
    ]

    if not items_seleccionados:
        raise ValueError("No hay productos seleccionados para crear el pedido.")

    # 3. Validar productos, stock y armar itemsPedido
    items_pedido = []
    subtotal_pedido = 0.0
    productos_a_actualizar_stock = []  # (idProducto, cantidad)

    for item in items_seleccionados:
        id_producto = item.get("idProducto")
        cantidad = item.get("cantidad", 0)

        if not id_producto or cantidad <= 0:
            continue

        producto = productos_col.find_one({"_id": id_producto})
        if not producto:
            raise ValueError("Uno de los productos del carrito ya no existe.")

        if producto.get("estadoProducto") != "activo":
            raise ValueError(
                f"El producto '{producto.get('nombreProducto', '')}' ya no está activo."
            )

        inventario = producto.get("inventario", {})
        stock_actual = inventario.get("stockActual", 0)
        precio_actual = inventario.get("precioVenta")

        if precio_actual is None:
            raise ValueError(
                f"El producto '{producto.get('nombreProducto', '')}' no tiene precio definido."
            )

        if cantidad > stock_actual:
            raise ValueError(
                f"No hay stock suficiente para '{producto.get('nombreProducto', '')}'. "
                f"Disponible: {stock_actual}, solicitado: {cantidad}."
            )

        subtotal_linea = float(cantidad * precio_actual)
        subtotal_pedido += subtotal_linea

        items_pedido.append({
            "idProducto": id_producto,
            "nombreProducto": producto.get("nombreProducto", ""),
            "cantidad": int(cantidad),
            "precioUnitario": float(precio_actual),
            "subtotalLinea": subtotal_linea
        })

        productos_a_actualizar_stock.append((id_producto, cantidad))

    # 4. Calcular totales
    subtotal_pedido = float(subtotal_pedido)
    costo_envio = float(costo_envio)
    total_pedido = subtotal_pedido + costo_envio

        # 4.5. Obtener la dirección principal del usuario
    direcciones_col = get_direcciones_envio_collection()
    dir_principal = direcciones_col.find_one({
        "idUsuario": id_usuario,
        "activo": True,
        "esPrincipal": True,
    })

    if not dir_principal:
        # No dejamos crear pedido si no hay dirección principal
        raise ValueError("Debes tener al menos una dirección de envío principal para finalizar la compra.")

    # Snapshot de la dirección al momento del pedido
    direccion_snapshot = {
        "idDireccionEnvio": dir_principal["_id"],
        "nombreContacto": dir_principal.get("nombreContacto", ""),
        "telefonoContacto": dir_principal.get("telefonoContacto", ""),
        "ciudad": dir_principal.get("ciudad", ""),
        "barrio": dir_principal.get("barrio", ""),
        "complemento": dir_principal.get("complemento", ""),
    }

    # 5. Construir documento Pedido (siguiendo tu $jsonSchema)
    ahora = datetime.now(timezone.utc)

    pedido_doc = {
        "idUsuarioCliente": id_usuario,
        "itemsPedido": items_pedido,
        "fechaCreacionPedido": ahora,
        "estadoPedido": "pendiente",  # luego lo cambiarás a 'pagado', etc.
        "subtotalPedido": subtotal_pedido,
        "costoEnvioPedido": costo_envio,
        "totalPedido": total_pedido,
        "metodoEntrega": metodo_entrega,  # 'domicilio' | 'contraEntrega'
        "metodoPago": metodo_pago,       # 'efectivo', 'tarjetaCredito', etc.
        # 👇 NUEVO
        "idDireccionEnvio": direccion_snapshot["idDireccionEnvio"],
        "direccionEnvioSnapshot": direccion_snapshot,
    }

    # 6. Insertar Pedido
    result = pedidos_col.insert_one(pedido_doc)
    pedido_doc["_id"] = result.inserted_id

    # 7. Actualizar stock de productos
    for id_producto, cantidad in productos_a_actualizar_stock:
        productos_col.update_one(
            {"_id": id_producto},
            {"$inc": {"inventario.stockActual": -int(cantidad)}}
        )

    # 8. Marcar carrito como 'convertido'
    carritos_col.update_one(
        {"_id": carrito["_id"]},
        {
            "$set": {
                "estadoCarrito": "convertido",
                "fechaActualizacionCarrito": ahora
            }
        }
    )

    return pedido_doc


# ─────────────────────────────────────────────
#  CRUD de PRODUCTOS (uso para admin / catálogo)
# ─────────────────────────────────────────────

from datetime import datetime, timezone
from bson import ObjectId
from pymongo.errors import PyMongoError

def listar_productos(estado: str | None = None) -> list[dict]:
    """
    Devuelve una lista de productos.
    - Si 'estado' es 'activo' o 'inactivo', filtra por ese estado.
    - Ordena por nombreProducto.
    """
    col = get_productos_collection()
    filtro = {}
    if estado in ("activo", "inactivo"):
        filtro["estadoProducto"] = estado

    cursor = col.find(filtro).sort("nombreProducto", 1)

    productos = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])  # más cómodo para templates
        productos.append(doc)
    return productos


def obtener_producto_por_id(id_producto_str: str) -> dict | None:
    """
    Devuelve un producto por su _id en string.
    Retorna None si el id no es válido o no existe.
    """
    try:
        oid = ObjectId(id_producto_str)
    except Exception:
        return None

    col = get_productos_collection()
    doc = col.find_one({"_id": oid})
    if doc:
        doc["id"] = str(doc["_id"])
    return doc


def crear_producto(doc_producto: dict) -> str:
    """
    Inserta un nuevo producto.
    Espera que 'doc_producto' ya respete el schema de Mongo.
    Añade fechaCreacion y fechaActualizacion.
    Devuelve el id insertado como string.
    """
    ahora = datetime.now(timezone.utc)
    doc_producto["fechaCreacion"] = ahora
    doc_producto["fechaActualizacion"] = ahora

    col = get_productos_collection()
    resultado = col.insert_one(doc_producto)
    return str(resultado.inserted_id)


def actualizar_producto(id_producto_str: str, campos_actualizados: dict) -> bool:
    """
    Actualiza un producto existente.
    Solo actualiza los campos pasados en 'campos_actualizados'.
    Devuelve True si se modificó algún documento.
    """
    try:
        oid = ObjectId(id_producto_str)
    except Exception:
        raise ValueError("id_producto_str no es un ObjectId válido")

    if not campos_actualizados:
        return False

    campos_actualizados["fechaActualizacion"] = datetime.now(timezone.utc)

    col = get_productos_collection()
    res = col.update_one(
        {"_id": oid},
        {"$set": campos_actualizados}
    )
    return res.modified_count == 1


def cambiar_estado_producto(id_producto_str: str, nuevo_estado: str) -> bool:
    """
    Cambia 'estadoProducto' a 'activo' o 'inactivo'.
    Esto actúa como un 'soft delete' cuando lo ponemos en inactivo.
    """
    if nuevo_estado not in ("activo", "inactivo"):
        raise ValueError("estado inválido, use 'activo' o 'inactivo'.")

    return actualizar_producto(
        id_producto_str,
        {"estadoProducto": nuevo_estado}
    )


def eliminar_producto_definitivo(id_producto_str: str) -> bool:
    """
    Elimina físicamente un producto de la colección.
    En la mayoría de casos es mejor usar cambiar_estado_producto()
    para no romper referencias en carritos/pedidos.
    """
    try:
        oid = ObjectId(id_producto_str)
    except Exception:
        raise ValueError("id_producto_str no es un ObjectId válido")

    col = get_productos_collection()
    res = col.delete_one({"_id": oid})
    return res.deleted_count == 1

def listar_productos_activos():
    """
    Devuelve una lista de productos con estadoProducto = 'activo'.
    Agrega un campo 'id' como string para usar en los templates.
    """
    col = get_productos_collection()
    cursor = col.find({"estadoProducto": "activo"}).sort("nombreProducto", 1)

    productos = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        productos.append(doc)
    return productos

def listar_direcciones_usuario(usuario_id: str):
    col = get_direcciones_envio_collection()
    try:
        oid = ObjectId(usuario_id)
    except Exception:
        return []

    cursor = col.find(
        {"idUsuario": oid, "activo": True}
    ).sort("fechaCreacion", 1)

    direcciones = []
    for doc in cursor:
        direcciones.append({
            "id": str(doc["_id"]),  # 👈 importante, esto alimenta {{ d.id }} en el template
            "nombreContacto": doc.get("nombreContacto", ""),
            "telefonoContacto": doc.get("telefonoContacto", ""),
            "ciudad": doc.get("ciudad", ""),
            "barrio": doc.get("barrio", ""),
            "complemento": doc.get("complemento", ""),
            "esPrincipal": doc.get("esPrincipal", False),
        })
    return direcciones

def crear_direccion_envio(usuario_id: str, data: dict):
    """
    data: dict con claves:
      nombreContacto, telefonoContacto, ciudad, barrio,
      complemento, esPrincipal (bool)
    """
    col = get_direcciones_envio_collection()
    oid_usuario = ObjectId(usuario_id)

    es_principal = bool(data.get("esPrincipal"))

    # Si la nueva será principal, desmarcamos las anteriores
    if es_principal:
        col.update_many(
            {"idUsuario": oid_usuario, "activo": True},
            {"$set": {"esPrincipal": False}}
        )

    doc = {
        "idUsuario": oid_usuario,
        "nombreContacto": data.get("nombreContacto", "").strip(),
        "telefonoContacto": data.get("telefonoContacto", "").strip(),
        "ciudad": data.get("ciudad", "").strip(),
        "barrio": data.get("barrio", "").strip(),
        "complemento": data.get("complemento", "").strip(),
        "esPrincipal": es_principal,
        "activo": True,
        "fechaCreacion": datetime.now(timezone.utc),
        "fechaActualizacion": datetime.now(timezone.utc),
    }
    result = col.insert_one(doc)
    return result.inserted_id


def set_direccion_principal(usuario_id: str, direccion_id: str):
    col = get_direcciones_envio_collection()
    oid_usuario = ObjectId(usuario_id)
    oid_dir = ObjectId(direccion_id)

    # Desmarcar todas
    col.update_many(
        {"idUsuario": oid_usuario, "activo": True},
        {"$set": {"esPrincipal": False}}
    )
    # Marcar la seleccionada
    col.update_one(
        {"_id": oid_dir, "idUsuario": oid_usuario},
        {
            "$set": {
                "esPrincipal": True,
                "fechaActualizacion": datetime.now(timezone.utc),
            }
        },
    )


def eliminar_direccion_envio(usuario_id: str, direccion_id: str):
    col = get_direcciones_envio_collection()
    oid_usuario = ObjectId(usuario_id)
    oid_dir = ObjectId(direccion_id)

    # Obtener la dirección antes de eliminar
    dir_obj = col.find_one({"_id": oid_dir, "idUsuario": oid_usuario})

    if not dir_obj:
        return False

    era_principal = dir_obj.get("esPrincipal", False)

    # Soft delete
    col.update_one(
        {"_id": oid_dir, "idUsuario": oid_usuario},
        {
            "$set": {
                "activo": False,
                "esPrincipal": False,
                "fechaActualizacion": datetime.now(timezone.utc),
            }
        },
    )

    # Si era principal → seleccionar la primera dirección activa como nueva principal
    if era_principal:
        nueva = col.find_one(
            {"idUsuario": oid_usuario, "activo": True},
            sort=[("fechaCreacion", 1)]
        )
        if nueva:
            col.update_one(
                {"_id": nueva["_id"]},
                {"$set": {"esPrincipal": True}}
            )

    return True


def actualizar_direccion_envio(usuario_id: str, direccion_id: str, data: dict) -> bool:
    """
    Actualiza una dirección de envío existente del usuario.
    data: dict con:
      nombreContacto, telefonoContacto, ciudad, barrio,
      complemento, esPrincipal (bool)
    """
    col = get_direcciones_envio_collection()
    oid_usuario = ObjectId(usuario_id)
    oid_dir = ObjectId(direccion_id)

    es_principal = bool(data.get("esPrincipal"))

    # Si la dirección se va a marcar como principal, desmarcamos las demás
    if es_principal:
        col.update_many(
            {"idUsuario": oid_usuario, "activo": True},
            {"$set": {"esPrincipal": False}}
        )

    update_doc = {
        "nombreContacto": data.get("nombreContacto", "").strip(),
        "telefonoContacto": data.get("telefonoContacto", "").strip(),
        "ciudad": data.get("ciudad", "").strip(),
        "barrio": data.get("barrio", "").strip(),
        "complemento": data.get("complemento", "").strip(),
        "esPrincipal": es_principal,
        "fechaActualizacion": datetime.now(timezone.utc),
    }

    result = col.update_one(
        {"_id": oid_dir, "idUsuario": oid_usuario, "activo": True},
        {"$set": update_doc}
    )

    return result.modified_count > 0

def marcar_direccion_principal(usuario_id: str, direccion_id: str):
    col = get_direcciones_envio_collection()
    oid_usuario = ObjectId(usuario_id)
    oid_dir = ObjectId(direccion_id)

    # Desmarcar todas las direcciones actuales
    col.update_many(
        {"idUsuario": oid_usuario, "activo": True},
        {"$set": {"esPrincipal": False}}
    )

    # Marcar la seleccionada
    result = col.update_one(
        {"_id": oid_dir, "idUsuario": oid_usuario, "activo": True},
        {
            "$set": {
                "esPrincipal": True,
                "fechaActualizacion": datetime.now(timezone.utc),
            }
        }
    )

    return result.modified_count > 0

def obtener_direccion_principal(usuario_id: str):
    """
    Devuelve el documento real de la dirección principal del usuario
    (la que está en DireccionesEnvio), o None si no hay.
    """
    col = get_direcciones_envio_collection()
    try:
        oid_usuario = ObjectId(usuario_id)
    except Exception:
        return None

    doc = col.find_one({
        "idUsuario": oid_usuario,
        "activo": True,
        "esPrincipal": True,
    })

    # Si no hay marcada como principal, opcionalmente podríamos tomar la primera activa
    if not doc:
        doc = col.find_one(
            {"idUsuario": oid_usuario, "activo": True},
            sort=[("fechaCreacion", 1)]
        )

    return doc
