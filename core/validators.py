from keel.security.scanning import FileSecurityValidator

# FileSecurityValidator checks KEEL_ALLOWED_UPLOAD_EXTENSIONS, KEEL_MAX_UPLOAD_SIZE,
# and runs ClamAV when KEEL_FILE_SCANNING_ENABLED is set.  Use for all uploads so
# image fields get the same size cap and AV scan as document fields.
validate_document_file = FileSecurityValidator()
validate_image_file = FileSecurityValidator()
