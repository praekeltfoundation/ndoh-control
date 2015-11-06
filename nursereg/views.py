from rest_framework import viewsets, generics, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User, Group
from .models import NurseSource, NurseReg
from .serializers import (UserSerializer, GroupSerializer,
                          NurseSourceSerializer, NurseRegSerializer)


class UserViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows users to be viewed or edited.
    """
    permission_classes = (IsAdminUser,)
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """
    permission_classes = (IsAdminUser,)
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class NurseSourceViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows sources to be viewed or edited.
    """
    permission_classes = (IsAdminUser,)
    queryset = NurseSource.objects.all()
    serializer_class = NurseSourceSerializer


class NurseRegPost(mixins.CreateModelMixin,  generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = NurseReg.objects.all()
    serializer_class = NurseRegSerializer

    def post(self, request, *args, **kwargs):
        # load the users sources - posting users should only have one source
        nurse_source = NurseSource.objects.get(user=self.request.user)
        request.data["nurse_source"] = nurse_source.id
        return self.create(request, *args, **kwargs)
