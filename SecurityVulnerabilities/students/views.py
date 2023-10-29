from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import SearchForm, StudentsForm
from accounts.models import Student
from .models import Grade, Board, MissionCategory, Mission, MissionRecord
from .data import Data
from django.db.models import Max
from .service import StudentService

# 學生成績查詢
def grade_search(request):
    # 取得當前登入的學生
    student = Student.objects.get(id=request.user.id)
    if request.method == 'POST':
        # 先用 POST 的資料建立表單做驗證
        form = SearchForm(request.POST)
        if form.is_valid():
            studentId = request.POST.get('studentId') if request.POST.get('studentId') else student.studentId
            semester = request.POST.get('semester') if request.POST.get('studentId') else 109
            subject = request.POST.get('subject') if request.POST.get('subject') else 'IC'
            # 驗證通過後，再用表單的資料建立一個新的表單把預設值帶入
            form = SearchForm(initial={
                'name': student.username,
                'studentId': studentId,
                'semester': semester,
                'subject': subject,
            })
            # 如果學號是數字，就加上單引號(SQL查詢需要) ex. s0001 -> 's0001'
            if studentId[1:5].isdigit():
                studentId = "\'" + studentId + "\'"
            results = Grade.objects.raw(
                """
                SELECT s.id, g.semester, g.subject, g.grade, s.studentId, s.username
                FROM students_grade AS g
                INNER JOIN accounts_student AS s
                ON g.student_id = s.id 
                WHERE s.studentId = %s AND g.semester = %s AND g.subject = '%s'
                """ % (studentId, semester, subject)
            )
            # 有沒有查詢結果 => 傳到前端顯示查無資料
            noResult = len(results) == 0

            # 有沒有查詢到其他學生的成績 有 => 成功SQL Injection
            for result in results:
                if result.studentId != student.studentId and "or" in studentId.lower():
                    StudentService.create_mission_record(request.user.id, 9, True)
                    SQLInjection_hacked = True
                    break
                else:
                    StudentService.create_mission_record(request.user.id, 9, False)
                    SQLInjection_hacked = False
                    break
        # 驗證不通過
        else:
            form = SearchForm(initial={
            'name': student.username,
            'studentId': student.studentId,
        })
    else:
        # 預設帶入登入學生的資料
        form = SearchForm(initial={
            'name': student.username,
            'studentId': student.studentId,
        })
    return render(request, "students/grade_search.html", locals())

# 學生資料維護
def student_maintenance(request, id):
    student = Student.objects.get(id=id)
    # 如果id是1代表是admin，成功Broken Access Control
    if id == 1:
        StudentService.create_mission_record(request.user.id, 10, True)
        BrokenAccessControl_hacked = True
    if request.method == 'POST':
        # 用ModelForm建立表單，並用POST的資料做驗證
        form = StudentsForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
    else:
        form = StudentsForm(instance=student)
    return render(request, "students/student_maintenance.html", locals())

#留言板
def board(request):
    if request.method == 'POST':
        author = Student.objects.get(id=request.user.id)
        content = request.POST.get('content')
        board = Board.objects.create(author=author, content=content)
        board.save()
        if content.replace(';', '') == "<script>alert('XSS')</script>":
            StudentService.create_mission_record(request.user.id, 8, True)
            StoredXSS_hacked = True
        else:
            StudentService.create_mission_record(request.user.id, 8, False)
            StoredXSS_hacked = False
        # return redirect(reverse('Board'))
    boards = Board.objects.all()
    return render(request, 'students/board.html', locals())

# XSS
def xss_vulnerable(request):
    # 從check_answer傳來的POST請求(DOM-based XSS 錯誤)
    if request.method == 'POST':
        input = request.POST.get('input')
        return JsonResponse({'isCorrect': False, 'input': input})
    input = request.GET.get('input')

    # 確認input有沒有值(沒有值代表進入頁面) 且 不是預設的值(預設的不計算ReflectedXSS作答紀錄)
    if input and input != "ntuemie":
        mission_id = request.GET.get('mission_id')
        if input.replace(';', '') == "<script>alert('XSS')</script>":
            StudentService.create_mission_record(request.user.id, mission_id, True)
            ReflectedXSS_hacked = True
        else:
            StudentService.create_mission_record(request.user.id, mission_id, False)
            ReflectedXSS_hacked = False
    category_id = MissionCategory.objects.get(title='XSS').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/xss.html', locals())

# SQL Injection
def sql_injection_vulnerable(request):
    category_id = MissionCategory.objects.get(title='SQL Injection').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/sql_injection.html', locals())

# CSRF
def csrf(request):
    return render(request, 'students/csrf.html', locals())

# Broken Authentication
def broken_authentication_vulnerable(request):
    return render(request, 'students/broken_authentication.html', locals())

# Broken Access Control
def broken_access_control(request):
    category_id = MissionCategory.objects.get(title='Broken Access Control').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/broken_access_control.html', locals())

# Devtools頁面
def devtools(request):
    return render(request, 'students/devtools.html', locals())

# Devtools Element頁籤
def devtools_elements(request):
    category_id = MissionCategory.objects.get(title='Elements').id    
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/dev_elements.html', locals())

# Devtools Console頁籤
def devtools_console(request):
    category_id = MissionCategory.objects.get(title='Console').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/dev_console.html', locals())

# Devtools Source頁籤
def devtools_source(request):
    category_id = MissionCategory.objects.get(title='Source').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/dev_source.html', locals())

# Devtools Network頁籤
def devtools_network(request):
    category_id = MissionCategory.objects.get(title='Network').id
    missions_info, missions_complete_count = StudentService.get_missions_info(request.user.id, category_id)
    return render(request, 'students/dev_network.html', locals())

# 檢查答案
def check_answer(request):
    if request.method == 'POST':
        question = request.POST.get('question')
        input = request.POST.get('input')
        answer = request.POST.get('answer')
        mission_id = int(request.POST.get('mission_id'))
        if question == 'OverMaxLength':
            if len(input) > int(answer):
                StudentService.create_mission_record(request.user.id, mission_id, True)
                return JsonResponse({'isCorrect': True})
            else:
                StudentService.create_mission_record(request.user.id, mission_id, False)
        elif question == 'DOM-basedXSS':
            if input.replace(';', '') == answer:
                StudentService.create_mission_record(request.user.id, mission_id, True)
                return JsonResponse({'isCorrect': True})
            else:
                StudentService.create_mission_record(request.user.id, mission_id, False)
                return xss_vulnerable(request)
        if input == answer:
            StudentService.create_mission_record(request.user.id, mission_id, True)
            return JsonResponse({'isCorrect': True})
        else:
            StudentService.create_mission_record(request.user.id, mission_id, False)

    return JsonResponse({'isCorrect': False})

# Ajax
@csrf_exempt
def ajaxJsonResponse(request):
    data = Data.weather_data
    return JsonResponse({'data': data})