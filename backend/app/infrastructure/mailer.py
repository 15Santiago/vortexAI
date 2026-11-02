import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class RegistrationMailError(RuntimeError):
    pass


def send_registration_code(email: str, code: str) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        raise RegistrationMailError("El servicio de correo no está configurado. Contacta al administrador.")

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise RegistrationMailError("La configuración del correo no es válida.") from exc

    message = EmailMessage()
    message["Subject"] = "Código temporal para crear tu cuenta VortexAI"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Tu código de verificación es {code}. Expira en 2 minutos. "
        "Si no solicitaste esta cuenta, ignora este mensaje."
    )
    username = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                if username:
                    server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("No se pudo enviar el código temporal de registro.")
        raise RegistrationMailError(
            "No se pudo enviar el correo de verificación. Intenta de nuevo más tarde."
        ) from exc
