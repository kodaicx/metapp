from fastapi import FastAPI, Query, Response
import imaplib
import email
import re
import html

app = FastAPI()

IMAP_SERVER = "imap.firstmail.ltd"
IMAP_PORT = 993

def clean_html(raw_html: str) -> str:
    # HTML etiketlerini ve özel karakterleri temizle
    clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
    return html.unescape(clean_text)

def extract_meta_code(text: str) -> str | None:
    # 1. Onay kodu / Code anahtar kelimesinden hemen sonra gelen 6 haneli kod
    match = re.search(r'(?:onay kodu|confirmation code|code|kod)[\s:]*([0-9]{6})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # 2. Metindeki ilk bağımsız 6 haneli sayı
    match_general = re.search(r'\b\d{6}\b', text)
    if match_general:
        return match_general.group(0)
        
    return None

@app.get("/code")
def get_code(mail_user: str = Query(...), mail_pass: str = Query(...)):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(mail_user, mail_pass)
        mail.select("INBOX")

        status, messages = mail.search(None, 'ALL')
        if not messages[0]:
            mail.logout()
            return Response(content="NO_MAIL", media_type="text/plain")

        # En yeni mail ilk sırada olacak şekilde sırala
        email_ids = [int(i) for i in messages[0].split()]
        email_ids.sort(reverse=True)

        for e_id in email_ids[:5]:
            _, msg_data = mail.fetch(str(e_id), '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ["text/plain", "text/html"]:
                                try:
                                    payload = part.get_payload(decode=True).decode(errors="ignore")
                                    body += " " + payload
                                except:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    # HTML kodlarını temizle
                    text_only = clean_html(body)
                    code = extract_meta_code(text_only)
                    
                    if code:
                        mail.logout()
                        return Response(content=code, media_type="text/plain")

        mail.logout()
        return Response(content="NO_CODE", media_type="text/plain")

    except Exception:
        return Response(content="ERROR", media_type="text/plain")
