from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Admin
from .serializers import AdminLoginSerializer, AdminSignupSerializer
from doctor.models import Doctor
from doctor.serializers import DoctorListSerializer, DoctorDetailSerializer
from staff.models import Staff
from staff.serializers import StaffListSerializer, StaffDetailSerializer
from django.contrib.auth.models import User

from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from django.contrib.auth.hashers import make_password


class RegisterAPIView(APIView):

    def post(self, request):

        name = request.data.get("name")
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role")

        if not name or not email or not password or not role:
            return Response(
                {"error": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        hashed_password = make_password(password)

        if role == "doctor":
            Doctor.objects.create(
    name=name,
    email=email,
    password=hashed_password,
    is_approved=False,
    is_active=False
)

        elif role == "staff":
            Staff.objects.create(
                name=name,
                email=email,
                password=hashed_password,
                is_approved=False,
                is_active=False
            )

        else:
            return Response(
                {"error": "Invalid role"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Registration successful. Waiting for admin approval."},
            status=status.HTTP_201_CREATED
        )
    
class AdminLoginAPIView(APIView):
    """
    POST /api/admin/login/
    Body:
    {
        "username": "admin",
        "password": "admin123"
    }
    """

    def post(self, request):

        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is not None and (user.is_staff or user.is_superuser):

            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Admin login successful",
                "role": "admin",
                "admin_id": user.id,
                "username": user.username,
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid admin credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )


class AdminProfileDetailsAPIView(APIView):
    """
    GET /api/admin/profile/
    Returns admin details from auth_user table (id=7).
    """
    def get(self, request):
        try:
            admin = User.objects.get(id=7)
            return Response({
                "admin_id": admin.id,
                "username": admin.username,
                "name": admin.username,
                "email": admin.email,
                "role": "Super Admin",
                "permissions": "Full System Access"
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)

class AdminDashboardAPIView(APIView):
    """
    GET /api/admin-user/dashboard/
    Returns dashboard statistics.
    """

    def get(self, request):

        total_doctors = Doctor.objects.count()
        total_staff = Staff.objects.count()

        pending_doctors = Doctor.objects.filter(is_approved=False).count()
        pending_staff = Staff.objects.filter(is_approved=False).count()
        total_pending_requests = pending_doctors + pending_staff

        return Response({
            "total_doctors": total_doctors,
            "total_staff": total_staff,
            "pending_doctors": pending_doctors,
            "pending_staff": pending_staff,
            "total_pending_requests": total_pending_requests
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
    GET  /api/admin/doctors/         — list all doctors00

    
    POST /api/admin/doctors/         — toggle approve/deactivate
    """
    def get(self, request):
        doctors = Doctor.objects.all().values(
            'id', 'name', 'email', 'specialization', 'phone_number', 'is_approved', 'is_active', 'created_at'
        )
        return Response({"doctors": list(doctors)}, status=status.HTTP_200_OK)
    def post(self, request):
        doctor_id = request.data.get("doctor_id")
        action = request.data.get("action")

        try:
            doctor = Doctor.objects.get(id=doctor_id)

            if action == "approve":
                doctor.is_approved = True
                doctor.save()

            elif action == "deactivate":
                doctor.is_active = False
                doctor.save()

            return Response({"message": "Doctor status updated"}, status=200)

        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

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
    Permanently deletes the record from the database.
    """
    def post(self, request, request_id):
        role = request.data.get('role')
        if role == 'doctor':
            try:
                doctor = Doctor.objects.get(id=request_id)
                name = doctor.name
                doctor.delete()
                return Response({"message": f"Dr. {name}'s request has been rejected and removed permanently."}, status=status.HTTP_200_OK)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
        elif role == 'staff':
            try:
                staff = Staff.objects.get(id=request_id)
                name = staff.name
                staff.delete()
                return Response({"message": f"{name}'s request has been rejected and removed permanently."}, status=status.HTTP_200_OK)
            except Staff.DoesNotExist:
                return Response({"error": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Invalid role. Must be 'doctor' or 'staff'."}, status=status.HTTP_400_BAD_REQUEST)


class AdminApprovalRequestsListAPIView(APIView):

    def get(self,request):

        pending_doctors=list(
            Doctor.objects.filter(is_approved=False).values(
                "id","name","email","created_at"
            )
        )

        for d in pending_doctors:
            d["user_type"]="doctor"
            d["role"]="Doctor"

        pending_staff=list(
            Staff.objects.filter(is_approved=False).values(
                "id","name","email","created_at"
            )
        )

        for s in pending_staff:
            s["user_type"]="staff"
            s["role"]="Staff"

        return Response(pending_doctors+pending_staff)


class AdminApproveUserAPIView(APIView):

    def post(self,request):

        user_id=request.data.get("user_id")
        user_type=request.data.get("user_type")

        if user_type=="doctor":
            user=Doctor.objects.get(id=user_id)

        else:
            user=Staff.objects.get(id=user_id)

        user.is_approved=True
        user.is_active=True
        user.save()

        return Response({"message":"User approved"})


class AdminRejectUserAPIView(APIView):
    """
    POST /api/admin/reject-user/
    Body: { "user_id": 12, "user_type": "doctor" }
    Permanently deletes the record from the database.
    """
    def post(self, request):
        user_id = request.data.get('user_id')
        user_type = request.data.get('user_type', 'doctor')

        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if user_type == 'staff':
                user = Staff.objects.get(id=user_id)
            else:
                user = Doctor.objects.get(id=user_id)

            name = user.name
            user.delete()
            return Response({"message": f"{name} has been rejected and removed permanently."}, status=status.HTTP_200_OK)
        except (Doctor.DoesNotExist, Staff.DoesNotExist):
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class AdminDoctorListAPIView(APIView):

    def get(self,request):

        doctors=Doctor.objects.filter(is_approved=True)

        serializer=DoctorListSerializer(doctors,many=True)

        return Response(serializer.data)


class AdminDoctorToggleAPIView(APIView):
    """
    PATCH /api/admin/doctors/{id}/toggle/
    Toggles the is_active status of a doctor.
    """
    def patch(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
            doctor.is_active = not doctor.is_active
            doctor.save()
            status_str = "active" if doctor.is_active else "disabled"
            return Response({
                "message": f"Doctor status updated to {status_str}",
                "status": status_str
            }, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)


class AdminDoctorToggleStatusAPIView(APIView):

    def post(self,request):

        doctor_id=request.data.get("doctor_id")
        is_active=request.data.get("is_active")

        doctor=Doctor.objects.get(id=doctor_id)

        doctor.is_active=is_active
        doctor.save()

        return Response({
            "message":"Doctor status updated"
        })

class AdminDoctorDetailAPIView(APIView):
    """
    GET    /api/admin/doctors/{id}/ — Returns detailed info.
    DELETE /api/admin/doctors/{id}/ — Removes doctor & revokes login.
    """
    def get(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
            serializer = DoctorDetailSerializer(doctor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
            email = doctor.email
            name = doctor.name

            # 1. Disable auth_user access if it exists
            auth_users = User.objects.filter(email=email)
            for u in auth_users:
                u.is_active = False
                u.save()
            
            # 2. Delete the Doctor record
            doctor.delete()
            return Response({"message": "Doctor removed successfully"}, status=status.HTTP_200_OK)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)


class AdminStaffListAPIView(APIView):

    def get(self,request):

        staff=Staff.objects.filter(is_approved=True)

        serializer=StaffListSerializer(staff,many=True)

        return Response(serializer.data)


class AdminStaffToggleStatusAPIView(APIView):

    def post(self,request):

        staff_id=request.data.get("staff_id")
        is_active=request.data.get("is_active")

        staff=Staff.objects.get(id=staff_id)

        staff.is_active=is_active
        staff.save()

        return Response({
            "message":"Staff status updated"
        })


class AdminStaffDetailAPIView(APIView):
    """
    GET    /api/admin/staff/{id}/ — Returns detailed info.
    DELETE /api/admin/staff/{id}/ — Removes staff.
    """
    def get(self, request, pk):
        try:
            staff = Staff.objects.get(pk=pk)
            serializer = StaffDetailSerializer(staff)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({"error": "Staff not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            staff = Staff.objects.get(pk=pk)
            email = staff.email
            
            # 1. Disable auth_user access if it exists
            auth_users = User.objects.filter(email=email)
            for u in auth_users:
                u.is_active = False
                u.save()

            # 2. Delete the Staff record
            staff.delete()
            return Response({"message": "Staff removed successfully"}, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({"error": "Staff not found"}, status=status.HTTP_404_NOT_FOUND)
class AdminSystemStatisticsAPIView(APIView):

    def get(self, request):

        total_doctors = Doctor.objects.filter(is_approved=True).count()
        total_staff = Staff.objects.filter(is_approved=True).count()

        pending_doctors = Doctor.objects.filter(is_approved=False).count()
        pending_staff = Staff.objects.filter(is_approved=False).count()

        return Response({
            "total_doctors": total_doctors,
            "total_staff": total_staff,
            "pending_doctors": pending_doctors,
            "pending_staff": pending_staff,
            "total_pending_requests": pending_doctors + pending_staff
        })