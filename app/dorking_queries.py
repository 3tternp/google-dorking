"""
Google Dorking Queries Database
Comprehensive list of dorking queries organized by category
"""

DORKING_QUERIES = {
    "subdomain_enumeration": [
        "site:*.{domain}",
        "site:*.*.{domain}",
        "site:*.*.*.{domain}",
    ],
    "exposed_ftp": [
        'site:{domain} intitle:"index of" inurl:ftp',
        'site:{domain} filetype:url +inurl:"ftp://" +inurl:";@"',
        'site:{domain} intitle:"FTP root at"',
        'site:{domain} inurl:FTP "ftp root at"',
        'site:{domain} name size "Last modified" inurl:ftp',
        'site:{domain} "Parent Directory" "Last modified" ftp',
    ],
    "exposed_documents": [
        'site:{domain} ext:doc | ext:docx | ext:odt | ext:pdf | ext:rtf | ext:sxw | ext:psw | ext:ppt | ext:pptx | ext:pps | ext:csv',
        'site:{domain} ext:xlsx',
    ],
    "exposed_git": [
        'site:{domain} "index of" inurl:.git',
        'site:{domain} intitle:"index of" .git/hooks/',
        'site:{domain} filetype:git | ext:git',
    ],
    "directory_listings": [
        'site:{domain} intext:"index of /"',
        'site:{domain} intitle:"index of"',
        'site:{domain} intitle:"index of" "docker-compose.yml"',
        'site:{domain} intitle:"index of"|"access_token.json"',
        'site:{domain} intitle:"index of" "config.json"',
        'site:{domain} intitle:"index of" "service-Account-Credentials.json" | "creds.json"',
        'site:{domain} intitle:"index of" "db.json"',
        'site:{domain} intitle:"index of" "credentials.json"',
        'site:{domain} intitle:"index of" "awsconfig.json"',
        'site:{domain} intext:"index of" /etc/passwd',
        'site:{domain} intext:"index of" /etc/shadow',
        'site:{domain} "index of" id_rsa',
        'site:{domain} "index of" private.key',
    ],
    "php_with_parameters": [
        'site:{domain} ext:php inurl:?',
    ],
    "xss_and_redirects": [
        'site:openbugbounty.org inurl:reports intext:"{domain}"',
    ],
    "juicy_extensions": [
        'site:{domain} ext:log | ext:txt | ext:conf | ext:cnf | ext:ini | ext:env | ext:sh | ext:bak | ext:backup | ext:swp | ext:old | ext:~ | ext:git | ext:svn | ext:htpasswd | ext:htaccess',
    ],
    "code_leaks": [
        'site:pastebin.com "{domain}"',
        'site:jsfiddle.net "{domain}"',
        'site:codebeautify.org "{domain}"',
        'site:codepen.io "{domain}"',
        'site:scribd.com "{domain}"',
        'site:npmjs.com "{domain}"',
        'site:npm.runkit.com "{domain}"',
        'site:libraries.co "{domain}"',
        'site:ycombinator.com "{domain}"',
        'site:coggle.it "{domain}"',
        'site:papaly.com "{domain}"',
        'site:trello.com "{domain}"',
        'site:prezi.com "{domain}"',
        'site:jsdelivr.net "{domain}"',
        'site:codeshare.io "{domain}"',
        'site:sharecode.io "{domain}"',
        'site:repl.it "{domain}"',
        'site:gitter.im "{domain}"',
        'site:bitbucket.org "{domain}"',
        'site:zoom.us "{domain}"',
        'site:atlassian.com "{domain}"',
        'inurl:gitlab "{domain}"',
        'site:xmind.app "{domain}"',
    ],
    "cloud_storage": [
        'site:s3.amazonaws.com "{domain}"',
        'site:blob.core.windows.net "{domain}"',
        'site:googleapis.com "{domain}"',
        'site:drive.google.com "{domain}"',
        'site:dev.azure.com "{domain}"',
        'site:onedrive.live.com "{domain}"',
        'site:digitaloceanspaces.com "{domain}"',
        'site:sharepoint.com "{domain}"',
        'site:s3-external-1.amazonaws.com "{domain}"',
        'site:s3.dualstack.us-east-1.amazonaws.com "{domain}"',
        'site:dropbox.com/s "{domain}"',
        'site:box.com/s "{domain}"',
        'site:docs.google.com inurl:"/d/" "{domain}"',
    ],
    "xss_parameters": [
        'inurl:q= | inurl:s= | inurl:search= | inurl:query= inurl:& site:{domain}',
    ],
    "open_redirect_parameters": [
        'inurl:"url=" | inurl:"return=" | inurl:"next=" | inurl:"redir=" | inurl:"http" | inurl:"%3Dhttp" | inurl:"%3D%2F" | inurl:"redirect"= | inurl:"redirecturl=" | inurl:"redirect_url=" | inurl:"returnurl=" | inurl:"relaystate=" | inurl:"forward=" | inurl:"forwardurl=" | inurl:"forward_url=" | inurl:"uri=" | inurl:"dest=" | inurl:"destination=" site:{domain}',
    ],
    "sqli_parameters": [
        'inurl:id= | inurl:pid= | inurl:category= | inurl:cat= | inurl:action= | inurl:sid= | inurl:dir= inurl:& site:{domain}',
    ],
    "ssrf_parameters": [
        'inurl:http | inurl:url= | inurl:path= | inurl:dest= | inurl:html= | inurl:data= | inurl:domain= | inurl:page= inurl:& site:{domain}',
    ],
    "lfi_parameters": [
        'inurl:include | inurl:dir | inurl:detail= | inurl:file= | inurl:folder= | inurl:inc= | inurl:locate= | inurl:doc= | inurl:conf= inurl:& site:{domain}',
    ],
    "rce_parameters": [
        'inurl:cmd | inurl:exec= | inurl:query= | inurl:code= | inurl:do= | inurl:run= | inurl:read= | inurl:ping= inurl:& site:{domain}',
    ],
    "sql_errors": [
        'site:{domain} intext:"sql syntax near" | intext:"syntax error has occurred" | intext:"incorrect syntax near" | intext:"unexpected end of SQL command" | intext:"Warning: mysql_connect()" | intext:"Warning: mysql_query()" | intext:"Warning: pg_connect()"',
    ],
    "configuration_files": [
        'inurl:config | inurl:env | inurl:setting | inurl:backup | ext:xml | ext:conf | ext:cnf | ext:reg | ext:inf | ext:rdp | ext:cfg | ext:txt | ext:ora | ext:ini site:{domain}',
        'site:{domain} intitle:"index of" inurl:app.conf',
        'site:{domain} intitle:"index of" inurl:conf',
        'site:{domain} filetype:conf',
        'site:{domain} configuration filetype:txt',
        'site:{domain} inurl:config.inc',
        'site:{domain} password host inurl:config filetype:txt',
        'site:{domain} inurl:config password host',
        'site:{domain} inurl:conf.xml',
        'site:{domain} inurl:conf.js',
        'site:{domain} inurl:conf.json',
        'site:{domain} inurl:configuration.json',
        'site:{domain} inurl:configuration.js',
        'site:{domain} inurl:configuration.xml',
        'site:{domain} inurl:secret filetype:yaml',
    ],
    "sensitive_parameters": [
        'inurl:email= | inurl:phone= | inurl:password= | inurl:secret= inurl:& site:{domain}',
    ],
    "jfrog_artifactory": [
        'site:jfrog.io "{domain}"',
        'site:{domain} inurl:/ui/repos/tree/general',
    ],
    "firebase": [
        'site:firebaseio.com "{domain}"',
    ],
    "api_documentation": [
        'inurl:apidocs | inurl:api-docs | inurl:swagger | inurl:api-explorer site:{domain}',
        'site:{domain} inurl:/swagger-ui.html',
        'site:{domain} inurl:/api/swagger',
        'site:{domain} inurl:/api/v1/docs | inurl:/api/v2/docs | inurl:/api/v3/docs',
        'site:{domain} inurl:/api/apidocs',
    ],
    "file_upload": [
        'site:{domain} "choose file"',
        'site:{domain} inurl:"/downloader.php?file="',
    ],
    "dependency_confusion": [
        'site:{domain} inurl:/ui/package.json',
        'site:{domain} inurl:/ui/package-lock.json',
        'site:{domain} inurl:/package.json',
    ],
    "cached_versions": [
        'cache:{domain}',
    ],
    "wordpress": [
        'site:{domain} inurl:/wp-admin/admin-ajax.php',
        'site:{domain} inurl:"/wp-json/wp/v2/users/"',
        'site:{domain} inurl:"/wp-content/uploads"',
        'site:{domain} intitle:"index of" "wp-config.php.bak"',
        'site:{domain} filetype:txt inurl:wp-config.txt',
        'site:{domain} inurl:wp-config.php intext:DB_PASSWORD',
        'site:{domain} inurl:wp-login.php?action=register',
    ],
    "phpmyadmin": [
        'site:{domain} intitle:"Welcome to phpMyAdmin"',
        'site:{domain} inurl:phpmyadmin/index.php',
        'site:{domain} inurl:"/phpmyadmin/user_password.php',
        'site:{domain} "phpMyAdmin MySQL-Dump"',
        'site:{domain} filetype:sql intext:"-- phpMyAdmin SQL Dump"',
    ],
    "apache": [
        'site:{domain} inurl:server-status apache',
        'site:{domain} intitle:"Apache HTTP Server"',
        'site:{domain} intitle:"Apache Status"',
        'site:{domain} intitle:"Apache Tomcat"',
    ],
    "nginx": [
        'site:{domain} intitle:"Welcome to nginx!"',
        'site:{domain} inurl:nginx_status',
    ],
    "grafana": [
        'site:{domain} intitle:"grafana" inurl:"/grafana/login"',
        'site:{domain} intitle:"Grafana - Home"',
        'site:{domain} "Welcome to Grafana"',
    ],
    "drupal": [
        'site:{domain} intext:"Powered by Drupal"',
        'site:{domain} inurl:"sites/all/modules"',
    ],
    "joomla": [
        'site:{domain} site:*/joomla/login',
        'site:{domain} inurl:"/libraries/joomla/database/"',
        'site:{domain} "Joomla! Administration Login"',
    ],
    "magento": [
        'site:{domain} "Magento is a trademark"',
        'site:{domain} inurl:/catalogsearch/advanced',
        'site:{domain} inurl:/customer/account/',
    ],
    "employees": [
        'site:linkedin.com "{domain}"',
    ],
    "bugbounty": [
        '"submit vulnerability report" | "powered by bugcrowd" | "powered by hackerone"',
        'site:*/security.txt "bounty"',
    ],
}

def get_queries_for_domain(domain: str, selected_categories: list = None) -> dict:
    """
    Generate dorking queries for a specific domain
    
    Args:
        domain: Target domain (e.g., example.com)
        selected_categories: List of specific categories to use (None = all)
    
    Returns:
        Dictionary with category names and their respective queries
    """
    result = {}
    
    categories = selected_categories if selected_categories else DORKING_QUERIES.keys()
    
    for category in categories:
        if category in DORKING_QUERIES:
            queries = DORKING_QUERIES[category]
            result[category] = [query.format(domain=domain) for query in queries]
    
    return result

def get_all_categories() -> list:
    """Get all available dorking query categories"""
    return list(DORKING_QUERIES.keys())

def count_queries() -> dict:
    """Count total queries and per category"""
    total = sum(len(queries) for queries in DORKING_QUERIES.values())
    per_category = {cat: len(queries) for cat, queries in DORKING_QUERIES.items()}
    return {"total": total, "per_category": per_category}
