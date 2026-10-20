import re
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from users.models import Branch

# Validators
nin_validator = RegexValidator(
    regex=r'^[A-Z0-9]{14}$',
    message=_("NIN must be exactly 14 characters long containing only capital letters and numbers.")
)

# ✅ Accepts: +256770000000, 256770000000, 0770000000, 770000000
phone_validator = RegexValidator(
    regex=r'^(?:\+256|256|0)?7\d{8}$',
    message=_("Enter a valid UG number: 0770000000, 770000000, +256770000000 or 256770000000")
)

def validate_passport_photo(image):
    file_size = image.file.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(_(f"Max file size is {limit_mb}MB"))

def normalize_phone_number(phone):
    """Convert any format to +256XXXXXXXXX for storage consistency"""
    if not phone:
        return phone
    phone = re.sub(r'[\s\-()]', '', phone.strip())
    if phone.startswith('+256'):
        return phone
    if phone.startswith('256'):
        return f"+{phone}"
    if phone.startswith('0'):
        return f"+256{phone[1:]}"
    if phone.startswith('7') and len(phone) == 9:
        return f"+256{phone}"
    return phone

class Client(models.Model):
    passport_photo = models.ImageField(
        upload_to='clients/passports/',
        validators=[validate_passport_photo],
        help_text=_("Upload a clear passport-sized photo. Max size 2MB.")
    )

    # 👤 Changed to single field
    full_name = models.CharField(
        max_length=200,
        help_text=_("Client's full name e.g. John Doe")
    )
    
    nin = models.CharField(
        max_length=14,
        unique=True,
        validators=[nin_validator],
        verbose_name=_("NIN"),
        help_text=_("Enter the 14-character National Identification Number.")
    )

    # 📞 Flexible phone - any format
    telephone_number = models.CharField(
        max_length=15,
        validators=[phone_validator],
        help_text=_("0770000000, 770000000, +256770000000 or 256770000000")
    )
    
    village = models.CharField(max_length=100, blank=True)
    parish = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    landmark = models.TextField(blank=True, help_text=_("Directions to locate the client."))

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='clients')
    assigned_field_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_clients',
        limit_choices_to={'role': 'FIELD_OFFICER'}
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.nin:
            self.nin = self.nin.strip().upper()
            if not re.match(r'^[A-Z0-9]{14}$', self.nin):
                raise ValidationError({'nin': _("NIN must be a valid 14 character uppercase string.")})
        
        if self.full_name:
            self.full_name = ' '.join(self.full_name.strip().split()).title()
        
        if self.telephone_number:
            self.telephone_number = normalize_phone_number(self.telephone_number)

    def __str__(self):
        return f"{self.full_name} ({self.nin})"