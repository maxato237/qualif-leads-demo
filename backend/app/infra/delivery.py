class DeliveryError(Exception):
    """Un canal de sortie (Sheet, email) a échoué. Le lead reste qualifié."""
