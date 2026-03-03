from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Admin
from .serializers import AdminLoginSerializer, AdminSignupSerializer
from doctor.models import Doctor
from staff.models import Staff


class AdminLoginAPIView(APIView):
    """
    POST /api/admin/login/
    Body: { "email": "...", "password": "..." }
    """
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            try:
                admin = Admin.objects.get(email=email)
                if not admin.is_active:
                    return Response({"error": "Your account has been deactivated."}, status=status.HTTP_403_FORBIDDEN)
                if admin.check_password(password):
                    return Response({
                        "message": "Login successful",
                        "role": "admin",
                        "admin_id": admin.id,
                        "name": admin.name,
                        "email": admin.email,
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)
            except Admin.DoesNotExist:
                return Response({"error": "No admin account found with this email."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSignupAPIView(APIView):
    """
    POST /api/admin/signup/
    Body: { "name": "...", "email": "...", "password": "..." }
    """
    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if Admin.objects.filter(email=email).exists():
                return Response({"error": "An admin account with this email already exists."}, status=status.HTTP_409_CONFLICT)
            admin = Admin.objects.create(
                name=serializer.validated_data['name'],
                email=email,
                password=serializer.validated_data['password'],
            )
            return Response({
                "message": "Admin account created successfully.",
                "admin_id": admin.id,
                "name": admin.name,
                "email": admin.email,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDashboardAPIView(APIView):
    """
    GET /api/admin/dashboard/
    Returns summary stats: total doctors, total staff, pending approvals.
    """
    def get(self, request):
        total_doctors = Doctor.objects.count()
        total_staff = Staff.objects.count()
        pending_doctors = Doctor.objects.filter(is_approved=False).count()
        pending_staff = Staff.objects.filter(is_approved=False).count()
        total_pending = pending_doctors + pending_staff
        return Response({
            "total_doctors": total_doctors,
            "total_staff": total_staff,
            "total_pending_approvals": total_pending,
            "pending_doctors": pending_doctors,
            "pending_staff": pending_staff,
        }, status=status.HTTP_200_OK)


class AdminProfileAPIView(APIView):
    """
    GET  /api/admin/profile/?admin_id=<id>
    POST /api/admin/profile/  Body: { "admin_id":..., "name":... }
    """
    def get(self, request):
        admin_id = request.query_params.get('admin_id')
        if not admin_id:
            return Response({"error": "admin_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            admin = Admin.objects.get(id=admin_id)
            return Response({
                "admin_id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "created_at": admin.created_at,
            }, status=status.HTTP_200_OK)
        except Admin.DoesNotExist:
            return Response({"error": "Admin not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        admin_id = request.data.get('admin_id')
        if not admin_id:
            return Response({"error": "admin_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            admin = Admin.objects.get(id=admin_id)
            admin.name = request.data.get('name', admin.name)
            admin.save()
            return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)
        except Admin.DoesNotExist:
            return Response({"error": "Admin not found."}, status=status.HTTP_404_NOT_FOUND)


class AdminManageDoctorsAPIView(APIView):
    """
    GET  /api/admin/doctors/         — list all doctors
    POST /api/admin/doctors/         — toggle approve/deactivate
    """
    def get(self, request):
        doctors = Doctor.objects.all().values(
            'id', 'name', 'email', 'specialization', 'phone_number', 'is_approved', 'is_active', 'created_at'
        )
        return Response({"doctors": list(doctors)}, status=status.HTTP_200_OK)


class AdminRemoveDoctorAPIView(APIView):
    """
    POST /api/admin/doctors/<doctor_id>/remove/
    Deactivates a doctor account.
    """
    def post(self, request, doctor_id):
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            doctor.is_active = False
            doctor.save()
            return Response({"message": f"Doctor '{doctor.name}' access has been revoked."}, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)


class AdminManageStaffAPIView(APIView):
    """
    GET  /api/admin/staff/           — list all staff
    """
    def get(self, request):
        staff_list = Staff.objects.all().values(
            'id', 'name', 'email', 'department', 'phone_number', 'is_approved', 'is_active', 'created_at'
        )
        return Response({"staff": list(staff_list)}, status=status.HTTP_200_OK)


class AdminRemoveStaffAPIView(APIView):
    """
    POST /api/admin/staff/<staff_id>/remove/
    Deactivates a staff account.
    """
    def post(self, request, staff_id):
        try:
            staff = Staff.objects.get(id=staff_id)
            staff.is_active = False
            staff.save()
            return Response({"message": f"Staff '{staff.name}' has been removed from the system."}, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)


class AdminApprovalsAPIView(APIView):
    """
    GET  /api/admin/approvals/   — list all pending approval requests
    """
    def get(self, request):
        pending_doctors = list(Doctor.objects.filter(is_approved=False, is_active=True).values(
            'id', 'name', 'email', 'specialization', 'created_at'
        ))
        for d in pending_doctors:
            d['role'] = 'doctor'

        pending_staff = list(Staff.objects.filter(is_approved=False, is_active=True).values(
            'id', 'name', 'email', 'department', 'created_at'
        ))
        for s in pending_staff:
            s['role'] = 'staff'

        return Response({
            "pending_approvals": pending_doctors + pending_staff,
            "total_pending": len(pending_doctors) + len(pending_staff),
        }, status=status.HTTP_200_OK)


class AdminApproveRequestAPIView(APIView):
    """
    POST /api/admin/approvals/<request_id>/approve/
    Body: { "role": "doctor" | "staff" }
    """
    def post(self, request, request_id):
        role = request.data.get('role')
        if role == 'doctor':
            try:
                doctor = Doctor.objects.get(id=request_id)
                doctor.is_approved = True
                doctor.save()
                return Response({"message": f"Dr. {doctor.name} has been approved."}, status=status.HTTP_200_OK)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
        elif role == 'staff':
            try:
                staff = Staff.objects.get(id=request_id)
                staff.is_approved = True
                staff.save()
                return Response({"message": f"{staff.name} has been approved."}, status=status.HTTP_200_OK)
            except Staff.DoesNotExist:
                return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Invalid role. Must be 'doctor' or 'staff'."}, status=status.HTTP_400_BAD_REQUEST)


class AdminRejectRequestAPIView(APIView):
    """
    POST /api/admin/approvals/<request_id>/reject/
    Body: { "role": "doctor" | "staff" }
    Deactivates the account.
    """
    def post(self, request, request_id):
        role = request.data.get('role')
        if role == 'doctor':
            try:
                doctor = Doctor.objects.get(id=request_id)
                doctor.is_active = False
                doctor.save()
                return Response({"message": f"Dr. {doctor.name}'s request has been rejected."}, status=status.HTTP_200_OK)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
        elif role == 'staff':
            try:
                staff = Staff.objects.get(id=request_id)
                staff.is_active = False
                staff.save()
                return Response({"message": f"{staff.name}'s request has been rejected."}, status=status.HTTP_200_OK)
            except Staff.DoesNotExist:
                return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Invalid role. Must be 'doctor' or 'staff'."}, status=status.HTTP_400_BAD_REQUEST)
