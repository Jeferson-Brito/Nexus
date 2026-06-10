from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Department

@login_required
def change_department(request, dept_id):
    if not request.user.is_administrador():
        return redirect('home')
    
    # dept_id == 0 (Global) removido conforme solicitação
    if dept_id == 0:
        return redirect('home')

    request.session['selected_department_id'] = dept_id
    dept = get_object_or_404(Department, id=dept_id)
    messages.success(request, f"Departamento alterado para: {dept.name}")
    
    return redirect('home')

@login_required
def home(request):
    return redirect('escala')

@login_required
def dashboard(request):
    return redirect('escala')
