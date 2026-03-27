from django import template

register = template.Library()

@register.filter
def getattribute(obj, attr):
    return getattr(obj, attr, None)

@register.filter
def stock_en_sucursal(variante, sucursal_id):
    from api.models import InventarioSucursal
    if not variante or not sucursal_id:
        return 0
    inv = InventarioSucursal.objects.filter(sucursal_id=sucursal_id, variante=variante).first()
    return inv.stock if inv else 0
@register.filter
def is_boolean(value):
    return isinstance(value, bool)
