from django.shortcuts import render, redirect
from django.contrib import messages
from pymongo import errors
from datetime import datetime, timezone

from . import mongo_service

def landing(request):
    return render(request, 'paginaprincipal.html')

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not correo or not password:
            messages.error(request, "Debes ingresar correo y contraseña.")
            return render(request, "login.html")

        usuario = mongo_service.buscar_usuario_por_correo(correo)
        print("DEBUG LOGIN USUARIO →", usuario)

        if not usuario:
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(request, "login.html")

        hash_guardado = usuario.get("contraseñaHash", "")

        if not mongo_service.verificar_password(password, hash_guardado):
            messages.error(request, "Correo o contraseña incorrectos.")
            return render(request, "login.html")

        request.session["usuario_id"] = str(usuario["_id"])
        request.session["usuario_nombre"] = usuario["nombres"]
        request.session["usuario_rol"] = str(usuario["idRol"])

        return redirect("landing")

    return render(request, "login.html")

def logout_view(request):
    # Elimina toda la sesión del usuario
    request.session.flush()
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("landing")

def recuperar_clave_view(request):
    """
    Flujo sencillo de recuperación de contraseña:
    - El usuario ingresa su correo, nueva contraseña y confirmación.
    - Si el correo existe y las contraseñas coinciden, se actualiza el hash.
    """
    if request.method == "POST":
        correo = request.POST.get("correoElectronico", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        # Validaciones básicas
        if not correo or not password or not password2:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, "recuperar_clave.html")

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "recuperar_clave.html")

        usuario = mongo_service.buscar_usuario_por_correo(correo)
        if not usuario:
            # Mensaje genérico para no revelar si el correo existe o no
            messages.error(request, "No se encontró una cuenta asociada a ese correo.")
            return render(request, "recuperar_clave.html")

        ok = mongo_service.actualizar_password_por_correo(correo, password)
        if not ok:
            messages.error(request, "No fue posible actualizar la contraseña. Intenta de nuevo.")
            return render(request, "recuperar_clave.html")

        messages.success(
            request,
            "Tu contraseña se ha actualizado correctamente. Ahora puedes iniciar sesión."
        )
        return redirect("login")

    # GET
    return render(request, "recuperar_clave.html")


def perfil_view(request):
    # 1) Verificar que haya sesión
    usuario_id = request.session.get("usuario_id")
    
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect("login")

    # 2) Obtener usuario desde Mongo
    usuario = mongo_service.obtener_usuario_por_id(usuario_id)
    if not usuario:
        messages.error(request, "No se encontró la información de tu cuenta.")
        request.session.flush()
        return redirect("login")

    # 3) Si es POST, revisar qué acción se está haciendo
    if request.method == "POST":
        action = request.POST.get("action")

        # ───── ACTUALIZAR PERFIL ─────────────────────────────
        if action == "update":
            nombres = request.POST.get("nombres", "").strip()
            apellidos = request.POST.get("apellidos", "").strip()
            telefono = request.POST.get("telefono", "").strip()
            correo = request.POST.get("correoElectronico", "").strip().lower()
            tipo_ident = request.POST.get("tipoIdentificacion", "").strip()
            num_ident = request.POST.get("numeroIdentificacion", "").strip()

            if not all([nombres, apellidos, telefono, correo, tipo_ident, num_ident]):
                messages.error(request, "Todos los campos son obligatorios.")
                # recargar perfil con los datos actuales de BD
                usuario = mongo_service.obtener_usuario_por_id(usuario_id)
                return render(request, "perfil.html", {"usuario": usuario})

            # Validar correo único (excluyendo al propio usuario)
            existente_correo = mongo_service.buscar_usuario_por_correo(correo)
            if existente_correo and str(existente_correo["_id"]) != usuario_id:
                messages.error(request, "Ya existe un usuario con ese correo electrónico.")
                usuario = mongo_service.obtener_usuario_por_id(usuario_id)
                return render(request, "perfil.html", {"usuario": usuario})

            # Validar documento único (excluyendo al propio usuario)
            existente_doc = mongo_service.buscar_usuario_por_documento(tipo_ident, num_ident)
            if existente_doc and str(existente_doc["_id"]) != usuario_id:
                messages.error(request, "Ya existe un usuario con ese documento de identidad.")
                usuario = mongo_service.obtener_usuario_por_id(usuario_id)
                return render(request, "perfil.html", {"usuario": usuario})

            # Hacer update en Mongo
            mongo_service.actualizar_usuario(usuario_id, {
                "nombres": nombres,
                "apellidos": apellidos,
                "telefono": telefono,
                "correoElectronico": correo,
                "tipoIdentificacion": tipo_ident,
                "numeroIdentificacion": num_ident,
            })

            # Refrescamos dato en sesión (nombre para el saludo)
            request.session["usuario_nombre"] = nombres

            messages.success(request, "Tu perfil se actualizó correctamente.")
            usuario = mongo_service.obtener_usuario_por_id(usuario_id)
            return render(request, "perfil.html", {"usuario": usuario})

        # ───── SOLICITAR ELIMINACIÓN DE CUENTA ───────────────
        elif action == "delete":
            mongo_service.marcar_usuario_eliminado(usuario_id)
            # Cerramos sesión para que no pueda seguir navegando como activo
            request.session.flush()
            messages.info(
                request,
                "Tu solicitud de eliminación de cuenta ha sido registrada. Tu cuenta ha sido desactivada."
            )
            return redirect("landing")

    # 4) Si es GET, render normal
    return render(request, "perfil.html", {"usuario": usuario})

