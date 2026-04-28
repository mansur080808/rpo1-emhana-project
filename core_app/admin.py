from django.contrib import admin
from .models import Patient, Doctor, Appointment

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'iin', 'phone', 'created_at')
    search_fields = ('full_name', 'iin', 'phone')
    ordering = ('-created_at',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'specialty')
    search_fields = ('user__first_name', 'user__last_name', 'specialty')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'ФИО'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date_time', 'status')
    list_filter = ('status', 'doctor')
    search_fields = ('patient__full_name', 'patient__iin')
    ordering = ('-date_time',)
