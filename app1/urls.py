from django.urls import path
from . import views

urlpatterns = [
    # Home and Dashboard Views
    path('', views.home, name='home'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),

    # Student Registration and Attendance
    path('register_student/', views.register_student, name='register_student'),
    path('mark_attendance', views.mark_attendance, name='mark_attendance'),
    path('register_success/', views.register_success, name='register_success'),
    path('students/', views.student_list, name='student-list'),
    path('students/<int:pk>/', views.student_detail, name='student-detail'),
    path('students/attendance/', views.student_attendance_list, name='student_attendance_list'),
    path('students/<int:pk>/authorize/', views.student_authorize, name='student-authorize'),
    path('students/<int:pk>/delete/', views.student_delete, name='student-delete'),
    path('student/edit/<int:pk>/', views.student_edit, name='student-edit'),
    path('student-fee-detail/', views.student_fee_detail, name='student_fee_detail'),
    
    # Capture and Recognize Views
    path('capture-and-recognize/', views.capture_and_recognize, name='capture_and_recognize'),
    path('recognize_with_cam/', views.capture_and_recognize_with_cam, name='capture_and_recognize_with_cam'),
    
    # User Authentication Views
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Attendance Notifications
    path('send_attendance_notifications', views.send_attendance_notifications, name='send_attendance_notifications'),
    
    # Student Fees Management
    path('students-fees/', views.student_list_with_fees, name='student_list_with_fees'),
    path('students-fees/<int:student_id>/add_fee/', views.add_fee_for_student, name='add_fee_for_student'),
    path('fee/<int:fee_id>/pay/', views.pay_fee_for_student, name='pay_fee_for_student'),
    path('students-fees/<int:student_id>/fee_details/', views.student_fee_details, name='student_fee_details'),
    path('payment/<int:payment_id>/delete/', views.delete_fee_payment, name='delete_fee_payment'),
    path('fee/<int:fee_id>/mark_paid/', views.mark_fee_as_paid, name='mark_fee_as_paid'),
    
    # Late Check-in Policies
    path('late_checkin_policy_list/', views.late_checkin_policy_list, name='late_checkin_policy_list'),
    path('late-checkin-policies/create/', views.create_late_checkin_policy, name='create_late_checkin_policy'),
    path('late-checkin-policies/<int:policy_id>/update/',views.update_late_checkin_policy, name='update_late_checkin_policy'),
    path('delete-late-checkin-policy/<int:policy_id>/', views.delete_late_checkin_policy, name='delete_late_checkin_policy'),
    
    ########################################################### Camera Configurations
    path('camera-config/', views.camera_config_create, name='camera_config_create'),
    path('camera-config/list/', views.camera_config_list, name='camera_config_list'),
    path('camera-config/update/<int:pk>/', views.camera_config_update, name='camera_config_update'),
    path('camera-config/delete/<int:pk>/', views.camera_config_delete, name='camera_config_delete'),
    
    # Attendance (General View)
    path('attendance/', views.student_attendance, name='student_attendance'),
]


