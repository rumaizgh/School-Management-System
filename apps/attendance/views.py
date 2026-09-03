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
from django.db.models import Q
from apps.account.pagination import CustomPagination
from apps.academics.models import TimeTable
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend
from apps.notifications.services import send_attendance_absent_notification
from apps.notifications.models import NotificationHistory


class AttendanceSessionCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        timetable_id = request.data.get('timetable')

        if timetable_id:
            timetable = get_object_or_404(TimeTable, id=timetable_id)

            if timetable.teacher != request.user:
                return Response(
                    {"error": "You are not authorized to create a session for this timetable."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if AttendanceSession.objects.filter(timetable=timetable).exists():
                session = AttendanceSession.objects.get(timetable=timetable)
                has_records = AttendanceRecord.objects.filter(session=session).exists()

                if has_records:
                    return Response(
                        {"error": "An attendance session with records already exists for this timetable."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    session.delete()  # delete empty session, allow fresh one

            serializer = AttendanceSessionSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(institute=request.user.institute)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            teacher_id = request.data.get('teacher')
            if int(teacher_id) != request.user.id:
                return Response(
                    {"error": "You are not authorized to create a session for another teacher."},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = AttendanceSessionSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(institute=request.user.institute)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None):
        if not id:
            return Response({"error": "Teacher ID is required"}, status=400)

        teacher = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="teacher")
        # Get subjects of this teacher
        subjects = Subject.objects.filter(teacher=teacher).values("id", "subject_name")
        subjects = InstituteFilterBackend().filter_queryset(request, subjects, None)
        subjects_data = list(subjects)

        # Get batches of this teacher
        batches = (
            Batch.objects.filter(subjects__teacher=teacher)
            .values("id", "classs")
            .distinct()
        )
        batches = InstituteFilterBackend().filter_queryset(request, batches, None)
        batches_data = list(batches)

        return Response({"subjects": subjects_data, "batches": batches_data})


class ViewAttendanceSessions(APIView):
    def get(self, request, id=None):
        if id:
            teacher = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="teacher")
            records = AttendanceSession.objects.filter(
                teacher=teacher
            ).order_by("-date")
        else:
            records = AttendanceSession.objects.all().order_by("-date")

        records = InstituteFilterBackend().filter_queryset(request, records, None)

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True)
        return paginator.get_paginated_response(serializer.data)

    def delete(self, request, id):
        session = get_institute_scoped_object_or_404(AttendanceSession, request, id=id)
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
        records = InstituteFilterBackend().filter_queryset(request, records, None)

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True)
        return paginator.get_paginated_response(serializer.data)
    
class AttendanceStudentsList(APIView):
    def get(self, request, id):
        session = get_institute_scoped_object_or_404(AttendanceSession, request, id=id)
        classs = session.classs
        students = UserData.objects.filter(classs=classs, user_type="student", is_active = True)
        students = InstituteFilterBackend().filter_queryset(request, students, None)
        serializer = UserDataSerializer(students, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AttendanceRecordSerializer(data=request.data, many=True)
        if serializer.is_valid():
            records = serializer.save()
            for record in records:
                if record.status == 'absent':
                    send_attendance_absent_notification(record.student, record.session)
            return Response(serializer.data)
        return Response(serializer.errors)


class AttendanceRecordView(APIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return AttendanceRecordStudentSerializer
        return AttendanceRecordSerializer

    def get(self, request, id):
        session_qs = AttendanceSession.objects.filter(id=id)
        if session_qs.exists():
            session = session_qs.first()
            if request.user.institute and session.institute and session.institute != request.user.institute and not request.user.is_superuser:
                return Response({"error": "You do not have permission to access this session."}, status=status.HTTP_403_FORBIDDEN)
            records = AttendanceRecord.objects.filter(session=session)
        else:
            student_qs = UserData.objects.filter(id=id, user_type='student')
            if student_qs.exists():
                student = student_qs.first()
                if request.user.institute and student.institute and student.institute != request.user.institute and not request.user.is_superuser:
                    return Response({"error": "You do not have permission to access this student."}, status=status.HTTP_403_FORBIDDEN)
                records = AttendanceRecord.objects.filter(student=student)
            else:
                record_qs = AttendanceRecord.objects.filter(id=id)
                if record_qs.exists():
                    records = record_qs
                else:
                    return Response({"detail": f"No AttendanceSession, Student, or Record matches ID {id}."}, status=status.HTTP_404_NOT_FOUND)

        status_param = request.GET.get("status")
        if status_param:
            records = records.filter(status=status_param)

        student_param = request.GET.get("student") or request.GET.get("student_id")
        if student_param:
            records = records.filter(student_id=student_param)

        date_param = request.GET.get("date")
        if date_param:
            records = records.filter(session__date=date_param)

        records = InstituteFilterBackend().filter_queryset(request, records, None)
        records = records.select_related(
            'student',
            'session',
            'session__teacher',
            'session__subject',
            'session__classs'
        )

        serializer = self.get_serializer_class()(records, many=True)
        return Response(serializer.data)

    def patch(self, request, id):
        updated_records = []

        for item in request.data:
            record = get_institute_scoped_object_or_404(AttendanceRecord, request, id=item["id"], session_id=id)
            serializer = AttendanceRecordSerializer(record, data=item, partial=True)

            if serializer.is_valid():
                updated_record = serializer.save()
                if updated_record.status == 'absent':
                    send_attendance_absent_notification(updated_record.student, updated_record.session)
                updated_records.append(serializer.data)
            else:
                return Response(serializer.errors)

        return Response(updated_records)

class StudentAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status = request.GET.get("status")

        today = timezone.localdate()

        records = AttendanceRecord.objects.filter(
            student=request.user,
            session__date=today
        ).select_related('student', 'session', 'session__teacher', 'session__subject', 'session__classs')

        if status:
            records = records.filter(status=status)

        serializer = ViewAttendanceRecordStudentSerializer(records, many=True)
        unread_count = NotificationHistory.objects.filter(user=request.user, is_read=False).count()
        return Response({
            "unread_count": unread_count,
            "records": serializer.data
        })
    
class TeacherStudentAttendanceView(APIView):
    def get(self,request,id):
        student = get_institute_scoped_object_or_404(UserData, request, id=id, user_type="student")
        classs_id = request.GET.get("class")
        records = AttendanceRecord.objects.filter(student=student,session__teacher=request.user,session__classs=classs_id)
        records = InstituteFilterBackend().filter_queryset(request, records, None)
        records = records.select_related('student', 'session', 'session__teacher', 'session__subject', 'session__classs')
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

        sessions = InstituteFilterBackend().filter_queryset(request, sessions, None)

        if not sessions.exists():
            return Response({"message": "No sessions found"}, status=404)

        serializer = AttendanceSessionSerializer(sessions, many=True)
        return Response(serializer.data)