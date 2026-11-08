import os, requests
from django.core.mail.backends.base import BaseEmailBackend

class ResendBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        api_key = os.environ.get('RESEND_API_KEY')
        for msg in email_messages:
            try:
                r = requests.post(
                    'https://api.resend.com/emails',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={
                        'from': msg.from_email,
                        'to': msg.to,
                        'subject': msg.subject,
                        'html': msg.body if msg.content_subtype == 'html' else None,
                        'text': msg.body,
                    },
                    timeout=10,
                )
                if r.status_code in (200, 201):
                    sent += 1
            except Exception:
                pass
        return sent
