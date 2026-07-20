"""
Invio email agli iscritti della newsletter tramite un server SMTP
(es. Gmail, Outlook, o qualsiasi provider che fornisca un server SMTP).
Usa solo la libreria standard di Python: nessuna dipendenza aggiuntiva.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def invia_a_iscritti(host, porta, utente_smtp, password_smtp, mittente,
                      ssl_diretto, destinatari, oggetto, corpo):
    """Invia lo stesso messaggio a ogni destinatario con un invio separato
    (cosi nessun iscritto vede l'indirizzo email degli altri).

    Restituisce (numero_inviate, lista_errori). Ogni voce di lista_errori
    e una stringa "indirizzo: messaggio di errore".
    """
    inviate = 0
    errori = []

    for destinatario in destinatari:
        try:
            messaggio = MIMEMultipart()
            messaggio["From"] = mittente
            messaggio["To"] = destinatario
            messaggio["Subject"] = oggetto
            messaggio.attach(MIMEText(corpo, "plain", "utf-8"))

            if ssl_diretto:
                contesto = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, porta, context=contesto, timeout=15) as server:
                    server.login(utente_smtp, password_smtp)
                    server.sendmail(mittente, destinatario, messaggio.as_string())
            else:
                with smtplib.SMTP(host, porta, timeout=15) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(utente_smtp, password_smtp)
                    server.sendmail(mittente, destinatario, messaggio.as_string())

            inviate += 1
        except Exception as e:
            errori.append(f"{destinatario}: {e}")

    return inviate, errori
