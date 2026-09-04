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


def send_fee_updated_notification(fee):
    """
    Sends notification when an existing fee is updated for a student.
    Target: Student (and Parent).
    """
    try:
        if not fee or not fee.student:
            return None

        amount_str = f"{fee.amount:g}" if isinstance(fee.amount, (int, float)) else str(fee.amount)
        batch_name = fee.batch.classs if fee.batch else "Class"
        due_date_str = fee.due_date.strftime('%Y-%m-%d') if fee.due_date else ""

        title = "Fee Details Updated 💳"
        body = f"Your fee of ₹{amount_str} for Class {batch_name} due on {due_date_str} has been updated."

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
        logger.error(f"Error in send_fee_updated_notification: {e}", exc_info=True)
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


def send_salary_disbursement_notification(payment):
    """
    Sends a salary disbursement receipt notification to the teacher
    when a salary payment is recorded.

    Message format matches the WhatsApp receipt template in the spec:
        Hello {teacher_name},
        Your salary payment of {formatted_amount} for period {month} has been
        successfully processed.
        Payment Date: {paid_on}
        Payment Method: {payment_method}
        Reference ID: {transaction_id}
        Please find your official salary receipt attached.
    """
    try:
        if not payment or not payment.teacher:
            return None

        teacher = payment.teacher
        teacher_name = teacher.name or "Teacher"
        salary = payment.salary
        month = salary.month if salary else ""
        amount = payment.amount

        # Format currency amount
        try:
            currency = (
                salary.institute.currency_code
                if salary and salary.institute and salary.institute.currency_code
                else "INR"
            )
        except Exception:
            currency = "INR"

        formatted_amount = f"{currency} {float(amount):,.2f}"

        # Format paid_on date
        paid_on_str = ""
        if payment.paid_on:
            try:
                paid_on_str = payment.paid_on.strftime('%Y-%m-%d %H:%M')
            except Exception:
                paid_on_str = str(payment.paid_on)

        payment_method_display = (payment.payment_method or "").replace("_", " ").title()
        transaction_id = payment.transaction_id or "N/A"

        title = "Salary Disbursed ✅"
        body = (
            f"Hello {teacher_name}, your salary payment of {formatted_amount} "
            f"for period {month} has been successfully processed. "
            f"Payment Date: {paid_on_str}. "
            f"Payment Method: {payment_method_display}. "
            f"Reference ID: {transaction_id}."
        )

        extra_data = {
            "payment_id": str(payment.id),
            "salary_id": str(salary.id) if salary else "",
            "month": month,
        }

        return send_fcm_notification(
            user_ids=[teacher.id],
            title=title,
            body=body,
            notification_type="salary_disbursement",
            screen="salary_receipt",
            extra_data=extra_data,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_salary_disbursement_notification: {e}", exc_info=True)
        return None


def send_chapter_completion_notification(chapter):
    """
    Task B: Triggered when a chapter status is set to 'completed'
    and notify_students_on_completion is True.
    Sends notification to all active students (and parents) in the subject's class.
    """
    try:
        if not chapter or not chapter.notify_students_on_completion:
            return None

        subject = chapter.subject
        if not subject or not subject.classs:
            return None

        batch = subject.classs
        target_students = UserData.objects.filter(
            classs=batch,
            user_type='student',
            is_active=True
        ).distinct()

        user_ids = list(target_students.values_list('id', flat=True))
        if not user_ids:
            return None

        title = f"🎉 Chapter Completed in {subject.subject_name}!"
        body = f'Great progress! Chapter {chapter.chapter_number}: "{chapter.chapter_title}" has been completed by your teacher.'

        data_payload = {
            "type": "syllabus_chapter_completed",
            "subject_id": str(subject.id),
            "chapter_id": str(chapter.id)
        }

        return send_fcm_notification(
            user_ids=user_ids,
            title=title,
            body=body,
            notification_type="syllabus_chapter_completed",
            screen="chapter_detail",
            extra_data=data_payload,
            save_to_history=True
        )
    except Exception as e:
        logger.error(f"Error in send_chapter_completion_notification: {e}", exc_info=True)
        return None


def send_syllabus_due_reminders():
    """
    Task A: Scheduled Teacher Due Date Reminders (Cron / Daily Task).
    Queries chapters where reminder_enabled is True, status is not completed,
    and target_date is exactly reminder_days_before days away from current date.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.subject.models import Chapter

    try:
        today = timezone.localdate()
        reminders_sent = 0

        # Retrieve uncompleted chapters with reminders enabled
        chapters = Chapter.objects.filter(
            reminder_enabled=True,
            target_date__isnull=False
        ).exclude(status='completed').select_related('subject', 'subject__teacher')

        for chapter in chapters:
            due_date = chapter.target_date
            reminder_days = chapter.reminder_days_before
            if due_date and (due_date - today) == timedelta(days=reminder_days):
                teacher = chapter.subject.teacher if chapter.subject else None
                if not teacher or not teacher.is_active:
                    continue

                title = "⏰ Syllabus Reminder: Chapter Due Soon"
                body = (
                    f'Chapter {chapter.chapter_number}: "{chapter.chapter_title}" '
                    f'in {chapter.subject.subject_name} is due in {reminder_days} days ({due_date.strftime("%Y-%m-%d")}).'
                )

                data_payload = {
                    "type": "syllabus_due_reminder",
                    "subject_id": str(chapter.subject.id),
                    "chapter_id": str(chapter.id)
                }

                send_fcm_notification(
                    user_ids=[teacher.id],
                    title=title,
                    body=body,
                    notification_type="syllabus_due_reminder",
                    screen="chapter_detail",
                    extra_data=data_payload,
                    save_to_history=True
                )
                reminders_sent += 1

        logger.info(f"Syllabus due date reminders job executed successfully. Sent {reminders_sent} reminders.")
        return reminders_sent
    except Exception as e:
        logger.error(f"Error executing send_syllabus_due_reminders: {e}", exc_info=True)
        return 0

