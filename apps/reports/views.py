from datetime import date
from calendar import month_abbr

from django.db.models import Avg, Count, Q
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.account.models import UserData
from apps.academics.models import Batch, Exam
from apps.attendance.models import AttendanceSession, AttendanceRecord
from apps.subject.models import Subject, Chapter
from apps.academics.models import Mark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_or_null(value, digits=1):
    """Return rounded float or None if value is None / 0-division result."""
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _pass_rate(marks_qs):
    """
    Given a Mark queryset, compute pass rate %.
    A mark is 'passed' when obtained_mark >= exam.pass_mark.
    Returns None if queryset is empty.
    """
    total = marks_qs.count()
    if total == 0:
        return None
    passed = sum(
        1 for m in marks_qs.select_related('exam')
        if m.exam and m.obtained_mark >= m.exam.pass_mark
    )
    return _round_or_null((passed / total) * 100)


def _avg_percentage(marks_qs):
    """
    Average of (obtained_mark / total_mark * 100) across a Mark queryset.
    Returns None if empty or total_mark is 0.
    """
    valid = [
        (float(m.obtained_mark) / float(m.exam.total_mark)) * 100
        for m in marks_qs.select_related('exam')
        if m.exam and m.exam.total_mark and float(m.exam.total_mark) > 0
    ]
    if not valid:
        return None
    return _round_or_null(sum(valid) / len(valid))


def _institute_filter(queryset, institute):
    """Filter a queryset by institute; superadmin with no institute sees all."""
    if institute is None:
        return queryset
    model = queryset.model
    if hasattr(model, 'institute'):
        return queryset.filter(Q(institute=institute) | Q(institute__isnull=True))
    return queryset


def _last_n_months(n=6):
    """Return list of (year, month) tuples for the last n months (oldest first)."""
    today = timezone.localdate()
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


# ---------------------------------------------------------------------------
# Endpoint 1 — Admin Academic Overview
# ---------------------------------------------------------------------------

class AdminOverviewReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        institute = getattr(user, 'institute', None)

        # ── Counts ──────────────────────────────────────────────────────────
        base_users = UserData.objects.all()
        if institute:
            base_users = base_users.filter(institute=institute)

        total_students = base_users.filter(user_type='student', is_active=True).count()
        total_teachers = base_users.filter(user_type='teacher', is_active=True).count()

        batch_qs = Batch.objects.all()
        subject_qs = Subject.objects.all()
        exam_qs = Exam.objects.filter(is_deleted=False)
        session_qs = AttendanceSession.objects.all()
        record_qs = AttendanceRecord.objects.all()
        mark_qs = Mark.objects.all()

        if institute:
            batch_qs = batch_qs.filter(institute=institute)
            subject_qs = subject_qs.filter(institute=institute)
            exam_qs = exam_qs.filter(institute=institute)
            session_qs = session_qs.filter(institute=institute)
            record_qs = record_qs.filter(
                Q(session__institute=institute) | Q(session__institute__isnull=True)
            )
            mark_qs = mark_qs.filter(
                Q(exam__institute=institute) | Q(exam__institute__isnull=True)
            )

        total_classes = batch_qs.count()
        total_subjects = subject_qs.count()
        exams_conducted = exam_qs.count()

        # ── Overall attendance rate (all-time) ───────────────────────────────
        total_records = record_qs.count()
        present_all = record_qs.filter(status='present').count()
        overall_attendance_rate = (
            _round_or_null((present_all / total_records) * 100)
            if total_records > 0 else None
        )

        # ── Today ────────────────────────────────────────────────────────────
        today = timezone.localdate()
        today_sessions = session_qs.filter(date=today)
        today_records = record_qs.filter(session__in=today_sessions)
        present_today = today_records.filter(status='present').count()
        absent_today = today_records.filter(status='absent').count()

        # ── Overall pass rate ────────────────────────────────────────────────
        overall_pass_rate = _pass_rate(mark_qs)

        # ── Class-wise breakdown ─────────────────────────────────────────────
        class_wise = []
        for batch in batch_qs.order_by('classs'):
            student_count = base_users.filter(
                user_type='student', is_active=True, classs=batch
            ).count()

            b_sessions = session_qs.filter(classs=batch)
            b_records = record_qs.filter(session__in=b_sessions)
            b_total = b_records.count()
            b_present = b_records.filter(status='present').count()
            att_rate = (
                _round_or_null((b_present / b_total) * 100)
                if b_total > 0 else None
            )

            # All students in this batch
            batch_student_ids = base_users.filter(
                user_type='student', is_active=True, classs=batch
            ).values_list('id', flat=True)
            b_marks = mark_qs.filter(student_id__in=batch_student_ids)
            p_rate = _pass_rate(b_marks)

            class_wise.append({
                "class_name": str(batch),
                "student_count": student_count,
                "attendance_rate": att_rate,
                "pass_rate": p_rate,
            })

        # ── Subject-wise pass rate ───────────────────────────────────────────
        subject_wise_pass_rate = []
        for subj in subject_qs.order_by('subject_name'):
            subj_exams = exam_qs.filter(subject=subj)
            subj_marks = mark_qs.filter(exam__in=subj_exams)
            s_pass_rate = _pass_rate(subj_marks)
            subject_wise_pass_rate.append({
                "subject_name": subj.subject_name,
                "pass_rate": s_pass_rate,
                "total_exams": subj_exams.count(),
            })

        # ── Monthly attendance (last 6 months) ───────────────────────────────
        monthly_attendance = []
        for year, month in _last_n_months(6):
            month_sessions = session_qs.filter(date__year=year, date__month=month)
            month_records = record_qs.filter(session__in=month_sessions)
            m_total = month_records.count()
            m_present = month_records.filter(status='present').count()
            m_rate = (
                _round_or_null((m_present / m_total) * 100)
                if m_total > 0 else None
            )
            label = f"{month_abbr[month]} {year}"
            monthly_attendance.append({"month": label, "rate": m_rate})

        return Response({
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "total_subjects": total_subjects,
            "overall_attendance_rate": overall_attendance_rate,
            "present_today": present_today,
            "absent_today": absent_today,
            "exams_conducted": exams_conducted,
            "overall_pass_rate": overall_pass_rate,
            "class_wise": class_wise,
            "subject_wise_pass_rate": subject_wise_pass_rate,
            "monthly_attendance": monthly_attendance,
        })


