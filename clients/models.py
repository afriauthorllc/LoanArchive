import re
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from users.models import Branch

nin_validator = RegexValidator(
    regex=r'^[A-Z0-9]{14}$',
    message=_("NIN must be exactly 14 characters long containing only capital letters and numbers.")
)
phone_validator = RegexValidator(
    regex=r'^\+256[0-9]{9}$',
    message=_("Phone number must be entered in the format: '+256770000000'.")
)

def validate_passport_photo(image):
    file_size = image.file.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(_(f"Max file size is {limit_mb}MB"))

class Client(models.Model):
    passport_photo = models.ImageField(
        upload_to='clients/passports/',
        validators=[validate_passport_photo],
        help_text=_("Upload a clear passport-sized photo. Max size 2MB.")
    )

    # KEEP OLD FIELDS - DO NOT DELETE YET
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # ADD THIS - REAL DB FIELD
    full_name = models.CharField(
        max_length=200, 
        blank=True, 
        db_index=True,
        help_text=_("Auto-filled from first + last name")
    )
    
    nin = models.CharField(max_length=14, unique=True, validators=[nin_validator], verbose_name=_("NIN"))
    telephone_number = models.CharField(max_length=13, validators=[phone_validator])
    
    village = models.CharField(max_length=100, blank=True)
    parish = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    landmark = models.TextField(blank=True)

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='clients')
    assigned_field_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_clients', limit_choices_to={'role': 'FIELD_OFFICER'}
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    # REMOVED @property full_name - now it's a real field
    @property
    def display_name(self):
        return self.full_name or f"{self.first_name} {self.last_name}"

    def clean(self):
        super().clean()
        if self.nin:
            self.nin = self.nin.strip().upper()
        # Auto-fill full_name before saving
        if self.first_name and self.last_name:
            self.full_name = f"{self.first_name.strip()} {self.last_name.strip()}".strip()

    def save(self, *args, **kwargs):
        # Always keep full_name in sync
        if self.first_name or self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.nin})"