from django.shortcuts import render, redirect
from django.contrib import messages
from pymongo import errors
from datetime import datetime, timezone

from . import mongo_service

def landing(request):
    return render(request, 'paginaprincipal.html')

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("email", "").strip()
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


def register_view(request):
    if request.method == "POST":
        # ── 1. Tomar datos del formulario ─────────────────────
        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        tipo_ident = request.POST.get("tipoIdentificacion", "").strip()
        num_ident = request.POST.get("numeroIdentificacion", "").strip()
        correo = request.POST.get("correoElectronico", "").strip()
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
            messages.error(request, "Ya existe un usuario registrado con ese correo.")
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
            print("DEBUG DUPLICATE ERROR →", e)
            messages.error(
                request,
                "Ya existe un usuario registrado con ese correo o documento."
            )
            return render(request, "registro.html")
        except Exception as e:
            print("DEBUG ERROR INSERTANDO →", e)
            messages.error(request, f"Error al registrar el usuario: {e}")
            return render(request, "registro.html")

        # ── 7. Listo, redirigimos al login ────────────────────
        messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect("login")

    # Método GET
    return render(request, "registro.html")

