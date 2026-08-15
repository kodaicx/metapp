from fastapi import FastAPI, Query, Response
import imaplib
import email
import re

app = FastAPI()

IMAP_SERVER = "imap.firstmail.ltd"
IMAP_PORT = 993

def extract_code(body: str) -> str | None:
    match = re.search(r'\b\d{6}\b', body)
    return match.group(0) if match else None

@app.get("/code")
def get_code(mail_user: str = Query(...), mail_pass: str = Query(...)):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(mail_user, mail_pass)
        mail.select("INBOX")

        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        if not email_ids:
            mail.logout()
            return Response(content="NO_MAIL", media_type="text/plain")

        for e_id in email_ids[-5:][::-1]:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ["text/plain", "text/html"]:
                                try:
                                    body += part.get_payload(decode=True).decode(errors="ignore")
                                except:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    code = extract_code(body)
                    if code:
                        mail.logout()
                        return Response(content=code, media_type="text/plain")

        mail.logout()
        return Response(content="NO_CODE", media_type="text/plain")

    except Exception:
        return Response(content="ERROR", media_type="text/plain")
