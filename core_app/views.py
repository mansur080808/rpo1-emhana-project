from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json

from .models import Appointment, Patient, Doctor


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('emhana:dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('emhana:login')


@login_required
def dashboard_view(request):
    seven_days_ago = timezone.now() - timedelta(days=7)

    # График 1: динамика приёмов за 7 дней
    daily_appointments = (
        Appointment.objects
        .filter(date_time__gte=seven_days_ago)
        .annotate(date=TruncDate('date_time'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    dates = [obj['date'].strftime('%d.%m.%Y') for obj in daily_appointments]
    counts = [obj['count'] for obj in daily_appointments]

    # График 2: распределение статусов (Doughnut chart)
    status_data = (
        Appointment.objects
        .values('status')
        .annotate(count=Count('id'))
    )
    status_map = {'pending': 'Ожидает', 'completed': 'Завершён', 'cancelled': 'Отменён'}
    status_labels = [status_map.get(s['status'], s['status']) for s in status_data]
    status_counts = [s['count'] for s in status_data]

    context = {
        'dates_json': json.dumps(dates),
        'counts_json': json.dumps(counts),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'total_patients': Patient.objects.count(),
        'pending_appointments': Appointment.objects.filter(status='pending').count(),
        'completed_appointments': Appointment.objects.filter(status='completed').count(),
        'recent_appointments': Appointment.objects.select_related('patient', 'doctor__user').order_by('-date_time')[:10],
    }
    return render(request, 'dashboard.html', context)


@login_required
def appointment_list_view(request):
    appointments = Appointment.objects.select_related('patient', 'doctor__user').order_by('-date_time')

    status_filter = request.GET.get('status')
    doctor_filter = request.GET.get('doctor_id')
    search_iin = request.GET.get('q', '').strip()

    if status_filter and status_filter != 'None':
        appointments = appointments.filter(status=status_filter)
    if doctor_filter and doctor_filter != 'None':
        appointments = appointments.filter(doctor_id=doctor_filter)
    if search_iin:
        appointments = appointments.filter(patient__iin__icontains=search_iin)

    # Пагинация — 20 записей на страницу
    paginator = Paginator(appointments, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    doctors = Doctor.objects.select_related('user').all()

    # AJAX запрос — возвращаем JSON для живого поиска
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = []
        for apt in page_obj:
            data.append({
                'patient_name': apt.patient.full_name,
                'patient_iin': apt.patient.iin,
                'doctor_name': apt.doctor.user.get_full_name(),
                'doctor_specialty': apt.doctor.specialty,
                'date_time': apt.date_time.strftime('%d.%m.%Y %H:%M'),
                'status': apt.status,
                'notes': apt.notes[:50] if apt.notes else '',
            })
        return JsonResponse({
            'results': data,
            'total': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })

    context = {
        'page_obj': page_obj,
        'doctors': doctors,
        'search_iin': search_iin,
        'status_filter': status_filter,
        'doctor_filter': doctor_filter,
    }
    return render(request, 'appointment_list.html', context)


@login_required
def appointment_create_view(request):
    if request.method == 'POST':
        iin = request.POST.get('iin')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        doctor_id = request.POST.get('doctor_id')
        date_time = request.POST.get('date_time')
        notes = request.POST.get('notes', '')

        patient, created = Patient.objects.get_or_create(
            iin=iin,
            defaults={'full_name': full_name, 'phone': phone}
        )

        Appointment.objects.create(
            patient=patient,
            doctor_id=doctor_id,
            date_time=date_time,
            notes=notes
        )
        return redirect('emhana:appointment_list')

    doctors = Doctor.objects.select_related('user').all()
    return render(request, 'appointment_create.html', {'doctors': doctors})
