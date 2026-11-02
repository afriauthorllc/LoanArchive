from django.contrib.auth import get_user_model
from ..models import StaffNotification

User = get_user_model()

def notify_all_branch_staff(client, loan=None, type='payment_received', title=None, message=None, link=None):
    # Your User has branch field
    staff_qs = User.objects.filter(branch=client.branch, is_active=True)
    
    client_name = getattr(client, 'full_name', str(client))
    loan_id = loan.id if loan else ''

    defaults = {
        'payment_received': (f"Payment Received", f"{client_name} paid. Loan #{loan_id}", f"/loans/{loan_id}/" if loan else f"/clients/{client.id}/"),
        'loan_cleared': (f"Loan Fully Paid", f"{client_name} cleared Loan #{loan_id}", f"/clients/{client.id}/"),
        'qualifies_for_loan': (f"Qualifies For Loan", f"{client_name} now qualifies for another loan - previous cleared", f"/clients/{client.id}/"),
    }
    
    def_title, def_msg, def_link = defaults.get(type, (title, message, link))

    for staff in staff_qs:
        StaffNotification.objects.create(
            recipient=staff, branch=client.branch, client=client, loan=loan,
            title=title or def_title, 
            message=message or def_msg, 
            type=type, 
            link=link or def_link
        )
    print(f"[NOTIFY] Created {staff_qs.count()} notifications for {type}")

def notify_superuser(branch, subscription=None, type='subscription_renewed'):
    superusers = User.objects.filter(is_superuser=True)
    for su in superusers:
        StaffNotification.objects.create(
            recipient=su, branch=branch,
            title="Subscription Renewed",
            message=f"{branch.name} renewed subscription",
            type=type, link=f"/branches/{branch.id}/"
        )
        
        