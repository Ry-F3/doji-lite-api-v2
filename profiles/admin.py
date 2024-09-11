from django.contrib import admin
from .models import Profile


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('owner', 'first_name', 'last_name',
                    'created_at', 'updated_at')
    search_fields = ('owner__username', 'first_name', 'last_name', 'content')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    # Optionally, you can define how the profile details are displayed in the form
    fieldsets = (
        (None, {
            'fields': ('owner', 'first_name', 'last_name', 'content', 'image')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # def has_delete_permission(self, request, obj=None):
    #     """ Optionally restrict delete permission if needed. """
    #     return super().has_delete_permission(request, obj) and not obj.owner.is_superuser


admin.site.register(Profile, ProfileAdmin)
