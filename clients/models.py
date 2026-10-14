import re
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from users.models import Branch # Assumes Branch is in the same file; adjust import if needed

# Validators for data integrity
nin_validator = RegexValidator(
    regex=r'^[A-Z0-9]{14}$',
    message=_("NIN must be exactly 14 characters long containing only capital letters and numbers.")
)

phone_validator = RegexValidator(
    regex=r'^\+256[0-9]{9}$',
    message=_("Phone number must be entered in the format: '+256770000000'.")
)

def validate_passport_photo(image):
    """Restricts file uploads to a maximum of 2MB to save server storage."""
    file_size = image.file.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(_(f"Max file size is {limit_mb}MB"))

class Client(models.Model):
    """
    Represents a loan applicant/borrower in the system.
    """
    # 📸 Passport Photo
    passport_photo = models.ImageField(
        upload_to='clients/passports/',
        validators=[validate_passport_photo],
        help_text=_("Upload a clear passport-sized photo. Max size 2MB.")
    )

    # 👤 Personal Details
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # 🪪 Ugandan National Identification Number (NIN)
    nin = models.CharField(
        max_length=14,
        unique=True,
        validators=[nin_validator],
        verbose_name=_("NIN"),
        help_text=_("Enter the 14-character National Identification Number.")
    )

    # 📞 Contact Details
    telephone_number = models.CharField(
        max_length=13,
        validators=[phone_validator],
        help_text=_("Format: +256XXXXXXXXX")
    )
    
    # 📍 Physical Address Details
    village = models.CharField(max_length=100, blank=True)
    parish = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100)
    landmark = models.TextField(
        blank=True, 
        help_text=_("Directions, close buildings, or descriptions to help the Field Officer locate the client.")
    )

    # 🏢 System Hierarchy Alignment
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='clients',
        help_text=_("The home branch where this client's profile and loans are handled.")
    )
    assigned_field_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_clients',
        limit_choices_to={'role': 'FIELD_OFFICER'},
        help_text=_("The field officer responsible for evaluating and collecting from this client.")
    )

    # ⏳ Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        super().clean()
        # Clean spelling / formatting for the NIN automatically before saving
        if self.nin:
            self.nin = self.nin.strip().upper()
            if not re.match(r'^[A-Z0-9]{14}$', self.nin):
                raise ValidationError({'nin': _("NIN must be a valid 14 character uppercase string.")})

    def __str__(self):
        return f"{self.full_name} ({self.nin})"
