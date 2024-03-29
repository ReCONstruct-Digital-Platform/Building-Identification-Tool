from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models.models import User, Vote

class VoteAdmin(admin.ModelAdmin):
    fields = ['eval_unit', 'user', 'date_added', 'data_modified']
    list_filter = ['eval_unit']
    search_fields = ['eval_unit', 'user', 'date_added', 'date_modified']

admin.site.register(User, UserAdmin)
admin.site.register(Vote, VoteAdmin)
