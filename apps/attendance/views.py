from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from .models import AttendanceSession, AttendanceRecord, StudentLeaveRequest
from apps.subject.models import Subject
from .serializers import (
    AttendanceSessionSerializer,
    AttendanceRecordSerializer,
    AttendanceRecordStudentSerializer,
    ViewAttendanceRecordStudentSerializer,
    StudentLeaveRequestSerializer
)
from rest_framework.response import Response
from apps.account.models import UserData
from apps.account.serializers import UserDataSerializer
from apps.academics.models import Batch
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q
from apps.account.pagination import CustomPagination
from rest_framework.pagination import PageNumberPagination

from apps.academics.models import TimeTable
from apps.account.filters import get_institute_scoped_object_or_404, InstituteFilterBackend
from apps.notifications.services import (
    send_attendance_absent_notification,
    send_leave_submitted_notification,
    send_leave_approved_notification,
    send_leave_rejected_notification
)
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
        # Get subjects of this teacher (assigned directly or via timetable)
        subjects_qs = Subject.objects.filter(
            Q(teacher=teacher) | Q(timetable__teacher=teacher)
        ).distinct()
        subjects_qs = InstituteFilterBackend().filter_queryset(request, subjects_qs, None)
        subjects_data = list(subjects_qs.values("id", "subject_name"))

        # Get batches of this teacher (assigned directly, via timetable, or via subjects)
        batches_qs = Batch.objects.filter(
            Q(subjects__teacher=teacher) |
            Q(timetable__teacher=teacher) |
            Q(id__in=teacher.classs.values_list('id', flat=True))
        ).distinct()
        batches_qs = InstituteFilterBackend().filter_queryset(request, batches_qs, None)
        batches_data = list(batches_qs.values("id", "classs"))

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

        is_exam = request.query_params.get('is_exam')
        if is_exam is not None:
            if is_exam.lower() in ['true', '1']:
                records = records.filter(is_exam=True)
            elif is_exam.lower() in ['false', '0']:
                records = records.filter(is_exam=False)

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True, context={'request': request})
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

        is_exam = request.query_params.get('is_exam')
        if is_exam is not None:
            if is_exam.lower() in ['true', '1']:
                records = records.filter(is_exam=True)
            elif is_exam.lower() in ['false', '0']:
                records = records.filter(is_exam=False)

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        serializer = AttendanceSessionSerializer(paginated_records, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
class AttendanceStudentsList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        session = get_institute_scoped_object_or_404(AttendanceSession, request, id=id)
        classs = session.classs
        session_date = session.date

        students = UserData.objects.filter(classs=classs, user_type="student", is_active=True).order_by('roll_no', 'name')
        students = InstituteFilterBackend().filter_queryset(request, students, None)

        student_ids = [s.id for s in students]
        leaves = StudentLeaveRequest.objects.filter(
            student_id__in=student_ids,
            status__in=['approved', 'pending'],
            start_date__lte=session_date,
            end_date__gte=session_date
        ).order_by('-created_at')

        leaves_by_student = {}
        for l in leaves:
            if l.student_id not in leaves_by_student:
                leaves_by_student[l.student_id] = l

        results = []
        for s in students:
            leave = leaves_by_student.get(s.id)
            has_approved_leave = False
            leave_status = None
            leave_reason = None
            has_pending_leave = False

            if leave:
                leave_status = leave.status
                has_approved_leave = (leave.status == 'approved')
                has_pending_leave = (leave.status == 'pending')
                leave_reason = leave.formatted_reason

            profile_url = None
            if s.profile:
                try:
                    profile_url = request.build_absolute_uri(s.profile.url)
                except Exception:
                    profile_url = s.profile.url

            batch_name = classs.classs if classs else None

            results.append({
                "id": s.id,
                "name": s.name,
                "roll_no": s.roll_no,
                "profile": profile_url,
                "class_name": batch_name,
                "has_approved_leave": has_approved_leave,
                "leave_status": leave_status,
                "leave_reason": leave_reason,
                "has_pending_leave": has_pending_leave,
                "email": s.email,
                "phone": s.phone,
                "parent_name": s.parent_name,
                "parent_contact": s.parent_contact,
            })

        return Response(results)

    def post(self, request):
        serializer = AttendanceRecordSerializer(data=request.data, many=True)
        if serializer.is_valid():
            records = serializer.save()
            for record in records:
                if record.status == 'absent':
                    session_date = record.session.date
                    approved_leave = StudentLeaveRequest.objects.filter(
                        student=record.student,
                        status='approved',
                        start_date__lte=session_date,
                        end_date__gte=session_date
                    ).first()
                    if approved_leave:
                        record.is_excused = True
                        if not record.leave_reason:
                            record.leave_reason = approved_leave.formatted_reason
                        record.save(update_fields=['is_excused', 'leave_reason'])
                    else:
                        send_attendance_absent_notification(record.student, record.session)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceRecordView(APIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return AttendanceRecordStudentSerializer
        return AttendanceRecordSerializer

    def get(self, request, id):
        session_qs = AttendanceSession.objects.filter(id=id)
        if session_qs.exists():
            session = session_qs.first()
            if getattr(request.user, 'institute', None) and session.institute and session.institute != request.user.institute and not getattr(request.user, 'is_superuser', False):
                return Response({"error": "You do not have permission to access this session."}, status=status.HTTP_403_FORBIDDEN)
            records = AttendanceRecord.objects.filter(session=session)
        else:
            student_qs = UserData.objects.filter(id=id, user_type='student')
            if student_qs.exists():
                student = student_qs.first()
                if getattr(request.user, 'institute', None) and student.institute and student.institute != request.user.institute and not getattr(request.user, 'is_superuser', False):
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

        serializer = self.get_serializer_class()(records, many=True, context={'request': request})
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

        serializer = ViewAttendanceRecordStudentSerializer(records, many=True, context={'request': request})
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
        serializer = AttendanceRecordStudentSerializer(records, many=True, context={'request': request})
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

        serializer = AttendanceSessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data)


class LeavePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100

    def get_page_size(self, request):
        if 'limit' in request.query_params:
            try:
                return min(int(request.query_params['limit']), self.max_page_size)
            except (ValueError, TypeError):
                pass
        return super().get_page_size(request)

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data
        })


class StudentLeaveRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentLeaveRequestSerializer
    pagination_class = LeavePagination


    def get_queryset(self):
        user = self.request.user
        qs = StudentLeaveRequest.objects.all().select_related(
            'student', 'institute', 'reviewed_by'
        ).prefetch_related('student__classs')

        # Scope by institute
        qs = InstituteFilterBackend().filter_queryset(self.request, qs, self)

        # If student, strictly see only own leave requests
        if user.user_type == 'student':
            qs = qs.filter(student=user)
        else:
            # Admin / Teacher / Superuser filters
            student_id = self.request.query_params.get('student_id') or self.request.query_params.get('student')
            if student_id:
                qs = qs.filter(student_id=student_id)

            class_id = self.request.query_params.get('class_id')
            if class_id:
                qs = qs.filter(student__classs__id=class_id)

        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(student__name__icontains=search) |
                Q(student__roll_no__icontains=search) |
                Q(reason_notes__icontains=search) |
                Q(reason_category__icontains=search)
            )

        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        if user.user_type == 'student':
            if 'student' in data and int(data['student']) != user.id:
                return Response(
                    {"error": "You can only submit leave requests for yourself."},
                    status=status.HTTP_403_FORBIDDEN
                )
            data['student'] = user.id
        elif 'student' not in data:
            return Response(
                {"student": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(status='pending')

        # Auto-fill institute if empty
        if not instance.institute:
            if instance.student and instance.student.institute:
                instance.institute = instance.student.institute
            elif user.institute:
                instance.institute = user.institute
            instance.save(update_fields=['institute'])

        # Trigger notification to School Admin
        send_leave_submitted_notification(instance)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # Student / Parent edit rule
        if user.user_type == 'student':
            if instance.student != user:
                return Response(
                    {"error": "You can only edit your own leave requests."},
                    status=status.HTTP_403_FORBIDDEN
                )
            if instance.status != 'pending':
                return Response(
                    {"error": f"Leave request is already {instance.status} and cannot be modified."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prevent students from updating status or review fields
            allowed_fields = {'start_date', 'end_date', 'is_half_day', 'half_day_period', 'reason_category', 'reason_notes'}
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

            serializer = self.get_serializer(instance, data=update_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        # Admin review rule (approving or rejecting)
        new_status = request.data.get('status')
        if new_status:
            if instance.status in ['approved', 'rejected']:
                return Response(
                    {"error": f"Leave request is already {instance.status} and locked."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_status not in ['approved', 'rejected']:
                return Response(
                    {"error": "Status must be either 'approved' or 'rejected'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            instance.status = new_status
            if 'admin_remarks' in request.data:
                instance.admin_remarks = request.data.get('admin_remarks')
            instance.reviewed_by = user
            instance.reviewed_at = timezone.now()
            instance.save()

            if new_status == 'approved':
                # Retroactive sync with existing attendance sessions
                leave_reason_str = instance.formatted_reason
                AttendanceRecord.objects.filter(
                    student=instance.student,
                    session__date__range=[instance.start_date, instance.end_date]
                ).update(
                    status='absent',
                    leave_reason=leave_reason_str,
                    is_excused=True
                )
                send_leave_approved_notification(instance)
            elif new_status == 'rejected':
                send_leave_rejected_notification(instance)

            return Response(self.get_serializer(instance).data)

        # Standard admin edit of fields
        if instance.status in ['approved', 'rejected']:
            return Response(
                {"error": f"Leave request is already {instance.status} and locked."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if user.user_type == 'student' and instance.student != user:
            return Response(
                {"error": "You can only cancel your own leave requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        if instance.status in ['approved', 'rejected']:
            return Response(
                {"detail": "Official leave records cannot be deleted by students. Please contact school office."},
                status=status.HTTP_403_FORBIDDEN
            )

        instance.status = 'cancelled'
        instance.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        instance = self.get_object()
        if request.user.user_type not in ['admin', 'superadmin'] and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can approve leave requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        if instance.status in ['approved', 'rejected']:
            return Response(
                {"error": f"Leave request is already {instance.status} and locked."},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'approved'
        instance.admin_remarks = request.data.get('admin_remarks', instance.admin_remarks)
        instance.reviewed_by = request.user
        instance.reviewed_at = timezone.now()
        instance.save()

        # Retroactive sync
        AttendanceRecord.objects.filter(
            student=instance.student,
            session__date__range=[instance.start_date, instance.end_date]
        ).update(
            status='absent',
            leave_reason=instance.formatted_reason,
            is_excused=True
        )
        send_leave_approved_notification(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        instance = self.get_object()
        if request.user.user_type not in ['admin', 'superadmin'] and not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can reject leave requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        if instance.status in ['approved', 'rejected']:
            return Response(
                {"error": f"Leave request is already {instance.status} and locked."},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.status = 'rejected'
        instance.admin_remarks = request.data.get('admin_remarks', instance.admin_remarks)
        instance.reviewed_by = request.user
        instance.reviewed_at = timezone.now()
        instance.save()

        send_leave_rejected_notification(instance)
        return Response(self.get_serializer(instance).data)