def carrito_detalle(request):
    """
    Muestra el carrito del usuario logueado.
    Si no tiene carrito, crea uno vacío.
    También enriquece los items con info de precio actual
    para poder mostrar si hubo cambios.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tu carrito.")
        return redirect("login")

    try:
        carrito = mongo_service.obtener_o_crear_carrito_abierto(usuario_id)
    except Exception as e:
        print("ERROR al obtener carrito:", e)
        messages.error(request, "No fue posible cargar tu carrito en este momento.")
        return redirect("landing")

        # Construir una lista de items “listos para la vista”
    items_ui = []
    for item in carrito.get("itemsCarrito", []):
        id_producto = item.get("idProducto")
        producto = None
        precio_actual = None
        precio_cambio = False
        stock_actual = None
        stock_minimo = None
        stock_bajo = False

        try:
            producto = mongo_service.get_productos_collection().find_one({"_id": id_producto})
        except Exception as e:
            print("ERROR buscando producto de carrito:", e)

        if producto:
            inventario = producto.get("inventario", {})
            precio_actual = inventario.get("precioVenta")
            stock_actual = inventario.get("stockActual")
            stock_minimo = inventario.get("stockMinimo")

            if stock_actual is not None and stock_minimo is not None:
                stock_bajo = stock_actual <= stock_minimo

        precio_snapshot = item.get("precioUnitarioSnapshot")

        if precio_actual is not None and precio_snapshot is not None:
            precio_cambio = (precio_actual != precio_snapshot)

        items_ui.append({
            "idProducto": str(id_producto),
            "nombreProducto": item.get("nombreProducto") or (producto or {}).get("nombreProducto", ""),
            "cantidad": item.get("cantidad", 0),
            "precio_snapshot": precio_snapshot,
            "subtotal_snapshot": item.get("subtotalLineaSnapshot", 0),
            "seleccionado": item.get("seleccionado", True),
            "precio_actual": precio_actual,
            "precio_cambio": precio_cambio,
            "stock_actual": stock_actual,
            "stock_minimo": stock_minimo,
            "stock_bajo": stock_bajo,
        })

    # Flags globales para la vista
    hay_precio_cambiado = any(
        it.get("seleccionado") and it.get("precio_cambio")
        for it in items_ui
    )

    hay_stock_bajo_seleccionado = any(
        it.get("seleccionado") and it.get("stock_bajo")
        for it in items_ui
    )

    contexto = {
        "carrito": carrito,
        "items": items_ui,
        "hay_precio_cambiado": hay_precio_cambiado,
        "hay_stock_bajo_seleccionado": hay_stock_bajo_seleccionado,
    }

    return render(request, "carrito.html", contexto)



def carrito_agregar(request):
    """
    Agrega un producto al carrito del usuario.
    Espera POST con:
      - producto_id
      - cantidad
    """
    if request.method != "POST":
        return redirect("carrito")

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para agregar productos al carrito.")
        return redirect("login")

    producto_id = request.POST.get("producto_id", "").strip()
    cantidad_str = request.POST.get("cantidad", "1").strip()

    try:
        cantidad = int(cantidad_str)
    except ValueError:
        messages.error(request, "La cantidad debe ser un número entero.")
        return redirect("carrito")

    try:
        carrito = mongo_service.agregar_o_actualizar_item_carrito(
            usuario_id,
            producto_id,
            cantidad
        )
        messages.success(request, "Producto agregado al carrito correctamente.")
    except ValueError as ve:
        messages.error(request, str(ve))
    except errors.PyMongoError as e:
        print("ERROR Mongo al agregar al carrito:", e)
        messages.error(request, "Ocurrió un error al agregar el producto al carrito.")
    except Exception as e:
        print("ERROR inesperado al agregar al carrito:", e)
        messages.error(request, "Ocurrió un error inesperado al agregar el producto al carrito.")

    # Podrías redirigir a la página del producto o al carrito; por ahora al carrito:
    return redirect("carrito")

def carrito_actualizar_cantidad(request):
    """
    Actualiza la cantidad de un producto en el carrito.
    Espera POST con:
      - producto_id
      - cantidad
    Si cantidad = 0, elimina el ítem del carrito.
    """
    if request.method != "POST":
        return redirect("carrito")

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para modificar tu carrito.")
        return redirect("login")

    producto_id = request.POST.get("producto_id", "").strip()
    cantidad_str = request.POST.get("cantidad", "").strip()

    try:
        nueva_cantidad = int(cantidad_str)
    except ValueError:
        messages.error(request, "La cantidad debe ser un número entero.")
        return redirect("carrito")

    try:
        carrito = mongo_service.actualizar_cantidad_item_carrito(
            usuario_id,
            producto_id,
            nueva_cantidad
        )
        if nueva_cantidad == 0:
            messages.success(request, "Producto eliminado del carrito.")
        else:
            messages.success(request, "Cantidad actualizada en el carrito.")
    except ValueError as ve:
        messages.error(request, str(ve))
    except errors.PyMongoError as e:
        print("ERROR Mongo al actualizar cantidad:", e)
        messages.error(request, "Ocurrió un error al actualizar la cantidad.")
    except Exception as e:
        print("ERROR inesperado al actualizar cantidad:", e)
        messages.error(request, "Ocurrió un error inesperado al actualizar el carrito.")

    return redirect("carrito")

def carrito_actualizar_seleccion(request):
    """
    Marca un ítem del carrito como seleccionado o no.
    Espera POST con:
      - producto_id
      - seleccionado ( 'true' / 'false' )
    """
    if request.method != "POST":
        return redirect("carrito")

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para modificar tu carrito.")
        return redirect("login")

    producto_id = request.POST.get("producto_id", "").strip()
    seleccionado_str = request.POST.get("seleccionado", "true").strip().lower()
    seleccionado = (seleccionado_str == "true")

    try:
        carrito = mongo_service.actualizar_seleccion_item_carrito(
            usuario_id,
            producto_id,
            seleccionado
        )
        messages.success(request, "Carrito actualizado.")
    except ValueError as ve:
        messages.error(request, str(ve))
    except errors.PyMongoError as e:
        print("ERROR Mongo al actualizar selección:", e)
        messages.error(request, "Ocurrió un error al actualizar el carrito.")
    except Exception as e:
        print("ERROR inesperado al actualizar selección:", e)
        messages.error(request, "Ocurrió un error inesperado al actualizar el carrito.")

    return redirect("carrito")

from bson import ObjectId

def pedido_detalle(request, pedido_id: str):
    """
    Muestra el detalle de un pedido específico del usuario.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para ver tus pedidos.")
        return redirect("login")

    try:
        id_pedido = ObjectId(pedido_id)
        id_usuario = ObjectId(usuario_id)
    except Exception:
        messages.error(request, "Identificador de pedido no válido.")
        return redirect("landing")

    pedidos_col = mongo_service.get_pedidos_collection()

    try:
        pedido = pedidos_col.find_one({"_id": id_pedido})
    except Exception as e:
        print("ERROR al buscar pedido:", e)
        messages.error(request, "No fue posible cargar el pedido.")
        return redirect("landing")

    if not pedido:
        messages.error(request, "El pedido no existe.")
        return redirect("landing")

    if pedido.get("idUsuarioCliente") != id_usuario:
        messages.error(request, "No tienes permiso para ver este pedido.")
        return redirect("landing")

    items_ui = []
    for it in pedido.get("itemsPedido", []):
        items_ui.append({
        "nombreProducto": it.get("nombreProducto", ""),
        "cantidad": it.get("cantidad", 0),
        "precioUnitario": it.get("precioUnitario", 0),
        "subtotalLinea": it.get("subtotalLinea", 0),
    })

    pedido_id_str = str(pedido.get("_id"))  # 👈 NUEVO

    contexto = {
        "pedido": pedido,
        "items": items_ui,
        "pedido_id": pedido_id_str,          # 👈 NUEVO
}
    return render(request, "pedido_detalle.html", contexto)

