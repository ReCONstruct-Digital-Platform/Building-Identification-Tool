from django.contrib import admin

# Register your models here.
from .models import Building

# class ChoiceInline(admin.TabularInline):
#     model = Choice
#     # provide enough fields for x choices by default
#     extra = 2

class BuildingAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Address Components', {'fields': ['street_number', 'street_name', 'locality', 'region', 'province', 'country', 'postal_code']}),
        ('Other Information', {'fields': ['cubf', 'date_added']}),
    ]
    # inlines=[ChoiceInline]
    list_filter = ['cubf']
    search_fields = ['formatted_address']


admin.site.register(Building, BuildingAdmin)