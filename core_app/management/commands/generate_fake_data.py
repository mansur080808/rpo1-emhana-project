"""
Команда для генерации тестовых данных с помощью Faker.
Использование: python manage.py generate_fake_data
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from faker import Faker

from core_app.models import Patient, Doctor, Appointment

fake = Faker('ru_RU')

SPECIALTIES = [
    'Терапевт', 'Кардиолог', 'Невролог', 'Хирург',
    'Педиатр', 'Офтальмолог', 'Дерматолог', 'Эндокринолог',
]

STATUS_CHOICES = ['pending', 'completed', 'cancelled']
STATUS_WEIGHTS = [30, 55, 15]  # % вероятность каждого статуса

COMPLAINTS = [
    'Головная боль, температура 37.5',
    'Боль в животе, тошнота',
    'Кашель, насморк',
    'Боль в спине',
    'Повышенное давление',
    'Слабость, усталость',
    'Боль в суставах',
    'Профилактический осмотр',
    'Плановая консультация',
    'Результаты анализов',
]


class Command(BaseCommand):
    help = 'Генерирует 1000+ тестовых записей с помощью Faker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patients', type=int, default=200,
            help='Количество пациентов (по умолчанию: 200)'
        )
        parser.add_argument(
            '--appointments', type=int, default=1000,
            help='Количество приемов (по умолчанию: 1000)'
        )

    def handle(self, *args, **options):
        n_patients = options['patients']
        n_appointments = options['appointments']

        # 1. Создаём врачей
        self.stdout.write('Создаём врачей...')
        doctors = list(Doctor.objects.all())

        if len(doctors) < len(SPECIALTIES):
            for i, specialty in enumerate(SPECIALTIES):
                username = f'doctor_{i+1}'
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(
                        username=username,
                        password='docpass123',
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                    )
                    doctor = Doctor.objects.create(user=user, specialty=specialty)
                    doctors.append(doctor)
            self.stdout.write(self.style.SUCCESS(f'  Создано врачей: {len(SPECIALTIES)}'))
        else:
            self.stdout.write(f'  Врачи уже есть: {len(doctors)} шт.')

        # 2. Создаём пациентов
        self.stdout.write(f'Создаём {n_patients} пациентов...')
        patients = []
        existing_iins = set(Patient.objects.values_list('iin', flat=True))

        created_patients = 0
        attempts = 0
        while created_patients < n_patients and attempts < n_patients * 3:
            attempts += 1
            # Генерируем казахстанский ИИН: 12 цифр
            iin = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            if iin in existing_iins:
                continue
            existing_iins.add(iin)

            patient = Patient(
                iin=iin,
                full_name=fake.name(),
                phone=f'+7 {random.randint(700,799)} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
            )
            patients.append(patient)
            created_patients += 1

        Patient.objects.bulk_create(patients)
        all_patients = list(Patient.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  Создано пациентов: {created_patients}'))

        # 3. Создаём приёмы
        self.stdout.write(f'Создаём {n_appointments} приемов...')
        appointments = []
        now = timezone.now()

        for _ in range(n_appointments):
            # Случайная дата за последние 90 дней
            days_ago = random.randint(0, 90)
            hours = random.randint(8, 17)
            minutes = random.choice([0, 15, 30, 45])
            dt = now - timedelta(days=days_ago, hours=random.randint(0, 23)) + timedelta(hours=hours, minutes=minutes)

            status = random.choices(STATUS_CHOICES, weights=STATUS_WEIGHTS, k=1)[0]

            appointments.append(Appointment(
                patient=random.choice(all_patients),
                doctor=random.choice(doctors),
                date_time=dt,
                status=status,
                notes=random.choice(COMPLAINTS),
            ))

        Appointment.objects.bulk_create(appointments)
        self.stdout.write(self.style.SUCCESS(f'  Создано приемов: {n_appointments}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Готово! Пациентов: {Patient.objects.count()}, '
            f'Приемов: {Appointment.objects.count()}, '
            f'Врачей: {Doctor.objects.count()}'
        ))
