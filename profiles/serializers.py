from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request:
            return request.user == obj.owner
        return False

    class Meta:
        model = Profile
        fields = [
            'id', 'owner', 'created_at', 'updated_at', 'first_name',
            'last_name', 'content', 'image', 'is_owner'
        ]

    