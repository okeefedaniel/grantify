from django.contrib import admin

from .models import Award, AwardAmendment, AwardAttachment


class AwardAmendmentInline(admin.TabularInline):
    model = AwardAmendment
    extra = 0
    readonly_fields = ['created_at']


class AwardAttachmentInline(admin.TabularInline):
    model = AwardAttachment
    extra = 0
    readonly_fields = ('uploaded_at', 'size_bytes', 'content_type')
    fields = ('title', 'file', 'doc_category', 'source', 'visibility',
              'description', 'uploaded_by', 'uploaded_at')


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = [
        'award_number', 'title', 'grant_program', 'agency',
        'organization', 'status', 'award_amount', 'start_date', 'end_date',
    ]
    list_filter = ['status', 'agency', 'requires_match', 'created_at']
    search_fields = ['award_number', 'title', 'organization__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [AwardAmendmentInline, AwardAttachmentInline]
    date_hierarchy = 'created_at'


@admin.register(AwardAmendment)
class AwardAmendmentAdmin(admin.ModelAdmin):
    list_display = [
        'award', 'amendment_number', 'amendment_type',
        'status', 'requested_by', 'created_at',
    ]
    list_filter = ['amendment_type', 'status']
    search_fields = ['award__award_number', 'description']
    readonly_fields = ['created_at']


@admin.register(AwardAttachment)
class AwardAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        'award', 'title', 'doc_category', 'source', 'visibility',
        'uploaded_by', 'uploaded_at',
    )
    list_filter = ('source', 'doc_category', 'visibility')
    search_fields = ('title', 'description', 'filename', 'award__award_number')
    readonly_fields = (
        'uploaded_at', 'size_bytes', 'content_type', 'manifest_packet_uuid',
    )
