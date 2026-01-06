class BusinessRuleError(Exception):
    """Reglas de negocio violadas."""
    pass

class NotFoundError(Exception):
    """Recurso no encontrado."""
    pass
