from ..models import WhatsAppLog
from ..providers.whatsapp_provider import send_whatsapp_via_provider

def send_whatsapp_receipt(client, amount):
    log = WhatsAppLog.objects.create(client=client, phone=client.phone, template_name='payment_receipt', message=f"Payment of {amount} received")
    success, resp = send_whatsapp_via_provider(client.phone, 'payment_receipt', {'amount': amount})
    log.status = 'sent' if success else 'failed'
    log.save()
    
