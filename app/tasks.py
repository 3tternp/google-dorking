"""
Celery Tasks for background execution
"""

from celery import Celery, Task
from app.search_engine import GoogleSearcher
from app.dorking_queries import get_queries_for_domain
import json
from datetime import datetime

# Initialize Celery
celery_app = Celery('google_dorking')
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)

class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        print(f'Task {task_id} succeeded with result: {retval}')
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print(f'Task {task_id} failed with exception: {exc}')

celery_app.Task = CallbackTask

@celery_app.task(bind=True)
def execute_dorking_scan(self, domain: str, categories: list = None):
    """
    Execute dorking scan for a domain
    
    Args:
        domain: Target domain
        categories: List of categories to scan (None = all)
    
    Returns:
        Scan results
    """
    searcher = GoogleSearcher(delay=1.5)  # 1.5 second delay between requests
    
    try:
        # Get queries for the domain
        queries_dict = get_queries_for_domain(domain, categories)
        
        all_queries = []
        for category, queries in queries_dict.items():
            all_queries.extend(queries)
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(all_queries),
                'status': f'Starting scan for {domain} with {len(all_queries)} queries...',
                'domain': domain
            }
        )
        
        scan_results = {
            'domain': domain,
            'scan_date': datetime.now().isoformat(),
            'total_queries': len(all_queries),
            'categories_scanned': list(queries_dict.keys()),
            'results_by_category': {},
            'statistics': {}
        }
        
        # Execute queries by category
        for category_idx, (category, queries) in enumerate(queries_dict.items()):
            category_results = []
            
            for query_idx, query in enumerate(queries):
                # Update progress
                overall_progress = len([q for cat, qs in list(queries_dict.items())[:category_idx] for q in qs]) + query_idx
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': overall_progress,
                        'total': len(all_queries),
                        'status': f'Scanning category: {category}',
                        'current_query': query,
                        'domain': domain
                    }
                )
                
                # Execute query
                result = searcher.search(query, max_results=5)
                category_results.append(result)
            
            scan_results['results_by_category'][category] = category_results
        
        # Add statistics
        scan_results['statistics'] = searcher.get_stats()
        
        return {
            'status': 'completed',
            'data': scan_results
        }
    
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'error',
                'error': str(e),
                'domain': domain
            }
        )
        raise

@celery_app.task
def test_connection():
    """Test Celery connection"""
    return {'status': 'connected', 'timestamp': datetime.now().isoformat()}
