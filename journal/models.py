import uuid
from django.db import models


class Journal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, default="Our Journal")
    codeword_hash = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    player1_name = models.CharField(max_length=100, blank=True)
    player2_name = models.CharField(max_length=100, blank=True)
    date_ended = models.CharField(max_length=100, blank=True)
    map_notes = models.TextField(blank=True)
    map_image_left  = models.TextField(blank=True)  # base64 PNG — left map canvas
    map_image = models.TextField(blank=True)         # base64 PNG — right map canvas

    def __str__(self):
        return self.title


class Entry(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='entries')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Entry {self.created_at:%Y-%m-%d %H:%M}"
