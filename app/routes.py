"""
Flask Routes — Dorking + Passive Recon
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from app.tasks import execute_dorking_scan, test_connection
from app.dorking_queries import get_all_categories, count_queries
from celery.result import AsyncResult
import json, csv
from io import StringIO, BytesIO
from datetime import datetime

main_bp = Blueprint('main', __name__)
api_bp  = Blueprint('api',  __name__)

# ── Web routes ───────────────────────────────────────────────────────────────

@main_bp.route('/')
def index():
    categories  = get_all_categories()
    query_count = count_queries()
    return render_template('index.html',
                           categories=categories,
                           total_queries=query_count['total'],
                           per_category=query_count['per_category'])

@main_bp.route('/results/<task_id>')
def view_results(task_id):
    return render_template('results.html', task_id=task_id)

@main_bp.route('/recon/<task_id>')
def view_recon(task_id):
    return render_template('recon.html', task_id=task_id)

@main_bp.route('/help')
def help_page():
    return render_template('help.html')

# ── Dorking API ───────────────────────────────────────────────────────────────

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    categories  = get_all_categories()
    query_count = count_queries()
    return jsonify({'status':'success','categories':categories,
                    'total_queries':query_count['total'],
                    'per_category':query_count['per_category']}), 200

@api_bp.route('/start-scan', methods=['POST'])
def start_scan():
    try:
        data = request.get_json()
        if not data or 'domain' not in data:
            return jsonify({'status':'error','message':'Domain is required'}), 400
        domain     = data['domain'].strip()
        categories = data.get('categories', None)
        if not domain or len(domain) < 3:
            return jsonify({'status':'error','message':'Invalid domain format'}), 400
        task = execute_dorking_scan.delay(domain, categories)
        return jsonify({'status':'started','task_id':task.id,
                        'message':f'Dorking scan started for {domain}',
                        'domain':domain,
                        'categories': categories if categories else 'all'}), 202
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/scan-status/<task_id>', methods=['GET'])
def get_scan_status(task_id):
    try:
        tr = AsyncResult(task_id)
        resp = {'task_id': task_id, 'status': tr.status}
        if tr.status == 'PENDING':
            resp.update({'progress':0, 'message':'Task is pending…'})
        elif tr.status == 'PROGRESS':
            info = tr.info or {}
            resp.update({'progress':info.get('current',0),'total':info.get('total',0),
                         'message':info.get('status',''),'current_query':info.get('current_query','')})
        elif tr.status == 'SUCCESS':
            resp.update({'progress':100,'message':'Scan completed','data':tr.result.get('data',{})})
        elif tr.status == 'FAILURE':
            resp.update({'message':'Scan failed','error':str(tr.info)})
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/scan-results/<task_id>', methods=['GET'])
def get_scan_results(task_id):
    try:
        tr = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':f'Task status is {tr.status}'}), 400
        return jsonify({'status':'success','results':tr.result.get('data',{})}), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/export-results/<task_id>', methods=['GET'])
def export_results(task_id):
    try:
        fmt = request.args.get('format','json').lower()
        tr  = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':'Scan not completed yet'}), 400
        results   = tr.result.get('data', {})
        domain    = results.get('domain','unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            buf = BytesIO(json.dumps(results, indent=2, default=str).encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='application/json', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.json')
        elif fmt == 'csv':
            sb = StringIO()
            w  = csv.writer(sb)
            w.writerow(['Category','Query','Status','Results Count','Result URLs'])
            for cat, queries in results.get('results_by_category',{}).items():
                for q in queries:
                    urls = ' | '.join(r.get('url','') for r in q.get('results',[]) if r.get('url') and 'google.com' not in r.get('url',''))
                    w.writerow([cat, q.get('query',''), q.get('status','unknown'), len(q.get('results',[])), urls])
            buf = BytesIO(sb.getvalue().encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='text/csv', as_attachment=True,
                             download_name=f'dorking_{domain}_{timestamp}.csv')
        else:
            return jsonify({'status':'error','message':'Use json or csv'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# ── Passive Recon API ─────────────────────────────────────────────────────────

@api_bp.route('/start-recon', methods=['POST'])
def start_recon():
    """Start passive subdomain enumeration (no Google needed)."""
    try:
        from app.recon_tasks import run_subdomain_enum
        data = request.get_json()
        if not data or 'domain' not in data:
            return jsonify({'status':'error','message':'Domain is required'}), 400
        domain      = data['domain'].strip()
        brute_force = data.get('brute_force', True)
        if not domain or len(domain) < 3:
            return jsonify({'status':'error','message':'Invalid domain format'}), 400
        task = run_subdomain_enum.delay(domain, brute_force)
        return jsonify({'status':'started','task_id':task.id,
                        'message':f'Subdomain enumeration started for {domain}',
                        'domain': domain}), 202
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/recon-status/<task_id>', methods=['GET'])
def get_recon_status(task_id):
    try:
        tr   = AsyncResult(task_id)
        resp = {'task_id': task_id, 'status': tr.status}
        if tr.status == 'PENDING':
            resp.update({'progress':0,'message':'Waiting…'})
        elif tr.status == 'PROGRESS':
            info = tr.info or {}
            resp.update({'message':info.get('status',''),'current':info.get('current',0),'total':info.get('total',5)})
        elif tr.status == 'SUCCESS':
            resp.update({'message':'Completed','data':tr.result.get('data',{})})
        elif tr.status == 'FAILURE':
            resp.update({'message':'Failed','error':str(tr.info)})
        return jsonify(resp), 200
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

@api_bp.route('/export-recon/<task_id>', methods=['GET'])
def export_recon(task_id):
    try:
        fmt = request.args.get('format','json').lower()
        tr  = AsyncResult(task_id)
        if tr.status != 'SUCCESS':
            return jsonify({'status':'error','message':'Recon not completed yet'}), 400
        data      = tr.result.get('data', {})
        domain    = data.get('domain','unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'json':
            buf = BytesIO(json.dumps(data, indent=2, default=str).encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='application/json', as_attachment=True,
                             download_name=f'subdomains_{domain}_{timestamp}.json')
        elif fmt == 'csv':
            sb = StringIO()
            w  = csv.writer(sb)
            w.writerow(['Subdomain','IP','Source','Extra'])
            for s in data.get('subdomains',[]):
                w.writerow([s.get('subdomain',''), s.get('ip',''), s.get('source',''), s.get('extra','')])
            buf = BytesIO(sb.getvalue().encode('utf-8'))
            buf.seek(0)
            return send_file(buf, mimetype='text/csv', as_attachment=True,
                             download_name=f'subdomains_{domain}_{timestamp}.csv')
        else:
            return jsonify({'status':'error','message':'Use json or csv'}), 400
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500

# ── Utility ───────────────────────────────────────────────────────────────────

@api_bp.route('/test-connection', methods=['GET'])
def test_celery_connection():
    try:
        task = test_connection.delay()
        return jsonify({'status':'ok','message':'Celery connection successful','task_id':task.id}), 200
    except Exception as e:
        return jsonify({'status':'error','message':f'Celery connection failed: {str(e)}'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status':'healthy','service':'Google Dorking Tool',
                    'timestamp':datetime.now().isoformat()}), 200
