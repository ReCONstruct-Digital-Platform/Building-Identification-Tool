from django.contrib import admin

# Register your models here.
from .models.models import EvalUnit

class BuildingAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Address Components', {'fields': ['street_number', 'street_name', 'locality', 'region', 'province', 'country', 'postal_code']}),
        ('Other Information', {'fields': ['cubf', 'date_added']}),
    ]
    # inlines=[ChoiceInline]
    list_filter = ['cubf']
    search_fields = ['address']


admin.site.register(EvalUnit, BuildingAdmin)