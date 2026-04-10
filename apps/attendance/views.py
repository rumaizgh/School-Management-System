from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from .models import AttendanceSession, AttendanceRecord
from apps.subject.models import Subject
from .serializers import (
    AttendanceSessionSerializer,
    AttendanceRecordSerializer,
    AttendanceRecordStudentSerializer,
    ViewAttendanceRecordStudentSerializer
)
from rest_framework.response import Response
from apps.account.models import UserData
from apps.account.serializers import UserDataSerializer
from apps.academics.models import Batch
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.account.pagination import CustomPagination


class AttendanceSessionCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AttendanceSessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def get(self, request, id=None):
        if not id:
            return Response({"error": "Teacher ID is required"}, status=400)

        teacher = get_object_or_404(UserData, id=id, user_type="teacher")
        # Get subjects of this teacher
        subjects = Subject.objects.filter(teacher=teacher).values("id", "subject_name")
        subjects_data = list(subjects)

        # Get batches of this teacher
        batches = (
            Batch.objects.filter(subjects__teacher=teacher)
            .values("id", "classs")
            .distinct()
        )
        batches_data = list(batches)

        return Response({"subjects": subjects_data, "batches": batches_data})


class ViewAttendanceSessions(APIView):
    def get(self, request, id=None):
        if id:
            teacher = get_object_or_404(UserData, id=id, user_type="teacher")
            records = AttendanceSession.objects.filter(
                teacher=teacher
            ).order_by("-date")
        else:
            records = AttendanceSession.objects.all().order_by("-date")

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True)
        return paginator.get_paginated_response(serializer.data)

    def delete(self, request, id):
        session = get_object_or_404(AttendanceSession, id=id)
        if request.user != session.teacher and not request.user.is_superuser:
            return Response(
                {"error": "You do not have permission to delete this session"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            with transaction.atomic():
                session.delete()
            return Response(
                {"message": "Attendance session deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetSessionsByClass(APIView):
    def get(self, request, classs_id):
        records = AttendanceSession.objects.filter(
            classs_id=classs_id
        ).order_by("-date")

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True)
        return paginator.get_paginated_response(serializer.data)
    
class AttendanceStudentsList(APIView):
    def get(self, request, id):
        session = AttendanceSession.objects.get(id=id)
        classs = session.classs
        students = UserData.objects.filter(classs=classs, user_type="student", is_active = True)
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AttendanceRecordSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class AttendanceRecordView(APIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return AttendanceRecordStudentSerializer
        return AttendanceRecordSerializer

    def get(self, request, id):
        session = AttendanceSession.objects.get(id=id)
        status = request.GET.get("status")
        record = AttendanceRecord.objects.filter(session=session)
        if status:
            record = record.filter(status=status)
        serializer = self.get_serializer_class()(record, many=True)
        return Response(serializer.data)

    def patch(self, request, id):
        updated_records = []

        for item in request.data:
            record = AttendanceRecord.objects.get(id=item["id"], session_id=id)
            serializer = AttendanceRecordSerializer(record, data=item, partial=True)

            if serializer.is_valid():
                serializer.save()
                updated_records.append(serializer.data)
            else:
                return Response(serializer.errors)

        return Response(updated_records)

class StudentAttendanceView(APIView):
    def get(self, request):
        status = request.GET.get("status")

        today = timezone.localdate()

        records = AttendanceRecord.objects.filter(
            student=request.user,
            session__date=today
        )

        if status:
            records = records.filter(status=status)

        serializer = ViewAttendanceRecordStudentSerializer(records, many=True)
        return Response(serializer.data)
    
class TeacherStudentAttendanceView(APIView):
    def get(self,request,id):
        student=get_object_or_404(UserData,id=id,user_type="student")
        classs_id = request.GET.get("class")
        records = AttendanceRecord.objects.filter(student=student,session__teacher=request.user,session__classs=classs_id)
        serializer = AttendanceRecordStudentSerializer(records, many=True)
        return Response(serializer.data)

class SearchSession(APIView):
    def get(self, request):
        query = request.GET.get("q", "").strip()

        if not query:
            return Response({"message": "Enter search value"}, status=400)

        sessions = AttendanceSession.objects.select_related(
            'teacher', 'subject', 'classs'
        ).filter(
            Q(teacher__name__icontains=query) |
            Q(subject__subject_name__icontains=query) |
            Q(classs__classs__icontains=query)
        ).order_by('-date', 'time')

        if not sessions.exists():
            return Response({"message": "No sessions found"}, status=404)

        serializer = AttendanceSessionSerializer(sessions, many=True)
        return Response(serializer.data)