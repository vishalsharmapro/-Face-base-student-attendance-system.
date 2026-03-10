from django.contrib import admin
from .models import (
    Student,
    Attendance,
    LateCheckInPolicy,
    Fee,
    FeePayment,
    CameraConfiguration
)

from django.contrib import admin

admin.site.site_header = "Admin Dashboard"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Welcome to My Admin"
# Student Admin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone_number', 'student_class', 'authorized', 'roll_no', 'joining_date']
    list_filter = ['student_class', 'authorized']
    search_fields = ['name', 'email', 'roll_no']
    readonly_fields = ['image']

# Attendance Admin
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'check_in_time', 'check_out_time', 'status', 'is_late', 'calculate_duration']
    list_filter = ['date', 'status', 'is_late']
    search_fields = ['student__name', 'date']

    def calculate_duration(self, obj):
        return obj.calculate_duration() or 'N/A'
    calculate_duration.short_description = 'Duration'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ['student', 'date', 'check_in_time', 'check_out_time', 'status', 'is_late']
        else:  # Adding a new object
            return ['date', 'check_in_time', 'check_out_time', 'status', 'is_late']

    def save_model(self, request, obj, form, change):
        if not change:  # Only when adding a new record
            obj.mark_checked_in()  # Automatically mark check-in on creation
        super().save_model(request, obj, form, change)

# Late Check-In Policy Admin
@admin.register(LateCheckInPolicy)
class LateCheckInPolicyAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'description']
    search_fields = ['description']

# Fee Admin
@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ['student', 'total_fee', 'due_date', 'paid', 'balance']
    list_filter = ['paid', 'due_date']
    search_fields = ['student__name', 'student__roll_no']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calculate_balance()  # Recalculate balance after saving the fee

# Fee Payment Admin
@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ['fee', 'amount', 'date']
    search_fields = ['fee__student__name', 'fee__student__roll_no']
    list_filter = ['date']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Recalculate fee balance after payment
        obj.fee.calculate_balance()
        # After recalculating balance, check if it's paid
        if obj.fee.balance <= 0:
            obj.fee.paid = True
            obj.fee.save()

# Camera Configuration Admin
@admin.register(CameraConfiguration)
class CameraConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_source', 'threshold']
    search_fields = ['name', 'camera_source']
    list_filter = ['threshold']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Add any additional logic here if necessary
