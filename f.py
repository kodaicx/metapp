from fastapi import FastAPI, Query, Response
import imaplib
import email
import re

app = FastAPI()

IMAP_SERVER = "imap.firstmail.ltd"
IMAP_PORT = 993

def extract_meta_code(text: str) -> str | None:
    # 1. Öncelik: "Onay kodu", "code", "kod" kelimelerinden hemen sonra gelen 6 haneli sayı
    code_match = re.search(r'(?:onay kodu|code|kod)[\s:]*([0-9]{6})', text, re.IGNORECASE)
    if code_match:
        return code_match.group(1)
    
    # 2. Öncelik: Metin içindeki herhangi bir 6 haneli bağımsız sayı
    general_match = re.search(r'\b\d{6}\b', text)
    if general_match:
        return general_match.group(0)
        
    return None

@app.get("/code")
def get_code(mail_user: str = Query(...), mail_pass: str = Query(...)):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(mail_user, mail_pass)
        mail.select("INBOX")

        # Tüm mailleri sorgula
        status, messages = mail.search(None, 'ALL')
        if not messages[0]:
            mail.logout()
            return Response(content="NO_MAIL", media_type="text/plain")

        # Mailleri SAYISAL olarak büyükten küçüğe sırala (En yeni mail her zaman İLK elemandır)
        email_ids = [int(i) for i in messages[0].split()]
        email_ids.sort(reverse=True)

        # En yeni 5 maili incele
        for e_id in email_ids[:5]:
            _, msg_data = mail.fetch(str(e_id), '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    body = ""
                    # Öncelikle sade metin (plain text) kısmını almaya çalış
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                    break
                                except:
                                    pass
                            elif content_type == "text/html" and not body:
                                try:
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                except:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    code = extract_meta_code(body)
                    if code:
                        mail.logout()
                        return Response(content=code, media_type="text/plain")

        mail.logout()
        return Response(content="NO_CODE", media_type="text/plain")

    except Exception:
        return Response(content="ERROR", media_type="text/plain")
