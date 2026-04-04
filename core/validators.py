from django.core.validators import FileExtensionValidator
from keel.security.scanning import FileSecurityValidator

# FileSecurityValidator checks extension whitelist (from settings), size, and malware.
# Image validator uses Django's built-in for the extension subset.
validate_document_file = FileSecurityValidator()
validate_image_file = FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'])
