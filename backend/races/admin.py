from django.contrib import admin

from .models import Paragraph, Race, RaceParticipant


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
    readonly_fields = ["created_at", "started_at", "race_text"]


@admin.register(RaceParticipant)
class RaceParticipantAdmin(admin.ModelAdmin):
    list_display = ["id", "race", "player", "joined_at", "finished_at", "wpm", "accuracy"]
    list_select_related = ["race", "player"]
    search_fields = ["player__username"]
    readonly_fields = ["joined_at", "typed_text", "revision", "finished_at", "elapsed_seconds", "wpm", "accuracy"]
