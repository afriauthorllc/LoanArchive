import africastalking, logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms_via_provider(phone, message):
    print(f"[SMS DISABLED] Would send to {phone}: {message}")
    return True, "disabled", 0.0
    