# ---------------------------------------------------------------------------
# Endpoint 2 — Teacher Report
# ---------------------------------------------------------------------------

class TeacherReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        user = request.user

        # Permission: admin OR teacher themselves
        if user.user_type not in ('admin', 'superadmin') and user.id != teacher_id:
            return Response(
                {"detail": "You do not have permission to view this report."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            teacher = UserData.objects.get(id=teacher_id, user_type='teacher')
        except UserData.DoesNotExist:
            return Response({"detail": "Teacher not found."}, status=status.HTTP_404_NOT_FOUND)

        institute = getattr(teacher, 'institute', None)

        now = timezone.localdate()

        session_qs = AttendanceSession.objects.filter(teacher=teacher)
        total_sessions_taken = session_qs.count()
        sessions_this_month = session_qs.filter(
            date__year=now.year, date__month=now.month
        ).count()

        # Per-subject breakdown
        subject_qs = Subject.objects.filter(teacher=teacher).select_related('classs')
        if institute:
            subject_qs = subject_qs.filter(
                Q(institute=institute) | Q(institute__isnull=True)
            )

        exam_qs = Exam.objects.filter(is_deleted=False)
        if institute:
            exam_qs = exam_qs.filter(
                Q(institute=institute) | Q(institute__isnull=True)
            )

        mark_qs = Mark.objects.all()
        if institute:
            mark_qs = mark_qs.filter(
                Q(exam__institute=institute) | Q(exam__institute__isnull=True)
            )

        subject_wise = []
        for subj in subject_qs:
            # Sessions for this teacher + subject
            total_sessions = session_qs.filter(subject=subj).count()

            # Syllabus chapters
            chapters = Chapter.objects.filter(subject=subj)
            syllabus_chapters_total = chapters.count()
            syllabus_chapters_completed = chapters.filter(status='completed').count()
            if syllabus_chapters_total > 0:
                completion_percentage = _round_or_null(
                    (syllabus_chapters_completed / syllabus_chapters_total) * 100
                )
            else:
                completion_percentage = None

            # Exam performance for this subject
            subj_exams = exam_qs.filter(subject=subj)
            subj_marks = mark_qs.filter(exam__in=subj_exams)

            student_pass_rate = _pass_rate(subj_marks)

            # average_marks = average raw obtained_mark across all students
            avg_agg = subj_marks.aggregate(avg=Avg('obtained_mark'))
            avg_raw = avg_agg['avg']
            average_marks = _round_or_null(avg_raw)

            class_name = str(subj.classs) if subj.classs else ""

            subject_wise.append({
                "subject_id": subj.id,
                "subject_name": subj.subject_name,
                "class_name": class_name,
                "total_sessions": total_sessions,
                "syllabus_chapters_total": syllabus_chapters_total,
                "syllabus_chapters_completed": syllabus_chapters_completed,
                "completion_percentage": completion_percentage,
                "student_pass_rate": student_pass_rate,
                "average_marks": average_marks,
            })

        return Response({
            "total_sessions_taken": total_sessions_taken,
            "sessions_this_month": sessions_this_month,
            "subject_wise": subject_wise,
        })


# ---------------------------------------------------------------------------
# Endpoint 3 — Student Report
# ---------------------------------------------------------------------------

def _trend(percentages):
    """
    Determine trend from a list of exam percentages (chronological order).
    Requires at least 2 values. Returns 'improving', 'declining', or 'stable'.
    """
    if len(percentages) < 2:
        return None
    first = percentages[0]
    last = percentages[-1]
    diff = last - first
    if diff > 5:
        return "improving"
    elif diff < -5:
        return "declining"
    else:
        return "stable"


class StudentReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        user = request.user

        # Permission: admin/superadmin, student themselves, or any teacher
        is_admin = user.user_type in ('admin', 'superadmin')
        is_self = user.id == student_id
        is_teacher = user.user_type == 'teacher'

        if not (is_admin or is_self or is_teacher):
            return Response(
                {"detail": "You do not have permission to view this report."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            student = UserData.objects.prefetch_related('classs').get(
                id=student_id, user_type='student'
            )
        except UserData.DoesNotExist:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        student_batches = student.classs.all()

        # ── Attendance ───────────────────────────────────────────────────────
        institute = getattr(student, 'institute', None)

        session_qs = AttendanceSession.objects.filter(classs__in=student_batches)
        if institute:
            session_qs = session_qs.filter(
                Q(institute=institute) | Q(institute__isnull=True)
            )
        total_classes_held = session_qs.count()

        student_records = AttendanceRecord.objects.filter(student=student)
        classes_attended = student_records.filter(status='present').count()
        classes_absent = student_records.filter(status='absent').count()

        overall_attendance_rate = (
            _round_or_null((classes_attended / total_classes_held) * 100)
            if total_classes_held > 0 else None
        )

        # ── Exam results ─────────────────────────────────────────────────────
        mark_qs = (
            Mark.objects
            .filter(student=student)
            .select_related('exam', 'exam__subject', 'exam__timetable')
            .order_by('id')
        )

        exam_results = []
        for m in mark_qs:
            exam = m.exam
            if not exam:
                continue

            total_mark = float(exam.total_mark) if exam.total_mark else None
            pass_mark = float(exam.pass_mark) if exam.pass_mark else None
            obtained = float(m.obtained_mark) if m.obtained_mark is not None else None

            if obtained is not None and total_mark:
                is_pass = obtained >= (pass_mark or 0)
                percentage = _round_or_null((obtained / total_mark) * 100)
            else:
                is_pass = None
                percentage = None

            # Date from timetable if available
            exam_date = ""
            if exam.timetable and exam.timetable.date:
                exam_date = exam.timetable.date.strftime('%Y-%m-%d')

            subject_name = exam.subject.subject_name if exam.subject else ""

            exam_results.append({
                "exam_name": exam.exam_name,
                "subject_name": subject_name,
                "date": exam_date,
                "obtained_mark": obtained,
                "total_mark": total_mark,
                "pass_mark": pass_mark,
                "is_pass": is_pass,
                "percentage": percentage,
            })

        # ── Subject-wise performance ─────────────────────────────────────────
        # Group marks by subject
        subject_map = {}
        for m in mark_qs:
            exam = m.exam
            if not exam or not exam.subject:
                continue
            subj = exam.subject
            if subj.id not in subject_map:
                subject_map[subj.id] = {"name": subj.subject_name, "marks": []}
            subject_map[subj.id]["marks"].append(m)

        subject_wise_performance = []
        for subj_id, data in subject_map.items():
            marks = data["marks"]
            exams_taken = len(marks)

            # Compute per-exam percentage, ordered by mark id (chronological)
            percentages = []
            for m in sorted(marks, key=lambda x: x.id):
                exam = m.exam
                if exam and exam.total_mark and float(exam.total_mark) > 0:
                    pct = (float(m.obtained_mark) / float(exam.total_mark)) * 100
                    percentages.append(pct)

            avg_pct = (
                _round_or_null(sum(percentages) / len(percentages))
                if percentages else None
            )

            # Trend based on last 3
            last_3 = percentages[-3:] if len(percentages) >= 2 else percentages
            trend = _trend(last_3) if len(last_3) >= 2 else None

            subject_wise_performance.append({
                "subject_name": data["name"],
                "average_percentage": avg_pct,
                "exams_taken": exams_taken,
                "trend": trend,
            })

        # ── Prediction ───────────────────────────────────────────────────────
        total_exams = len(exam_results)
        prediction = None

        if total_exams >= 2:
            # Gather last 3 exam percentages
            last_3_pcts = [
                r["percentage"]
                for r in exam_results[-3:]
                if r["percentage"] is not None
            ]
            avg_recent = (
                sum(last_3_pcts) / len(last_3_pcts)
                if last_3_pcts else None
            )
            att = float(overall_attendance_rate) if overall_attendance_rate is not None else 0.0
            avg = float(avg_recent) if avg_recent is not None else 0.0

            if avg >= 80 and att >= 80:
                level = "Excellent"
                note = "Outstanding work! You're setting a great example. Keep it up! 🌟"
            elif avg >= 60 or att >= 75:
                level = "Good"
                note = "You're doing well! A little more effort and you'll reach the top. 🏆"
            elif avg >= 40:
                level = "Average"
                note = "You have the potential! Stay consistent and things will improve. 📈"
            else:
                level = "Needs Improvement"
                note = "Don't give up! Every expert was once a beginner. Start today. 🚀"

            prediction = {
                "predicted_level": level,
                "confidence_note": note,
                "based_on": "last_3_exams_and_attendance",
            }

        return Response({
            "overall_attendance_rate": overall_attendance_rate,
            "total_classes_held": total_classes_held,
            "classes_attended": classes_attended,
            "classes_absent": classes_absent,
            "exam_results": exam_results,
            "subject_wise_performance": subject_wise_performance,
            "prediction": prediction,
        })
