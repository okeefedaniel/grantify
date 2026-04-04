from django.contrib import admin

from .models import (
    Agency, AuditLog, HarborProfile, Notification, Organization,
    OrganizationClaim, OrganizationContact,
)


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'org_type', 'city', 'state', 'is_active', 'is_high_priority', 'created_at')
    list_filter = ('org_type', 'is_active', 'is_high_priority', 'sam_registered', 'state')
    search_fields = ('name', 'ein', 'uei_number', 'duns_number')
    readonly_fields = ('id', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# Agency
# ---------------------------------------------------------------------------
@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        'abbreviation', 'name', 'department_code', 'can_be_grantor',
        'is_active', 'onboarded_at',
    )
    list_filter = ('is_active', 'can_be_grantor', 'can_be_grantee')
    search_fields = ('name', 'abbreviation', 'department_code')
    readonly_fields = ('id', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# HarborProfile
# ---------------------------------------------------------------------------
@admin.register(HarborProfile)
class HarborProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency', 'organization')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'entity_type', 'entity_id')
    list_filter = ('action', 'entity_type')
    search_fields = ('description', 'entity_type', 'entity_id')
    readonly_fields = (
        'id', 'user', 'action', 'entity_type', 'entity_id',
        'description', 'changes', 'ip_address', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
@admin.register(OrganizationClaim)
class OrganizationClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'organization__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user', 'organization', 'reviewed_by')


@admin.register(OrganizationContact)
class OrganizationContactAdmin(admin.ModelAdmin):
    list_display = ('organization', 'assigned_to', 'assigned_by', 'assigned_at')
    search_fields = ('organization__name', 'assigned_to__username')
    readonly_fields = ('id', 'assigned_at')
    raw_id_fields = ('organization', 'assigned_to', 'assigned_by')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'priority', 'is_read', 'created_at')
    list_filter = ('priority', 'is_read')
    search_fields = ('title', 'message')
    readonly_fields = ('id', 'created_at')
