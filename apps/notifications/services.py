import logging
from .firebase_service import send_fcm_notification
from apps.account.models import UserData

logger = logging.getLogger(__name__)


def send_attendance_absent_notification(student, session):
    """
    Sends notification when a student is marked Absent in an attendance session.
    Target: Student (and Parent).
    """
    try:
        if not student:
            return None

        student_name = student.name or "Student"
        session_date = session.date.strftime('%Y-%m-%d') if session and session.date else ""

        title = "Absent Alert 📅"
        body = f"Dear Parent, {student_name} was marked Absent for the class session on {session_date}."

        extra_data = {
            "student_id": str(student.id),
        }
        if session:
            extra_data["session_id"] = str(session.id)

        return send_fcm_notification(
            user_ids=[student.id],
            title=title,
            body=body,
            notification_type="attendance_alert",
            screen="attendance",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_attendance_absent_notification: {e}", exc_info=True)
        return None


def send_fee_assigned_notification(fee):
    """
    Sends notification when a new fee is assigned to a student.
    Target: Student (and Parent).
    """
    try:
        if not fee or not fee.student:
            return None

        amount_str = f"{fee.amount:g}" if isinstance(fee.amount, (int, float)) else str(fee.amount)
        batch_name = fee.batch.classs if fee.batch else "Class"
        due_date_str = fee.due_date.strftime('%Y-%m-%d') if fee.due_date else ""

        title = "New Fee Assigned 💳"
        body = f"A fee of ₹{amount_str} for Class {batch_name} is due on {due_date_str}."

        extra_data = {
            "fee_id": str(fee.id),
            "student_id": str(fee.student.id),
        }

        return send_fcm_notification(
            user_ids=[fee.student.id],
            title=title,
            body=body,
            notification_type="fee_alert",
            screen="fee_details",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_fee_assigned_notification: {e}", exc_info=True)
        return None


def send_payment_success_notification(payment):
    """
    Sends notification when payment is successfully recorded for a student's fee.
    Target: Student (and Parent).
    """
    try:
        if not payment or not payment.fee or not payment.fee.student:
            return None

        student = payment.fee.student
        student_name = student.name or "Student"
        amount_str = f"{payment.amount:g}" if isinstance(payment.amount, (int, float)) else str(payment.amount)

        title = "Payment Received Thank You! ✅"
        body = f"We have received a payment of ₹{amount_str} for {student_name}'s outstanding fee. Receipt: #{payment.id}."

        extra_data = {
            "payment_id": str(payment.id),
            "fee_id": str(payment.fee.id),
            "student_id": str(student.id),
        }

        return send_fcm_notification(
            user_ids=[student.id],
            title=title,
            body=body,
            notification_type="fee_alert",
            screen="payment_receipt",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_payment_success_notification: {e}", exc_info=True)
        return None


def send_exam_scheduled_notification(exam):
    """
    Sends notification when a new exam is scheduled/created.
    Target: All active students in target Batch/Class and their Parents.
    """
    try:
        if not exam or not exam.batch:
            return None

        start_date_str = ""
        if exam.timetable and exam.timetable.date:
            start_date_str = exam.timetable.date.strftime('%Y-%m-%d')

        target_students = UserData.objects.filter(
            classs=exam.batch,
            user_type='student',
            is_active=True
        ).distinct()

        student_ids = list(target_students.values_list('id', flat=True))
        if not student_ids:
            return None

        title = "Exam Scheduled 📝"
        if start_date_str:
            body = f"The timetable for {exam.exam_name} has been published. It begins on {start_date_str}."
        else:
            body = f"The timetable for {exam.exam_name} has been published."

        extra_data = {
            "exam_id": str(exam.id),
            "batch_id": str(exam.batch.id),
        }

        return send_fcm_notification(
            user_ids=student_ids,
            title=title,
            body=body,
            notification_type="exam_alert",
            screen="exam_timetable",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_exam_scheduled_notification: {e}", exc_info=True)
        return None


def send_marks_released_notification(mark):
    """
    Sends notification when exam marks are uploaded/published for a student.
    Target: The individual Student (and Parent).
    """
    try:
        if not mark or not mark.exam or not mark.student:
            return None

        exam_name = mark.exam.exam_name
        subject_name = mark.exam.subject.subject_name if mark.exam.subject else "Subject"
        student_name = mark.student.name or "Student"
        obtained = f"{mark.obtained_mark:g}" if isinstance(mark.obtained_mark, (int, float)) else str(mark.obtained_mark)
        total = f"{mark.exam.total_mark:g}" if isinstance(mark.exam.total_mark, (int, float)) else str(mark.exam.total_mark)

        title = "Results Declared 🎓"
        body = f"Marks for {exam_name} - {subject_name} have been published. {student_name} scored {obtained}/{total}."

        extra_data = {
            "exam_id": str(mark.exam.id),
            "student_id": str(mark.student.id),
            "mark_id": str(mark.id),
        }

        return send_fcm_notification(
            user_ids=[mark.student.id],
            title=title,
            body=body,
            notification_type="exam_alert",
            screen="marklist",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_marks_released_notification: {e}", exc_info=True)
        return None


def send_timetable_updated_notification(timetable):
    """
    Sends notification when a timetable entry is created or updated.
    Target: Students of affected Batch, and assigned Teacher.
    """
    try:
        if not timetable or not timetable.classs:
            return None

        subject_name = timetable.subject.subject_name if timetable.subject else "Class"
        day_display = timetable.get_day_display() if hasattr(timetable, 'get_day_display') else timetable.day
        start_str = timetable.start_time.strftime('%I:%M %p') if timetable.start_time else ""
        end_str = timetable.end_time.strftime('%I:%M %p') if timetable.end_time else ""

        target_users = UserData.objects.filter(
            classs=timetable.classs,
            user_type='student',
            is_active=True
        ).distinct()

        user_ids = list(target_users.values_list('id', flat=True))

        if timetable.teacher and timetable.teacher.is_active:
            if timetable.teacher.id not in user_ids:
                user_ids.append(timetable.teacher.id)

        if not user_ids:
            return None

        title = "Timetable Updated ⏰"
        body = f"Your {subject_name} class timetable has changed. New Time: {day_display} at {start_str} - {end_str}."

        extra_data = {
            "timetable_id": str(timetable.id),
            "batch_id": str(timetable.classs.id),
        }

        return send_fcm_notification(
            user_ids=user_ids,
            title=title,
            body=body,
            notification_type="timetable_alert",
            screen="timetable",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_timetable_updated_notification: {e}", exc_info=True)
        return None
