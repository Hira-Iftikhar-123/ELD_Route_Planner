from rest_framework import serializers


class TripPlanSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)

    def validate_current_location(self, value: str) -> str:
        return value.strip()

    def validate_pickup_location(self, value: str) -> str:
        return value.strip()

    def validate_dropoff_location(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs):
        pickup = attrs["pickup_location"].casefold()
        dropoff = attrs["dropoff_location"].casefold()
        if pickup == dropoff:
            raise serializers.ValidationError(
                {"dropoff_location": "Pickup and dropoff must be different cities."}
            )
        return attrs