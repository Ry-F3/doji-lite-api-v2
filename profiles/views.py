from django.http import Http404
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Profile
from .serializers import ProfileSerializer
from doji_lite_api_v2.permissions import IsOwnerOrReadOnly


class ProfileList(APIView):
    # queryset = profile.objects.all
    def get(self, request):
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(
            profiles, many=True, context={'request': request})
        return Response(serializer.data)


class ProfileDetail(APIView):
    permission_classes = [IsOwnerOrReadOnly]
    serializer_class = ProfileSerializer

    def get_object(self, pk):
        try:
            profile = Profile.objects.get(pk=pk)
            self.check_object_permissions(self.request, profile)
            return profile
        except Profile.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(
            profile, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
