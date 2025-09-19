from django.db import models

class Session(models.Model):
    session_id = models.CharField(max_length=128, primary_key=True)
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.session_id
    
class Song(models.Model):
    id = models.BigAutoField(primary_key=True)  # active sessions only
    session = models.ForeignKey(Session, on_delete=models.CASCADE)  # which session song belongs to
    artist_id = models.CharField(max_length=128)  # artist_id
    artist_name = models.CharField(max_length=255)
    song_id = models.CharField(max_length=128)
    song_title = models.CharField(max_length=255)
    song_popularity = models.IntegerField(default=0)
    vibe_sequence = models.IntegerField(null=True, blank=True)  # priority in which this influences song selection
    playlist_sequence = models.IntegerField(null=True, blank=True)  # sequence in which song are played
    playlist_hist_sequence = models.IntegerField(null=True, blank=True)  # song history sequence
    is_playing = models.BooleanField(default=False)  # song playing
    is_played = models.BooleanField(default=False)  # song played
    
    def __str__(self):
        return self.song_title