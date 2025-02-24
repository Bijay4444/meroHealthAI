from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, CaregiverRelationship, NotificationPreference
from django.db.models import Q
from .serializers import (
    CustomUserSerializer,
    CustomUserCreateSerializer,
    CaregiverRelationshipSerializer,
    NotificationPreferenceSerializer,
)

from .permissions import IsCaregiverPermission, HasCaregiverPermission

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomUserSerializer

    def get_object(self):
        return self.request.user


class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        try:
            user = CustomUser.objects.get(email=email)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                }, status=status.HTTP_200_OK)
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)

class CaregiverListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get relationships where user is either the patient or caregiver
        relationships = CaregiverRelationship.objects.filter(
            Q(user=request.user) | Q(caregiver=request.user)
        )
        serializer = CaregiverRelationshipSerializer(relationships, many=True)
        return Response(serializer.data)

class CaregiverAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            caregiver_email = request.data.get('caregiver_email')
            relationship_type = request.data.get('relationship', 'FAMILY')
            permission_level = request.data.get('permission_level', 'VIEW')
            
            # Verify user is a patient
            if request.user.user_type != 'PATIENT':
                return Response(
                    {"error": "Only patients can add caregivers"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find caregiver by email
            try:
                caregiver = CustomUser.objects.get(
                    email=caregiver_email,
                    user_type='CAREGIVER'
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {"error": "No caregiver found with this email"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if relationship already exists
            if CaregiverRelationship.objects.filter(
                user=request.user,
                caregiver=caregiver
            ).exists():
                return Response(
                    {"error": "This caregiver is already linked to your account"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create relationship
            relationship = CaregiverRelationship.objects.create(
                user=request.user,
                caregiver=caregiver,
                relationship=relationship_type,
                permission_level=permission_level,
                emergency_contact=request.data.get('emergency_contact', False),
                notes=request.data.get('notes', '')
            )

            serializer = CaregiverRelationshipSerializer(relationship)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    
class CaregiverUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            relationship = CaregiverRelationship.objects.get(pk=pk)
            # Only allow updates if user is the patient
            if relationship.user != request.user:
                return Response(
                    {"error": "Not authorized to modify this relationship"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = CaregiverRelationshipSerializer(
                relationship,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CaregiverRelationship.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    def delete(self, request, pk):
        try:
            relationship = CaregiverRelationship.objects.get(
                pk=pk,
                user=request.user  # Ensure only the patient can delete their caregivers
            )
            relationship.delete()
            return Response(
            {"message": "Caregiver relationship deleted successfully"},
            status=status.HTTP_200_OK
            )
        except CaregiverRelationship.DoesNotExist:
            return Response(
                {"error": "Relationship not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preferences = NotificationPreference.objects.filter(user=request.user)
        serializer = NotificationPreferenceSerializer(preferences, many=True)
        return Response(serializer.data)

class NotificationPreferenceUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NotificationPreferenceSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#caregiver login
class CaregiverRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()
        data['user_type'] = 'CAREGIVER'
        serializer = CustomUserCreateSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CaregiverDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsCaregiverPermission]

    def get(self, request):
        if request.user.user_type != 'CAREGIVER':
            return Response(
                {"error": "Only caregivers can access this view"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationships = CaregiverRelationship.objects.filter(
            caregiver=request.user
        ).select_related('user')
        
        patients_data = []
        for rel in relationships:
            patient_data = {
                "patient_id": rel.user.id,
                "patient_name": rel.user.name,
                "patient_email": rel.user.email,
                "relationship": rel.relationship,
                "can_view_adherence": rel.can_view_adherence,
                "can_modify_schedule": rel.can_modify_schedule
            }
            patients_data.append(patient_data)
            
        return Response(patients_data)

