from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count
from .models import Blog, Comment, Like
from .serializers import (RegisterSerializer,LoginSerializer, UserSerializer,BlogListSerializer, BlogDetailSerializer, CommentSerializer)

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

class AuthViewSet(viewsets.ViewSet):
  permission_classes=[AllowAny]
  
  
  def get_serializer_class(self):
    if self.action == 'login':
        return LoginSerializer
    return RegisterSerializer

  # POST /auth/register
  @swagger_auto_schema(request_body=RegisterSerializer)
  @action(detail=False, methods=['post'])
  def register(self, request):
    serializer=RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user=serializer.save()

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    return Response({
        "user": UserSerializer(user).data,
        "access": access,
        "refresh": str(refresh)
    }, status=status.HTTP_201_CREATED)
  
  @swagger_auto_schema(method='post', request_body=LoginSerializer)
  @action(detail=False, methods=['post'])
  def login(self,request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username=request.data.get('username')
    password=request.data.get('password')

    if not username or not password:
      return Response(
        {"details":"username or pass  missing"},
        status=status.HTTP_400_BAD_REQUEST

      )
    
    user=authenticate(username=username, password=password)
    
    if user is None:
      return Response(
        {"detail":"Invalid username or password"},
        status=status.HTTP_400_BAD_REQUEST
      )
    
    refresh = RefreshToken.for_user(user)
    return Response({
        "user": UserSerializer(user).data,
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }, status=status.HTTP_200_OK)
   
class BlogViewSet(viewsets.ModelViewSet):
  pagination_class=StandardResultsSetPagination
  queryset=Blog.objects.all().select_related('author')
  def get_permissions(self):
    if self.action in ['create','update','like', 'unlike', 'comment','partial_update','destroy']:
      return [IsAuthenticated()]
    return [IsAuthenticatedOrReadOnly()]
  
  def get_serializer_class(self):
    if self.action in ['comment']:
      return CommentSerializer
    if self.action in ['retrieve']:
      return BlogDetailSerializer
    return BlogListSerializer
    
  def get_queryset(self):
    qs=Blog.objects.all().select_related('author').annotate(likes_count=Count('likes'),comments_count=Count('comments')).order_by('-created_at')
    return qs
  
  def perform_create(self, serializer):
    serializer.save(author=self.request.user)

  @action(detail=True, methods=['post'],permission_classes=[IsAuthenticated])
  def like(self, request, pk=None):
    blog=self.get_object() #blog = Blog.objects.get(pk=pk)
    like, created=Like.objects.get_or_create(user=request.user,blog=blog)
    if created:
      return Response({'detail':'liked'}, status=status.HTTP_201_CREATED)
    return Response({'detail':'already liked'},status=status.HTTP_200_OK)
  
  @action(detail=True,methods=['post'],permission_classes=[IsAuthenticated])
  def unlike(self,request,pk=None):
    blog=self.get_object()
    try:
      like=Like.objects.get(user=request.user, blog=blog)
      like.delete()
      return Response({'detail':'unliked'}, status=status.HTTP_200_OK)
    except:
      return Response({'detail':'not liked yet'}, status=status.HTTP_400_BAD_REQUEST)
  
  # @swagger_auto_schema(
  #   method='post',
  #   request_body=openapi.Schema(
  #       type=openapi.TYPE_OBJECT,
  #       properties={
  #           'text': openapi.Schema(type=openapi.TYPE_STRING)
  #       }
  #   )
# )


  @swagger_auto_schema(method='post', request_body=CommentSerializer)
  @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
  def comment(self,request,pk=None):
    blog=self.get_object()
    serializer=CommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user, blog=blog)
    return Response(serializer.data, status=status.HTTP_201_CREATED)
  

class CommentViewSet(viewsets.ReadOnlyModelViewSet):
  pagination_class=StandardResultsSetPagination
  permission_classes=[IsAuthenticatedOrReadOnly] 
  serializer_class = CommentSerializer

  @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='blog_id',
                in_=openapi.IN_QUERY,
                description='Filter comments by Blog ID',
                type=openapi.TYPE_INTEGER,
                required=False,
            )
        ]
    )
  def list(self,request,*args, **kwargs):
    return super().list(request, *args, **kwargs)

  def get_queryset(self):
    blog_id = self.request.query_params.get('blog_id')
    if blog_id:
        return Comment.objects.filter(blog_id=blog_id).select_related('user','blog')
    return Comment.objects.all().select_related('user','blog')









  



  
