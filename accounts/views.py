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



