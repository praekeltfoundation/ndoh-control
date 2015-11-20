from rest_framework import viewsets, generics, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import NurseSource, NurseReg
from .serializers import (NurseSourceSerializer, NurseRegSerializer)


class NurseSourceViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows sources to be viewed or edited.
    """
    permission_classes = (IsAdminUser,)
    queryset = NurseSource.objects.all()
    serializer_class = NurseSourceSerializer


class NurseRegViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows registrations to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = NurseReg.objects.all()
    serializer_class = NurseRegSerializer


class NurseRegPost(mixins.CreateModelMixin,  generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = NurseReg.objects.all()
    serializer_class = NurseRegSerializer

    def post(self, request, *args, **kwargs):
        # load the users sources - posting users should only have one source
        nurse_source = NurseSource.objects.get(user=self.request.user)
        request.data["nurse_source"] = nurse_source.id
        return self.create(request, *args, **kwargs)
