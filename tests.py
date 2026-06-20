"""
Testing module for Google Dorking Tool
"""

import unittest
import json
from app import create_app
from app.dorking_queries import get_queries_for_domain, get_all_categories, count_queries

class TestDorkingQueries(unittest.TestCase):
    """Test dorking query generation"""
    
    def test_get_queries_for_domain(self):
        """Test query generation for a domain"""
        queries = get_queries_for_domain('example.com')
        self.assertIsInstance(queries, dict)
        self.assertGreater(len(queries), 0)
    
    def test_domain_substitution(self):
        """Test {domain} placeholder is fully substituted in all queries"""
        queries = get_queries_for_domain('test.com')
        for category, query_list in queries.items():
            for query in query_list:
                self.assertNotIn('{domain}', query)
    
    def test_get_all_categories(self):
        """Test getting all categories"""
        categories = get_all_categories()
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
    
    def test_count_queries(self):
        """Test query counting"""
        count = count_queries()
        self.assertIn('total', count)
        self.assertIn('per_category', count)
        self.assertGreater(count['total'], 0)

class TestFlaskApp(unittest.TestCase):
    """Test Flask application"""
    
    def setUp(self):
        """Set up test client"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_index_page(self):
        """Test home page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_help_page(self):
        """Test help page loads"""
        response = self.client.get('/help')
        self.assertEqual(response.status_code, 200)
    
    def test_api_categories(self):
        """Test API categories endpoint"""
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('categories', data)
    
    def test_api_health(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_start_scan_missing_domain(self):
        """Test start scan without domain"""
        response = self.client.post('/api/start-scan',
                                   data=json.dumps({}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
    
    def test_start_scan_invalid_domain(self):
        """Test start scan with invalid domain"""
        response = self.client.post('/api/start-scan',
                                   data=json.dumps({'domain': 'a'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
