"""
Utility per l'hashing sicuro delle password, senza dipendere da Flask.
Usa PBKDF2-HMAC-SHA256 (modulo hashlib della libreria standard).
"""

import hashlib
import os
import hmac

ITERAZIONI = 260_000


def genera_hash_password(password: str) -> str:
    """Restituisce una stringa 'salt$hash' pronta per essere salvata nel database."""
    sale = os.urandom(16).hex()
    derivato = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sale), ITERAZIONI)
    return f"{sale}${derivato.hex()}"


def verifica_password(password: str, hash_salvato: str) -> bool:
    """Confronta una password in chiaro con l'hash salvato, in tempo costante."""
    try:
        sale, atteso = hash_salvato.split("$")
    except ValueError:
        return False
    derivato = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sale), ITERAZIONI)
    return hmac.compare_digest(derivato.hex(), atteso)
