from django.contrib import admin

from .models import Paragraph, Race


@admin.register(Paragraph)
class ParagraphAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at"]
    search_fields = ["title", "text"]


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = ["id", "paragraph", "host", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["paragraph__title", "host__username"]
    list_select_related = ["paragraph", "host"]
    readonly_fields = ["created_at"]
