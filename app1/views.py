import os
import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import Student, Attendance
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
import time
import base64
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Student, Attendance,CameraConfiguration
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now as timezone_now
from datetime import datetime, timedelta
from django.utils.timezone import localtime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Student, Attendance
from django.db.models import Count
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.contrib.auth.models import Group
import pygame  # Import pygame for playing sounds
import threading
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.contrib import messages
from .models import LateCheckInPolicy
from .forms import LateCheckInPolicyForm
from django.shortcuts import render, get_object_or_404
from .models import Student, Fee, FeePayment
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Sum
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import render
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import StudentEditForm
###############################################################

# Home page view
def home(request):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return render(request, 'home.html')  # Display the home page for unauthenticated users
    
    # If the user is authenticated, check if they are admin or student
    if request.user.is_staff:
        return redirect('admin_dashboard')
    
    try:
        # Attempt to fetch the student's profile
        student_profile = Student.objects.get(user=request.user)
        # If the student profile exists, redirect to the student dashboard
        return redirect('student_dashboard')
    except Student.DoesNotExist:
        # If no student profile exists, redirect to an error page or home page
        return render(request, 'home.html')  # You can customize this if needed

##############################################################
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get today's date
    today = timezone.now().date()

    # Count total students
    total_students = Student.objects.count()

    # Total attendance records for today
    total_attendance = Attendance.objects.filter(date=today).count()

    # Total present students for today
    total_present = Attendance.objects.filter(date=today, status='Present').count()

    # Total absent students for today
    total_absent = Attendance.objects.filter(date=today, status='Absent').count()

    # Total late check-ins for today
    total_late_checkins = Attendance.objects.filter(date=today, is_late=True).count()

    # Total check-ins for today
    total_checkins = Attendance.objects.filter(date=today, check_in_time__isnull=False).count()

    # Total check-outs for today
    total_checkouts = Attendance.objects.filter(date=today, check_out_time__isnull=False).count()

    # Total number of cameras
    total_cameras = CameraConfiguration.objects.count()

    # Passing the data to the template
    context = {
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_late_checkins': total_late_checkins,
        'total_checkins': total_checkins,
        'total_checkouts': total_checkouts,
        'total_cameras': total_cameras,
    }

    return render(request, 'admin/admin-dashboard.html', context)

##############################################################

def mark_attendance(request):
    return render(request, 'Mark_attendance.html')

##############################################################

#############################################################
# Initialize MTCNN and InceptionResnetV1
mtcnn = MTCNN(keep_all=True)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

# Function to detect and encode faces
def detect_and_encode(image):
    with torch.no_grad():
        boxes, _ = mtcnn.detect(image)
        if boxes is not None:
            faces = []
            for box in boxes:
                face = image[int(box[1]):int(box[3]), int(box[0]):int(box[2])]
                if face.size == 0:
                    continue
                face = cv2.resize(face, (160, 160))
                face = np.transpose(face, (2, 0, 1)).astype(np.float32) / 255.0
                face_tensor = torch.tensor(face).unsqueeze(0)
                encoding = resnet(face_tensor).detach().numpy().flatten()
                faces.append(encoding)
            return faces
    return []
###########################################################################
# Function to encode uploaded images
def encode_uploaded_images():
    known_face_encodings = []
    known_face_names = []

    # Fetch only authorized images
    uploaded_images = Student.objects.filter(authorized=True)

    for student in uploaded_images:
        image_path = os.path.join(settings.MEDIA_ROOT, str(student.image))
        known_image = cv2.imread(image_path)
        known_image_rgb = cv2.cvtColor(known_image, cv2.COLOR_BGR2RGB)
        encodings = detect_and_encode(known_image_rgb)
        if encodings:
            known_face_encodings.extend(encodings)
            known_face_names.append(student.name)

    return known_face_encodings, known_face_names
############################################################################
# Function to recognize faces
def recognize_faces(known_encodings, known_names, test_encodings, threshold=0.6):
    recognized_names = []
    for test_encoding in test_encodings:
        distances = np.linalg.norm(known_encodings - test_encoding, axis=1)
        min_distance_idx = np.argmin(distances)
        if distances[min_distance_idx] < threshold:
            recognized_names.append(known_names[min_distance_idx])
        else:
            recognized_names.append('Not Recognized')
    return recognized_names

