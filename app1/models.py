from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import time
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
import pytz


# Student Model
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)
    student_class = models.CharField(max_length=100)
    image = models.ImageField(upload_to='students/')
    authorized = models.BooleanField(default=False)
    roll_no = models.CharField(max_length=20)
    address = models.TextField()
    date_of_birth = models.DateField()
    joining_date = models.DateField()
    mother_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# Late Check-In Policy Model
class LateCheckInPolicy(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="late_checkin_policy")

    def get_default_start_time():
        return time(8, 0)  # Default time as 8:00 AM

    start_time = models.TimeField(default=get_default_start_time)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.name} - Late Check-In After {self.start_time}"


# Attendance Model
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent')], default='Absent')
    is_late = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name} - {self.date}"

    def mark_checked_in(self):
        self.check_in_time = timezone.now()
        self.status = 'Present'

        # Fetch the student's late check-in policy
        policy = self.student.late_checkin_policy
        if policy:
            # Convert the late check-in time to the local timezone
            current_local_time = timezone.localtime()
            late_check_in_threshold = current_local_time.replace(
                hour=policy.start_time.hour,
                minute=policy.start_time.minute,
                second=0,
                microsecond=0
            )

            # Check if the check-in time is late
            if self.check_in_time > late_check_in_threshold:
                self.is_late = True

        self.save()

    def mark_checked_out(self):
        if self.check_in_time:
            self.check_out_time = timezone.now()
            self.save()
        else:
            raise ValueError("Cannot mark check-out without check-in.")

    def calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        return None

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.date = timezone.now().date()
        super().save(*args, **kwargs)

        # Automatically add fees for students with 2 days of attendance in the same month
        self.add_monthly_fee_if_eligible()

    def add_monthly_fee_if_eligible(self):
        current_month = self.date.month
        current_year = self.date.year

        # Check if the student has at least 2 days of attendance this month
        attendance_count = Attendance.objects.filter(
            student=self.student,
            status='Present',
            date__month=current_month,
            date__year=current_year
        ).count()

        if attendance_count >= 30:
            # Check if a fee for this month already exists for the student
            fee_exists = Fee.objects.filter(
                student=self.student,
                added_month=current_month,
                added_year=current_year
            ).exists()
            if not fee_exists:
                Fee.objects.create(
                    student=self.student,
                    total_fee=300.00,
                    due_date=timezone.now().date() + timezone.timedelta(days=7),  # Due date 7 days from now
                    balance=300.00,
                    added_month=current_month,
                    added_year=current_year
                )


# Fee Model
class Fee(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="fees")
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    added_month = models.PositiveIntegerField()
    added_year = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.student.name} - Total Fee: {self.total_fee}, Balance: {self.balance}"

    def calculate_balance(self):
        # Calculate the total payment made for this fee
        payments = self.payments.aggregate(total=Sum('amount'))['total'] or 0
        self.balance = self.total_fee - payments
        self.paid = self.balance <= 0
        self.save()

    # Method to mark fee as paid manually from the admin interface
    def mark_as_paid(self):
        self.paid = True
        self.balance = 0
        self.save()


# FeePayment Model
class FeePayment(models.Model):
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Payment of {self.amount} for {self.fee.student.name} on {self.date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculate the balance for the fee when a payment is made
        self.fee.calculate_balance()


# Signal to create default LateCheckInPolicy for each student
@receiver(post_save, sender=Student)
def create_late_checkin_policy(sender, instance, created, **kwargs):
    if created:
        LateCheckInPolicy.objects.create(student=instance)

######################################################################
class CameraConfiguration(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Give a name to this camera configuration")
    camera_source = models.CharField(max_length=255, help_text="Camera index (0 for default webcam or RTSP/HTTP URL for IP camera)")
    threshold = models.FloatField(default=0.6, help_text="Face recognition confidence threshold")

    def __str__(self):
        return self.name