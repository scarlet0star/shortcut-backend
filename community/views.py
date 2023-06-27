from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from rest_framework.decorators import action
from yourfan.permissions import  UserMatch,ISNotBannedUser,IsStaff
from rest_framework.response import Response
from rest_framework import status
from .models import Board, Post, Comment
from .serializers import *
from django.contrib.auth import get_user_model

class BoardModelViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    lookup_field = 'custom_url'
    
    def get_permissions(self):
        if self.action in ["destroy", "create"]:
            permission_classes = [IsAdminUser]
        elif self.action in ["partial_update","update","ban"]:
            permission_classes = [IsStaff|IsAdminUser]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        serializer = BoardCreateSerializer(data=request.data)
        channel = get_object_or_404(Channel, channel_id=request.data['channel_id'])
        if serializer.is_valid():
            serializer.save(channel=channel)
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        custom_url = self.kwargs.get("custom_url")
        board = get_object_or_404(Board, custom_url=custom_url)
        board.is_active = False
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        if "title" in request.data:
            return Response(
                {"message": "게시판 명칭은 임의대로 변경이 불가합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=True, methods=["POST"])
    def subscribe(self,request,custom_url=None):
        board = self.get_object()
        
        if board.subscribers.filter(id=request.user.id).exist():
            board.subscribers.remove(request.user)
            return Response({"message":"unsubscribed..."},status=status.HTTP_200_OK)
        else:
            board.subscribers.add(request.user)
            return Response({"message":"subscribed..."},status=status.HTTP_200_OK)
    
    @action(detail=True,methods=["POST"])
    def ban(self,request,custom_url=None):
        target = get_user_model().objects.get(pk=request.data["user_id"])
        board = self.get_object()

        if board.banned_users.filter(id=target.id).exists(): 
            board.banned_users.remove(target)
            return Response({"message":"ban release completed"},status=status.HTTP_200_OK)
        else:
            board.banned_users.add(target)
            return Response({"message":"ban completed"},status=status.HTTP_200_OK)

class BoardPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, ISNotBannedUser]

    def get_queryset(self):
        custom_url = self.kwargs.get('board_custom_url')
        board = Board.objects.get(custom_url=custom_url)
        return Post.objects.filter(board=board)

class PostModelViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return PostSerializer
        return PostNotGetSerializer

    def get_permissions(self):
        if self.action in ["destroy", "update", "partial_update"]:
            permission_classes = [UserMatch | IsStaff]
        else:
            permission_classes = [ISNotBannedUser,IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def partial_update(self, request, *args, **kwargs):
        if "board" in request.data:
            return Response(
                {"message": "포스트 수정시 게시판은 임의대로 변경이 불가합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=True, methods=["POST "])
    def bookmark(self,request,pk=None):
        post = self.get_object()
        post.bookmarked_by.add(request.user)
        
        return Response({"status":"bookmarked..."},status=status.HTTP_200_OK)


class CommentModelViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return CommentSerializer
        return CommentNotGetSerializer

    def get_permissions(self):
        if self.action in ["destroy", "update", "partial_update"]:
            permission_classes = [UserMatch | IsStaff]
        else:
            permission_classes = [ISNotBannedUser,IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def partial_update(self, request, *args, **kwargs):
        if "post" in request.data:
            return Response(
                {"message": "게시글은 임의대로 변경이 불가합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)