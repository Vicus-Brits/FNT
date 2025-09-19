from rest_framework import serializers 
from .models import  Session, Song

class SessionSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Session
        fields = '__all__'

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = '__all__'  


class ArtistSearchResponseSerializer(serializers.Serializer):
    results = serializers.JSONField()  


class ArtistSongsResponseSerializer(serializers.Serializer):
    results =  serializers.JSONField() 


class SongSearchResponseSerializer(serializers.Serializer):
    results = serializers.JSONField() 

class AddPlaylistVibeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    song_id = serializers.IntegerField(required=False)
    vibe_sequence = serializers.IntegerField(required=False)
    playlist_sequence =  serializers.IntegerField(required=False)


class GetSongsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    list_type = serializers.CharField()  #Plalist Vibe
    songs = SongSerializer(many=True)


class OrderPlaylistItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    playlist_sequence = serializers.IntegerField()


class OrderPlaylistResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    updated_songs = serializers.IntegerField()


class OrderVibeItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    vibe_sequence = serializers.IntegerField()


class OrderVibeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    updated_songs = serializers.IntegerField()


class RemoveListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    removed_song_id = serializers.IntegerField()
    reordered_songs = serializers.IntegerField()

class ClearVibeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    cleared_songs = serializers.IntegerField()

class RecommendResponseSerializer(serializers.Serializer):
    results = serializers.JSONField() 
