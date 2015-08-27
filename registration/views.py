from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Source, Registration
from .serializers import SourceSerializer, RegistrationSerializer


class SourceViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows sources to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Source.objects.all()
    serializer_class = SourceSerializer


class RegistrationViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows registrations to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
