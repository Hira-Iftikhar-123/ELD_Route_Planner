from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import TripPlanSerializer
from .services.planner import TripPlannerError, plan_trip


@api_view(["GET"])
def health(_request):
    return Response(
        {
            "status": "ok",
            "service": "eld-route-planner",
            "geolocation_key_configured": bool(settings.GEOLOCATION_API_KEY),
        }
    )


@api_view(["POST"])
def plan_trip_view(request):
    serializer = TripPlanSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        result = plan_trip(
            current_location=data["current_location"],
            pickup_location=data["pickup_location"],
            dropoff_location=data["dropoff_location"],
            cycle_used_hours=data["cycle_used_hours"],
        )
    except TripPlannerError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"detail": "Unexpected error while planning trip."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(result)