from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class SplashAPIView(APIView):
    """
    API endpoint for the Splash Activity.
    Returns basic application configuration and version information.
    """
    def get(self, request, *args, **kwargs):
        data = {
            'app_name': 'COPD CDSS',
            'subtitle': 'AI-Assisted Oxygen Therapy',
            'version': 'v1.0.0',
            'usage_note': 'Clinical Use Only',
            'status': 'active',
            'maintenance_mode': False
        }
        return Response(data, status=status.HTTP_200_OK)
