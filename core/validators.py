from keel.security.scanning import FileSecurityValidator

# Allowed extensions for document uploads.
# FileSecurityValidator checks extension whitelist, file size, and malware
# scanning (via ClamAV when KEEL_FILE_SCANNING_ENABLED is True in production).
DOCUMENT_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.rtf',
    '.odt', '.ods', '.ppt', '.pptx', '.png', '.jpg', '.jpeg', '.gif',
    '.tiff', '.zip', '.gz',
]
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

validate_document_file = FileSecurityValidator(allowed_extensions=DOCUMENT_EXTENSIONS)
validate_image_file = FileSecurityValidator(allowed_extensions=IMAGE_EXTENSIONS)
