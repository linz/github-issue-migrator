""" A QUICKLY PUT TOGETHER SCRIPT TO READ ISSUES FROM ONE REPO 
TO ANOTHER. THE READ FROM REPOS ISSUES WILL BE CLOSED """

import sys
import json
import re
import requests
import yaml

class Issue(object):
    def __init__(self, issue_json):
        ''' '''
               
        self.title = issue_json['title']
        self.created_date = issue_json['created_at']
        self.creator = issue_json['user']['login']
        self.creator_avatar = issue_json['user']['avatar_url']
        self.creator_url = issue_json['user']['html_url']
        self.body = issue_json['body']
        self.og_url = issue_json['url']
        self.html_url = issue_json['html_url']
        self.labels = issue_json['labels']
        self.assingees = self.set_assingees(issue_json)
        #self.milestone = int(issue_json['milestone']['number']) failing
        self.comments = []

    def set_assingees(self, issue_json):
        return [item['login'] for item in issue_json['assignees']]
    
    def get_assingees(self):
        return self.assingees
       
    def get_assignee_payload(self):
        return {
            "assignees": self.assingees
            }
        
    def set_comments(self, comments_json):
        for comment_json in comments_json:
            comment = Comment(comment_json)
            self.comments.append(comment)
    
    def get_comment_body(self):
        for comment in self.comments:
            yield comment.get_payload()

    def get_body(self):
        return '''<a href="{0}"><img src="{1}" align="left" width="96" height="96" hspace="10"></img></a> **Issue by [{2}]({0})**
            {3}
            Originally opened as {4}      
                    
----
<br>        
{5}
            
            '''.format(self.creator_url, 
                       self.creator_avatar, 
                       self.creator, 
                       re.sub(r'T[0-9:].*Z', '', self.created_date), 
                       self.html_url, 
                       self.body.encode("utf-8"))
    
    
    def get_payload(self):

        return {
                "title": self.title,
                "body": self.get_body(),
                #"milestone": self.milestone, FAILING, NOT OPERATING AS PER DOC
                "labels": self.labels
                }

    
class Comment(object):
    def __init__(self, comment_json):
        self.commentor = comment_json['user']['login'] 
        self.commentor_avatar = comment_json['user']['avatar_url']
        self.commentor_url = comment_json['user']['html_url']        
        self.created_date = comment_json['created_at'] 
        self.body = comment_json['body'] 
     
    def get_payload(self):
        return { 'body': self.get_body() }
    
    def get_body(self):
        return '''<a href="{0}"><img src="{1}" align="left" width="96" height="96" hspace="10"></img></a> **Comment by [{2}]({0})**
            {3}
            <br>       
                
----
<br>           
{4}            
            '''.format(self.commentor_url, 
                       self.commentor_avatar, 
                       self.commentor, 
                       re.sub(r'T[0-9:].*Z', '', self.created_date), 
                       self.body.encode("utf-8"))
            


class ApiInterface (object):
    def __init__(self, access_token, from_owner, from_repo, to_owner, to_repo):
        self.token = access_token
        self.from_owner = from_owner
        self.from_repo = from_repo
        self.to_owner = to_owner
        self.to_repo = to_repo
       
    def get_issue(self, issue_num):
        r = requests.get('https://api.github.com/repos/{0}/{1}/issues/{2}?access_token={3}'
                            .format(self.from_owner, self.from_repo, issue_num, self.token))
        return r.json()
    
    def get_comments(self, comments_url):
        r = requests.get('{0}?access_token={1}'
                         .format(comments_url, self.token))
        return r.json()
    
    def create_issue(self, payload):    
        r = requests.post('https://api.github.com/repos/{0}/{1}/issues?access_token={2}'                      
                          .format(self.to_owner, self.to_repo, self.token), json.dumps(payload))    
        return r.json()['url'], r.json()['html_url'], 
    
    def add_assignees(self, issue_url, payload):
        #should not be needed. I should be able to 
        # set when creating issue  - but this is failing
        r = requests.post('{0}/assignees?access_token={1}'
                          .format(issue_url, self.token), json.dumps(payload))
        return r.json()
    
    
    def create_comment(self, issue_url, payload):
        r = requests.post('{0}/comments?access_token={1}'
                            .format(issue_url, self.token), json.dumps(payload))
        return r.json()
    
    def close_issue(self, issue_num):
        payload = {"state": "closed"}                
        r = requests.post('https://api.github.com/repos/{0}/{1}/issues/{2}?access_token={3}'
                         .format(self.from_owner, self.from_repo, issue_num, self.token), 
                         json.dumps(payload))    
        return r.json()

def main(): 
    
    #ARGS
    if len(sys.argv) != 2:
        print 'Usage: ' + str(sys.argv[0]) + ' config.yaml'
        sys.exit(-1)
    else:
        config_path = sys.argv[1]
   
    # CONFIG
    with open(config_path, 'r') as f:
        config = yaml.load(f)

    if "Connection" in config:
        access_token = config["Connection"]["access_token"]
    else:
        print 'CONFIG ERROR: No "Connection" section'
        sys.exit(-1)
    
    if "Repo" in config:
        from_owner = config['Repo']["from_owner"]
        from_repo = config['Repo']["from_repo"]
        to_owner = config['Repo']["to_owner"]
        to_repo = config['Repo']["to_repo"]
    else:
        print 'CONFIG ERROR: No "Repo" section'
        sys.exit(-1)
    
    if "Issues" in config:
        issues = config["Issues"]["issues"]
    else:
        print 'CONFIG ERROR: No "Issues" section'
        sys.exit(-1)   
    
    # INIT API INTERFACE
    api_iface = ApiInterface(access_token, from_owner, from_repo, to_owner, to_repo)
    
    # PROCESS ISSUES
    for issue_num in issues:
        issue_json = api_iface.get_issue(issue_num)
        og_url = issue_json['url']
        issue_obj = Issue(issue_json)
       
        # GET / SET COMMENTS      
        comments = api_iface.get_comments(issue_json['comments_url'])
        issue_obj.set_comments(comments)

        #POST ISSUE INFO
        payload = issue_obj.get_payload()
        
        new_api_url, new_http_url = api_iface.create_issue(payload)
        
        # ADD ASSINGEES()
        if issue_obj.get_assingees():
            api_iface.add_assignees(new_api_url, issue_obj.get_assignee_payload())
                
        #POST COMMENT INFO 
        for comment in issue_obj.get_comment_body():
            api_iface.create_comment(new_api_url, comment)
        
        
        #CLOSE ORGINAL ISSUE      
        closing_json = {'body': '''Closed by issue migration script. Issue [now]({}) '''
                        .format(new_http_url) }        
        api_iface.create_comment(og_url, closing_json)
        api_iface.close_issue(issue_num)
        
if __name__ == "__main__":
    main()
