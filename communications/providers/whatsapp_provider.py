def send_whatsapp_via_provider(phone, template_name, params={}):
    print(f"[WHATSAPP MOCK] To {phone}: {template_name} {params}")
    return True, "mock-sent"
    
    
    