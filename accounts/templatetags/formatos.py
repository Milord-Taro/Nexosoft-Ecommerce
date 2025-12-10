from django import template

register = template.Library()


@register.filter
def moneda_col(value):
    """
    Formatea un número como moneda colombiana:
    1000000 -> '1.000.000'
    """
    try:
        valor = float(value)
    except (TypeError, ValueError):
        return value

    entero = int(round(valor))
    # 1,000,000
    con_comas = f"{entero:,}"
    # Reemplaza comas por puntos -> 1.000.000
    return con_comas.replace(",", ".")
