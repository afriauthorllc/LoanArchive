from ..models import SMSLog
from ..providers.sms_provider import send_sms_via_provider

def send_payment_confirmation(client, loan, amount=None):
    amount = amount or loan.last_payment_amount
    msg = f"Dear {client.first_name}, we received UGX {amount} for loan {loan.loan_number}. Balance: UGX {loan.balance}. Thank you - {client.branch.name}"
    
    log = SMSLog.objects.create(
        branch=client.branch, client=client, phone=client.phone,
        message=msg, type='payment_received'
    )
    success, response, cost = send_sms_via_provider(client.phone, msg)
    log.status = 'sent' if success else 'failed'
    log.provider_response = response
    log.cost = cost
    log.save()
    return log
    
    