def carrito_checkout(request):
    """
    Convierte el carrito actual del usuario en un Pedido.
    Usa solo los items seleccionados.
    """
    if request.method != "POST":
        return redirect("carrito")

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        messages.error(request, "Debes iniciar sesión para finalizar tu compra.")
        return redirect("login")

    # Por ahora tomamos estos valores del formulario o ponemos defaults:
    metodo_entrega = request.POST.get("metodo_entrega", "domicilio")
    metodo_pago = request.POST.get("metodo_pago", "efectivo")
    costo_envio_str = request.POST.get("costo_envio", "0")

    try:
        costo_envio = float(costo_envio_str)
    except ValueError:
        costo_envio = 0.0

    try:
        pedido = mongo_service.crear_pedido_desde_carrito(
            usuario_id,
            metodo_entrega,
            metodo_pago,
            costo_envio
        )
        pedido_id_str = str(pedido.get("_id"))
        messages.success(
            request,
            "Pedido creado correctamente."
        )
        return redirect("pedido_detalle", pedido_id=pedido_id_str)


    except ValueError as ve:
        # Errores de validación de negocio (sin stock, sin items seleccionados, etc.)
        messages.error(request, str(ve))
        return redirect("carrito")

    except errors.PyMongoError as e:
        print("ERROR Mongo al crear pedido desde carrito:", e)
        messages.error(
            request,
            "Ocurrió un error al crear el pedido. Intenta de nuevo más tarde."
        )
        return redirect("carrito")

    except Exception as e:
        print("ERROR inesperado en carrito_checkout:", e)
        messages.error(
            request,
            "Ocurrió un error inesperado al procesar tu compra."
        )
        return redirect("carrito")