#####################################################################
@csrf_exempt
def capture_and_recognize(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    try:
        # Initialize today's date
        current_time = timezone_now()
        today = current_time.date()

        # Step 1: Mark absent students who haven't checked in
        students = Student.objects.all()
        attendance_records = Attendance.objects.filter(date=today)
        absent_students = {student.id for student in students} - {record.student_id for record in attendance_records}

        # Bulk create absences for students without attendance records
        Attendance.objects.bulk_create([
            Attendance(student_id=student_id, date=today, status='Absent')
            for student_id in absent_students
        ])

        # Update existing attendance records with missing check-ins
        attendance_records.filter(check_in_time__isnull=True, date=today).update(status='Absent')

        # Step 2: Parse and validate image data from the request
        data = json.loads(request.body)
        image_data = data.get('image')
        if not image_data:
            return JsonResponse({'message': 'No image data received.'}, status=400)

        # Decode the Base64 image
        image_data = image_data.split(',')[1]  # Remove Base64 prefix
        image_bytes = base64.b64decode(image_data)
        np_img = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        # Convert BGR to RGB for face recognition
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Step 3: Detect and encode faces
        test_face_encodings = detect_and_encode(frame_rgb)
        if not test_face_encodings:
            return JsonResponse({'message': 'No face detected.'}, status=200)

        # Step 4: Retrieve known face encodings and recognize faces
        known_face_encodings, known_face_names = encode_uploaded_images()
        if not known_face_encodings:
            return JsonResponse({'message': 'No known faces available.'}, status=200)

        recognized_names = recognize_faces(
            np.array(known_face_encodings), known_face_names, test_face_encodings, threshold=0.6
        )

        # Step 5: Prepare and update attendance records
        attendance_response = []
        for name in recognized_names:
            if name == 'Not Recognized':
                attendance_response.append({
                    'name': 'Unknown',
                    'status': 'Face not recognized',
                    'check_in_time': None,
                    'check_out_time': None,
                    'image_url': '/static/notrecognize.png',  # Placeholder for unrecognized faces
                    'play_sound': False
                })
                continue

            # Fetch student and attendance
            student = Student.objects.filter(name=name).first()
            if not student:
                continue

            attendance, created = Attendance.objects.get_or_create(student=student, date=today)

            if created or (not attendance.check_in_time):
                attendance.mark_checked_in()
                attendance.save()

                attendance_response.append({
                    'name': name,
                    'status': 'Checked-in',
                    'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                    'check_out_time': None,
                    'image_url': student.image.url if student.image else '/static/notrecognize.png',  # Student image
                    'play_sound': True
                })
            elif not attendance.check_out_time and current_time >= attendance.check_in_time + timedelta(seconds=60): # check out after 8 hours
                attendance.mark_checked_out()
                attendance_response.append({
                    'name': name,
                    'status': 'Checked-out',
                    'check_in_time': attendance.check_in_time.isoformat(),
                    'check_out_time': attendance.check_out_time.isoformat(),
                    'image_url': student.image.url if student.image else '/static/notrecognize.png',  # Student image
                    'play_sound': True
                })
            else:
                attendance_response.append({
                    'name': name,
                    'status': 'Already checked-in' if not attendance.check_out_time else 'Already checked-out',
                    'check_in_time': attendance.check_in_time.isoformat(),
                    'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                    'image_url': student.image.url if student.image else '/static/notrecognize.png',  # Student image
                    'play_sound': False
                })

        return JsonResponse({'attendance': attendance_response}, status=200)

    except Exception as e:
        return JsonResponse({'message': f"Error: {str(e)}"}, status=500)




#######################################################################
# View for capturing student information and image
def register_student(request):
    if request.method == 'POST':
        try:
            # Get student information from the form
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            student_class = request.POST.get('student_class')
            image_data = request.POST.get('image_data')
            roll_no = request.POST.get('roll_no')  # New field: Roll Number
            address = request.POST.get('address')  # New field: Address
            date_of_birth = request.POST.get('date_of_birth')  # New field: Date of Birth
            joining_date = request.POST.get('joining_date')  # New field: Joining Date
            mother_name = request.POST.get('mother_name')  # New field: Mother's Name
            father_name = request.POST.get('father_name')  # New field: Father's Name

            # Get user credentials (username and password)
            username = request.POST.get('username')
            password = request.POST.get('password')

            # Check if the username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose another one.')
                return render(request, 'register_student.html')

            # Decode the base64 image data
            if image_data:
                header, encoded = image_data.split(',', 1)
                image_file = ContentFile(base64.b64decode(encoded), name=f"{name}.jpg")

            # Create the user
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            # Create the student record and associate it with the newly created user
            student = Student(
                user=user,  # Associate the student with the created user
                name=name,
                email=email,
                phone_number=phone_number,
                student_class=student_class,
                image=image_file,
                authorized=False,  # Default to False during registration
                roll_no=roll_no,  # Set the roll number
                address=address,  # Set the address
                date_of_birth=date_of_birth,  # Set the date of birth
                joining_date=joining_date,  # Set the joining date
                mother_name=mother_name,  # Set the mother's name
                father_name=father_name  # Set the father's name
            )
            student.save()

            # Log the user in after successful registration
            login(request, user)

            # Add a success message
            messages.success(request, 'Registration successful! Welcome.')
            return redirect('register_success')  # Redirect to a success page
        except Exception as e:
            # Log the error for debugging (optional)
            print(f"Error during registration: {e}")

            # Add an error message
            messages.error(request, 'An error occurred during registration. Please try again.')
            return render(request, 'register_student.html')

    return render(request, 'register_student.html')

########################################################################


# Success view after capturing student information and image
def register_success(request):
    return render(request, 'register_success.html')

#########################################################################

#this is for showing Attendance list
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def student_attendance_list(request):
    # Get the search query and date filter from the request
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('attendance_date', '')

    # Get all students
    students = Student.objects.all()

    # Filter students based on the search query
    if search_query:
        students = students.filter(name__icontains=search_query)

    # Prepare the attendance data
    student_attendance_data = []

    for student in students:
        # Get the attendance records for each student, filtering by attendance date if provided
        attendance_records = Attendance.objects.filter(student=student)

        if date_filter:
            # Assuming date_filter is in the format YYYY-MM-DD
            attendance_records = attendance_records.filter(date=date_filter)

        attendance_records = attendance_records.order_by('date')
        
        student_attendance_data.append({
            'student': student,
            'attendance_records': attendance_records
        })

    context = {
        'student_attendance_data': student_attendance_data,
        'search_query': search_query,  # Pass the search query to the template
        'date_filter': date_filter       # Pass the date filter to the template
    }
    return render(request, 'student_attendance_list.html', context)

######################################################################

@staff_member_required
def student_list(request):
    students = Student.objects.all()
    return render(request, 'student_list.html', {'students': students})

@staff_member_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'student_detail.html', {'student': student})

