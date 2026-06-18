from flask import Blueprint, render_template, request, redirect, url_for, session
from bd import get_connection

asesor_bp = Blueprint('asesor_bp', __name__, url_prefix='/asesor')

@asesor_bp.route('/')
def asesor():
    if session.get('rol') != 'asesor':
        return redirect(url_for('auth.login'))
    return render_template('asesor.html')