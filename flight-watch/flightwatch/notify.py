"""Envio de alertas por e-mail via Gmail (SMTP com senha de app).

Variáveis de ambiente (no GitHub vêm dos secrets do repositório):
  GMAIL_APP_PASSWORD  senha de app de 16 letras gerada em myaccount.google.com/apppasswords
  ALERT_EMAIL         destinatário dos alertas
  GMAIL_USER          conta que envia (opcional; padrão = ALERT_EMAIL)

Uso para testar: python -m flightwatch.notify
"""
import os
import smtplib
import sys
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


class EmailNotConfigured(RuntimeError):
    pass


def _settings() -> tuple[str, str, str]:
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    to = os.environ.get("ALERT_EMAIL", "").strip()
    user = os.environ.get("GMAIL_USER", "").strip() or to
    if not password or not to:
        raise EmailNotConfigured("defina os secrets GMAIL_APP_PASSWORD e ALERT_EMAIL")
    return user, password, to


def send(subject: str, text: str, html: str | None = None,
         attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    """attachments: lista de (nome do arquivo, conteúdo, tipo MIME 'text/csv')."""
    user, password, to = _settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"flight-watch <{user}>"
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    for name, data, mime in attachments or []:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def main() -> None:
    try:
        send(
            "✈️ flight-watch: e-mail de teste",
            "Se você recebeu este e-mail, os alertas do flight-watch estão configurados.",
            "<p>Se você recebeu este e-mail, os alertas do <b>flight-watch</b> "
            "estão configurados. ✈️</p>",
        )
    except EmailNotConfigured as e:
        print(f"E-mail ainda não configurado: {e}")
        sys.exit(0)
    except smtplib.SMTPAuthenticationError as e:
        print(f"Gmail recusou o login (senha de app errada ou conta diferente): {e}")
        sys.exit(1)
    print("E-mail de teste enviado.")


if __name__ == "__main__":
    main()