@staff_member_required
def student_authorize(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        authorized = request.POST.get('authorized', False)
        student.authorized = bool(authorized)
        student.save()
        return redirect('student-detail', pk=pk)
    
    return render(request, 'student_authorize.html', {'student': student})

###############################################################################

def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        form = StudentEditForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student details updated successfully.')
            return redirect('student-detail', pk=student.pk)  # Redirect to the student detail page
    else:
        form = StudentEditForm(instance=student)

    return render(request, 'student_edit.html', {'form': form, 'student': student})
###########################################################
# This views is for Deleting student
@staff_member_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('student-list')  # Redirect to the student list after deletion
    
    return render(request, 'student_delete_confirm.html', {'student': student})

########################################################################

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Check if the user is a staff or student by checking if they have a linked Student profile
            try:
                # Attempt to fetch the student's profile
                student_profile = Student.objects.get(user=user)
                # If the student profile exists, redirect to the student dashboard
                return redirect('student_dashboard')
            except Student.DoesNotExist:
                # If no student profile exists, assume the user is a staff member
                return redirect('admin_dashboard')

        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')

#########################################################################

# This is for user logout
def user_logout(request):
    logout(request)
    return redirect('login')  # Replace 'login' with your desired redirect URL after logout
##############################################################################

#######################################################################################    

@staff_member_required
def send_attendance_notifications(request):
    # Filter late students who haven't been notified
    late_attendance_records = Attendance.objects.filter(is_late=True, email_sent=False)
    # Filter absent students who haven't been notified
    absent_students = Attendance.objects.filter(status='Absent', email_sent=False)

    # Process late students
    for record in late_attendance_records:
        student = record.student
        subject = f"Late Check-in Notification for {student.name}"

        # Render the email content from the HTML template for late students
        html_message = render_to_string(
            'email_templates/late_attendance_email.html',  # Path to the template
            {'student': student, 'record': record}  # Context to be passed into the template
        )

        recipient_email = student.email

        # Send the email with HTML content
        send_mail(
            subject,
            "This is an HTML email. Please enable HTML content to view it.",
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
            html_message=html_message
        )

        # Mark email as sent to avoid resending
        record.email_sent = True
        record.save()

    # Process absent students
    for record in absent_students:
        student = record.student
        subject = "Absent Attendance Notification"

        # Render the email content from the HTML template for absent students
        html_message = render_to_string(
            'email_templates/absent_attendance_email.html',  # Path to the new template
            {'student': student, 'record': record}  # Context to be passed into the template
        )

        # Send the email notification for absent students
        send_mail(
            subject,
            "This is an HTML email. Please enable HTML content to view it.",
            settings.DEFAULT_FROM_EMAIL,
            [student.email],
            fail_silently=False,
            html_message=html_message
        )

        # After sending the email, update the `email_sent` field to True
        record.email_sent = True
        record.save()

    # Combine late and absent students for the response
    all_notified_students = late_attendance_records | absent_students
    # Display success message
    messages.success(request, "Attendance notifications have been sent successfully!")

    # Return a response with a template that displays the notified students
    return render(request, 'notification_sent.html', {
        'notified_students': all_notified_students
    })

############################################################################################

# View to list all students with their fees and total balance
@staff_member_required
def student_list_with_fees(request):
    search_query = request.GET.get('search', '')  # Get the search query from the URL

    # Filter students based on the search query in name or class
    students = Student.objects.filter(
        name__icontains=search_query
    ) | Student.objects.filter(
        student_class__icontains=search_query
    )

    student_data = []
    for student in students:
        total_fee = student.fees.aggregate(total_fee=Sum('total_fee'))['total_fee'] or 0
        total_payment = student.fees.aggregate(total_payment=Sum('payments__amount'))['total_payment'] or 0
        balance = total_fee - total_payment
        fee_status = 'Paid' if balance <= 0 else 'Pending'
        student_data.append({
            'student': student,
            'total_fee': total_fee,
            'total_payment': total_payment,
            'balance': balance,
            'fee_status': fee_status,
        })

    return render(request, 'student_list_with_fees.html', {'student_data': student_data, 'search_query': search_query})


# View to add fees for a student
@staff_member_required
def add_fee_for_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        total_fee = request.POST['total_fee']
        due_date = request.POST['due_date']
        Fee.objects.create(student=student, total_fee=total_fee, due_date=due_date)
        return HttpResponseRedirect(reverse('student_list_with_fees'))
    return render(request, 'add_fee_for_student.html', {'student': student})

# View to mark fee payment for a student
@staff_member_required
def pay_fee_for_student(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    if request.method == 'POST':
        payment_amount = request.POST['payment_amount']
        FeePayment.objects.create(fee=fee, amount=payment_amount)
        fee.calculate_balance()  # Recalculate balance after payment
        return HttpResponseRedirect(reverse('student_list_with_fees'))
    return render(request, 'fee/pay_fee_for_student.html', {'fee': fee})

# View to view detailed fees and payments for a student
@staff_member_required
def student_fee_details(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    fees = student.fees.all()
    total_paid = sum(fee.payments.aggregate(total=Sum('amount'))['total'] or 0 for fee in fees)
    total_balance = sum(fee.balance for fee in fees)
    return render(request, 'fee/student_fee_details.html', {
        'student': student,
        'fees': fees,
        'total_paid': total_paid,
        'total_balance': total_balance,
    })

# View to delete a fee payment (optional feature for management)
@staff_member_required
def delete_fee_payment(request, payment_id):
    payment = get_object_or_404(FeePayment, id=payment_id)
    fee = payment.fee
    payment.delete()
    fee.calculate_balance()  # Recalculate balance after deletion
    return HttpResponseRedirect(reverse('student_fee_details', args=[fee.student.id]))

# View to mark fee as paid manually (useful for admins)
@staff_member_required
def mark_fee_as_paid(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    fee.mark_as_paid()  # Mark the fee as paid
    return HttpResponseRedirect(reverse('student_list_with_fees'))

##################################################################################
# views.py

@staff_member_required
def late_checkin_policy_list(request):
    policies = LateCheckInPolicy.objects.select_related('student').all()
    return render(request, 'latecheckinpolicy_list.html', {'policies': policies})

def create_late_checkin_policy(request):
    if request.method == 'POST':
        form = LateCheckInPolicyForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            if LateCheckInPolicy.objects.filter(student=student).exists():
                messages.error(request, f"A late check-in policy for {student} already exists.")
            else:
                form.save()
                messages.success(request, "Late check-in policy created successfully!")
                return redirect('late_checkin_policy_list')
    else:
        form = LateCheckInPolicyForm()

    return render(request, 'latecheckinpolicy_form.html', {'form': form})

@staff_member_required
def update_late_checkin_policy(request, policy_id):
    policy = get_object_or_404(LateCheckInPolicy, id=policy_id)
    if request.method == 'POST':
        form = LateCheckInPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Late check-in policy updated successfully!")
            return redirect('late_checkin_policy_list')
    else:
        form = LateCheckInPolicyForm(instance=policy)

    return render(request, 'latecheckinpolicy_form.html', {'form': form, 'policy': policy})

@staff_member_required
def delete_late_checkin_policy(request, policy_id):
    policy = get_object_or_404(LateCheckInPolicy, id=policy_id)
    if request.method == 'POST':
        policy.delete()
        messages.success(request, "Late check-in policy deleted successfully!")
        return redirect('late_checkin_policy_list')
    return render(request, 'latecheckinpolicy_confirm_delete.html', {'policy': policy})

#######################################################################################


from django.utils.timezone import now
def capture_and_recognize_with_cam(request):
    stop_events = []  # List to store stop events for each thread
    camera_threads = []  # List to store threads for each camera
    camera_windows = []  # List to store window names
    error_messages = []  # List to capture errors from threads

    def process_frame(cam_config, stop_event):
        """Thread function to capture and process frames for each camera."""
        cap = None
        window_created = False  # Flag to track if the window was created
        try:
            # Check if the camera source is a number (local webcam) or a string (IP camera URL)
            if cam_config.camera_source.isdigit():
                cap = cv2.VideoCapture(int(cam_config.camera_source))  # Use integer index for webcam
            else:
                cap = cv2.VideoCapture(cam_config.camera_source)  # Use string for IP camera URL

            if not cap.isOpened():
                raise Exception(f"Unable to access camera {cam_config.name}.")

            threshold = cam_config.threshold

            # Initialize pygame mixer for sound playback
            pygame.mixer.init()
            success_sound = pygame.mixer.Sound('app1/suc.wav')  # Load sound path

            window_name = f'Face Recognition - {cam_config.name}'
            camera_windows.append(window_name)  # Track the window name

            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print(f"Failed to capture frame for camera: {cam_config.name}")
                    break  # If frame capture fails, break from the loop

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                test_face_encodings = detect_and_encode(frame_rgb)  # Function to detect and encode face in frame

                if test_face_encodings:
                    known_face_encodings, known_face_names = encode_uploaded_images()  # Load known face encodings once
                    if known_face_encodings:
                        names = recognize_faces(
                            np.array(known_face_encodings), known_face_names, test_face_encodings, threshold
                        )

                        for name, box in zip(names, mtcnn.detect(frame_rgb)[0]):
                            if box is not None:
                                (x1, y1, x2, y2) = map(int, box)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                                if name != 'Not Recognized':
                                    students = Student.objects.filter(name=name)
                                    if students.exists():
                                        student = students.first()
                                        print(f"Recognized student: {student.name}")  # Debugging log

                                        # Check if attendance exists for today
                                        attendance, created = Attendance.objects.get_or_create(
                                            student=student, date=now().date()
                                        )

                                        if attendance.check_in_time is None:
                                            attendance.mark_checked_in()
                                            success_sound.play()
                                            cv2.putText(
                                                frame, f"{name}, checked in.", (50, 50), 
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA
                                            )
                                            print(f"Attendance checked in for {student.name}")
                                        elif attendance.check_out_time is None:
                                            if now() >= attendance.check_in_time + timedelta(seconds=60):
                                                attendance.mark_checked_out()
                                                success_sound.play()
                                                cv2.putText(
                                                    frame, f"{name}, checked out.", (50, 50), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA
                                                )
                                                print(f"Attendance checked out for {student.name}")
                                            else:
                                                cv2.putText(
                                                    frame, f"{name}, already checked in.", (50, 50), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA
                                                )
                                        else:
                                            cv2.putText(
                                                frame, f"{name}, already checked out.", (50, 50), 
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA
                                            )
                                            print(f"Attendance already completed for {student.name}")

                # Display frame in a separate window for each camera
                if not window_created:
                    cv2.namedWindow(window_name)  # Only create window once
                    window_created = True  # Mark window as created
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    stop_event.set()  # Signal the thread to stop when 'q' is pressed
                    break

        except Exception as e:
            print(f"Error in thread for {cam_config.name}: {e}")
            error_messages.append(str(e))  # Capture error message
        finally:
            if cap is not None:
                cap.release()
            if window_created:
                cv2.destroyWindow(window_name)  # Only destroy if window was created

    try:
        # Get all camera configurations
        cam_configs = CameraConfiguration.objects.all()
        if not cam_configs.exists():
            raise Exception("No camera configurations found. Please configure them in the admin panel.")

        # Create threads for each camera configuration
        for cam_config in cam_configs:
            stop_event = threading.Event()
            stop_events.append(stop_event)

            camera_thread = threading.Thread(target=process_frame, args=(cam_config, stop_event))
            camera_threads.append(camera_thread)
            camera_thread.start()

        # Keep the main thread running while cameras are being processed
        while any(thread.is_alive() for thread in camera_threads):
            time.sleep(1)  # Non-blocking wait, allowing for UI responsiveness

    except Exception as e:
        error_messages.append(str(e))  # Capture the error message
    finally:
        # Ensure all threads are signaled to stop
        for stop_event in stop_events:
            stop_event.set()

        # Ensure all windows are closed in the main thread
        for window in camera_windows:
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) >= 1:  # Check if window exists
                cv2.destroyWindow(window)

    # Check if there are any error messages
    if error_messages:
        # Join all error messages into a single string
        full_error_message = "\n".join(error_messages)
        return render(request, 'error.html', {'error_message': full_error_message})  # Render the error page with message

    return redirect('student_attendance_list')
##############################################################################

# Function to handle the creation of a new camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_create(request):
    # Check if the request method is POST, indicating form submission
    if request.method == "POST":
        # Retrieve form data from the request
        name = request.POST.get('name')
        camera_source = request.POST.get('camera_source')
        threshold = request.POST.get('threshold')

        try:
            # Save the data to the database using the CameraConfiguration model
            CameraConfiguration.objects.create(
                name=name,
                camera_source=camera_source,
                threshold=threshold,
            )
            # Redirect to the list of camera configurations after successful creation
            return redirect('camera_config_list')

        except IntegrityError:
            # Handle the case where a configuration with the same name already exists
            messages.error(request, "A configuration with this name already exists.")
            # Render the form again to allow user to correct the error
            return render(request, 'camera_config_form.html')

    # Render the camera configuration form for GET requests
    return render(request, 'camera/camera_config_form.html')


# READ: Function to list all camera configurations
@login_required
@user_passes_test(is_admin)
def camera_config_list(request):
    # Retrieve all CameraConfiguration objects from the database
    configs = CameraConfiguration.objects.all()
    # Render the list template with the retrieved configurations
    return render(request, 'camera/camera_config_list.html', {'configs': configs})


# UPDATE: Function to edit an existing camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_update(request, pk):
    # Retrieve the specific configuration by primary key or return a 404 error if not found
    config = get_object_or_404(CameraConfiguration, pk=pk)

    # Check if the request method is POST, indicating form submission
    if request.method == "POST":
        # Update the configuration fields with data from the form
        config.name = request.POST.get('name')
        config.camera_source = request.POST.get('camera_source')
        config.threshold = request.POST.get('threshold')
        config.success_sound_path = request.POST.get('success_sound_path')

        # Save the changes to the database
        config.save()  

        # Redirect to the list page after successful update
        return redirect('camera_config_list')  
    
    # Render the configuration form with the current configuration data for GET requests
    return render(request, 'camera/camera_config_form.html', {'config': config})


# DELETE: Function to delete a camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_delete(request, pk):
    # Retrieve the specific configuration by primary key or return a 404 error if not found
    config = get_object_or_404(CameraConfiguration, pk=pk)

    # Check if the request method is POST, indicating confirmation of deletion
    if request.method == "POST":
        # Delete the record from the database
        config.delete()  
        # Redirect to the list of camera configurations after deletion
        return redirect('camera_config_list')

    # Render the delete confirmation template with the configuration data
    return render(request, 'camera/camera_config_delete.html', {'config': config})



######################## start Student views  ####################################
@login_required
def student_dashboard(request):
    try:
        # Get the student object for the currently logged-in user
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student record does not exist for this user.")
        return redirect('admin_dashboard')  # Redirect to home or profile creation page if student does not exist

    # Calculate total present and total absent attendance for the student
    total_late_count = Attendance.objects.filter(student=student, is_late=True).count()
    total_present = Attendance.objects.filter(student=student, status='Present').count()
    total_absent = Attendance.objects.filter(student=student, status='Absent').count()

    # Retrieve the most recent attendance record for the student
    attendance_records = student.attendance_set.all().order_by('-date')[:2]

    # Retrieve fee details for the student
    fee = Fee.objects.filter(student=student, paid=False).first()  # Get the unpaid fee record (if any)
    fee_payment_records = FeePayment.objects.filter(fee=fee) if fee else []

    context = {
        'student': student,
        'total_present': total_present,
        'total_absent': total_absent,
        'attendance_records': attendance_records,
        'fee': fee,
        'fee_payment_records': fee_payment_records,
        'total_late_count': total_late_count,
    }

    return render(request, 'student/student-dashboard.html', context)
##############################################################
from django.db.models import Q
@login_required
def student_attendance(request):
    user = request.user
    student = Student.objects.get(user=user)  # Fetch the logged-in student's profile
    
    # Filters for search and date
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('attendance_date', '')
    
    # Query attendance records for the student
    attendance_records = Attendance.objects.filter(student=student)
    
    if search_query:
        attendance_records = attendance_records.filter(Q(student__name__icontains=search_query) | 
                                                      Q(student__roll_no__icontains=search_query))
    
    if date_filter:
        attendance_records = attendance_records.filter(date=date_filter)
    
    # Render the attendance records
    return render(request, 'student/student_attendance.html', {
        'student_attendance_data': attendance_records,
        'search_query': search_query,
        'date_filter': date_filter
    })


##############################################################

@login_required
def student_fee_detail(request):
    # Get the currently logged-in user's student profile
    student = get_object_or_404(Student, user=request.user)

    # Retrieve fee details for the student
    fee_details = Fee.objects.filter(student=student).order_by('-due_date')

    # Pass the data to the template
    context = {
        'student': student,
        'fee_details': fee_details,
    }
    return render(request, 'student/student_fee_detail.html', context)
    