"""
Flask Routes for Web Interface and API
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from app.tasks import execute_dorking_scan, test_connection
from app.dorking_queries import get_all_categories, count_queries
from celery.result import AsyncResult
import json
import csv
from io import StringIO
from datetime import datetime

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

# ============= WEB ROUTES =============

@main_bp.route('/')
def index():
    """Main page"""
    categories = get_all_categories()
    query_count = count_queries()
    return render_template('index.html', 
                         categories=categories,
                         total_queries=query_count['total'],
                         per_category=query_count['per_category'])

@main_bp.route('/results/<task_id>')
def view_results(task_id):
    """View scan results"""
    return render_template('results.html', task_id=task_id)

@main_bp.route('/help')
def help_page():
    """Help and documentation page"""
    return render_template('help.html')

# ============= API ROUTES =============

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available dorking categories"""
    categories = get_all_categories()
    query_count = count_queries()
    
    return jsonify({
        'status': 'success',
        'categories': categories,
        'total_queries': query_count['total'],
        'per_category': query_count['per_category']
    }), 200

@api_bp.route('/start-scan', methods=['POST'])
def start_scan():
    """
    Start a dorking scan
    
    Request JSON:
    {
        "domain": "example.com",
        "categories": ["wordpress", "phpmyadmin"]  # optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'domain' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Domain is required'
            }), 400
        
        domain = data['domain'].strip()
        categories = data.get('categories', None)
        
        # Validate domain format
        if not domain or len(domain) < 3:
            return jsonify({
                'status': 'error',
                'message': 'Invalid domain format'
            }), 400
        
        # Start async task
        task = execute_dorking_scan.delay(domain, categories)
        
        return jsonify({
            'status': 'started',
            'task_id': task.id,
            'message': f'Dorking scan started for {domain}',
            'domain': domain,
            'categories': categories if categories else 'all'
        }), 202
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/scan-status/<task_id>', methods=['GET'])
def get_scan_status(task_id):
    """
    Get scan progress and results
    """
    try:
        task_result = AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task_result.status,
        }
        
        if task_result.status == 'PENDING':
            response['progress'] = 0
            response['message'] = 'Task is pending...'
        
        elif task_result.status == 'PROGRESS':
            response['progress'] = task_result.info.get('current', 0)
            response['total'] = task_result.info.get('total', 0)
            response['message'] = task_result.info.get('status', '')
            response['current_query'] = task_result.info.get('current_query', '')
        
        elif task_result.status == 'SUCCESS':
            response['progress'] = 100
            response['message'] = 'Scan completed'
            response['data'] = task_result.result.get('data', {})
        
        elif task_result.status == 'FAILURE':
            response['message'] = 'Scan failed'
            response['error'] = str(task_result.info)
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/scan-results/<task_id>', methods=['GET'])
def get_scan_results(task_id):
    """
    Get full scan results
    """
    try:
        task_result = AsyncResult(task_id)
        
        if task_result.status != 'SUCCESS':
            return jsonify({
                'status': 'error',
                'message': f'Task status is {task_result.status}'
            }), 400
        
        results = task_result.result.get('data', {})
        
        return jsonify({
            'status': 'success',
            'results': results
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/export-results/<task_id>', methods=['GET'])
def export_results(task_id):
    """
    Export scan results as JSON or CSV
    """
    try:
        export_format = request.args.get('format', 'json').lower()
        task_result = AsyncResult(task_id)
        
        if task_result.status != 'SUCCESS':
            return jsonify({
                'status': 'error',
                'message': 'Scan not completed yet'
            }), 400
        
        results = task_result.result.get('data', {})
        
        if export_format == 'json':
            filename = f"dorking_results_{results['domain']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output = StringIO()
            json.dump(results, output, indent=2, default=str)
            output.seek(0)
            
            return send_file(
                StringIO(output.getvalue()),
                mimetype='application/json',
                as_attachment=True,
                download_name=filename
            )
        
        elif export_format == 'csv':
            filename = f"dorking_results_{results['domain']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Category', 'Query', 'Status', 'Results Count'])
            
            # Write data
            for category, queries in results.get('results_by_category', {}).items():
                for query_result in queries:
                    status = query_result.get('status', 'unknown')
                    results_count = len(query_result.get('results', []))
                    query = query_result.get('query', '')
                    writer.writerow([category, query, status, results_count])
            
            output.seek(0)
            
            return send_file(
                StringIO(output.getvalue()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid export format. Use json or csv'
            }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/test-connection', methods=['GET'])
def test_celery_connection():
    """Test Celery connection"""
    try:
        task = test_connection.delay()
        return jsonify({
            'status': 'ok',
            'message': 'Celery connection successful',
            'task_id': task.id
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Celery connection failed: {str(e)}'
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Google Dorking Tool',
        'timestamp': datetime.now().isoformat()
    }), 200