def register_view(request):
    if request.method == "POST":
        # ── 1. Tomar datos del formulario ─────────────────────
        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        tipo_ident = request.POST.get("tipoIdentificacion", "").strip()
        num_ident = request.POST.get("numeroIdentificacion", "").strip()
        correo = request.POST.get("correoElectronico", "").strip().lower()  # 👈 normalizamos a minúsculas
        telefono = request.POST.get("telefono", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        print("DEBUG REGISTRO →", nombres, apellidos, tipo_ident, num_ident, correo, telefono)

        # ── 2. Validaciones básicas ───────────────────────────
        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "registro.html")

        if not all([nombres, apellidos, tipo_ident, num_ident, correo, telefono, password]):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, "registro.html")

        # ── 3. Verificar si ya existe usuario con ese correo ──
        if mongo_service.buscar_usuario_por_correo(correo):
            messages.error(request, "Ya existe un usuario registrado con ese correo electrónico.")
            return render(request, "registro.html")

        # ── 3.1 Verificar si ya existe usuario con ese documento ──
        if mongo_service.buscar_usuario_por_documento(tipo_ident, num_ident):
            messages.error(request, "Ya existe un usuario con ese número de identificación.")
            return render(request, "registro.html")

        # ── 4. Obtener idRol = Cliente ────────────────────────
        id_rol = mongo_service.obtener_id_rol("Cliente")
        if not id_rol:
            messages.error(request, "No se encontró el rol 'Cliente' en la base de datos.")
            return render(request, "registro.html")

        # ── 5. Construir documento según schema de Mongo ──────
        usuario_doc = {
            "nombres": nombres,
            "apellidos": apellidos,
            "tipoIdentificacion": tipo_ident,
            "numeroIdentificacion": num_ident,
            "correoElectronico": correo,
            "contraseñaHash": mongo_service.hash_password(password),
            "telefono": telefono,
            "idRol": id_rol,
            "estadoCuenta": "activo",
            "fechaRegistro": datetime.now(timezone.utc),
        }

        print("DEBUG DOC A INSERTAR →", usuario_doc)

        # ── 6. Insertar en Mongo ──────────────────────────────
        try:
            result = mongo_service.crear_usuario(usuario_doc)
            print("DEBUG INSERT OK → id:", result.inserted_id)
        except errors.DuplicateKeyError as e:
            # Si por alguna carrera se cuela un duplicado, caemos aquí
            print("DEBUG DUPLICATE ERROR →", e)
            messages.error(
                request,
                "Ya existe un usuario registrado con ese correo o documento."
            )
            return render(request, "registro.html")
        except Exception as e:
            print("DEBUG ERROR INSERTANDO →", e)
            messages.error(request, "Error al registrar el usuario. Inténtalo de nuevo.")
            return render(request, "registro.html")

        # ── 7. Listo, redirigimos al login ────────────────────
        messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect("login")

    # Método GET
    return render(request, "registro.html")


def custom_404(request, exception):
    """
    Vista para errores 404 (página no encontrada).
    """
    return render(request, "404.html", status=404)


def custom_500(request):
    """
    Vista para errores 500 (error interno del servidor).
    """
    return render(request, "500.html", status=500)

def demo_404(request):
    """
    Vista solo para DEMOSTRACIÓN de la página 404.
    """
    return render(request, "404.html", status=404)


def demo_error_500(request):
    """
    Vista solo para DEMOSTRACIÓN de la página 500.
    No lanza error real, solo renderiza la plantilla.
    """
    return render(request, "500.html", status=200)



